import datetime
from functools import cached_property

import requests
from bs4 import BeautifulSoup

from . import utils


class User:
    """
    AO3 user object
    """

    def __init__(self, username):
        """Creates a new AO3 user object

        Args:
            username (str): AO3 username
        """

        self.username = username
        self.soup_works = self.request("https://archiveofourown.org/users/%s/works?page=1"%(username))
        self.loaded_page = 1
        self.soup_profile = self.request("https://archiveofourown.org/users/%s/profile"%username)
        
    def get_avatar(self):
        """Returns a tuple containing the name of the file and its data

        Returns:
            tuple: (name: str, img: bytes)
        """
        
        icon = self.soup_profile.find("p", {"class": "icon"})
        src = icon.img.attrs["src"]
        name = src.split("/")[-1].split("?")[0]
        img = requests.get(src).content
        return name, img

    @cached_property
    def works(self):
        """Returns the number of works authored by this user

        Returns:
            int: Number of works
        """

        div = self.soup_works.find("div", {'id': 'inner'})
        span = div.find("span", {'class': 'current'}).getText().replace("(", "").replace(")", "")
        n = span.split(" ")[1]
        return int(self.str_format(n))   

    @cached_property
    def npages(self):
        """Returns the number of work pages

        Returns:
            int: Number of pages
        """

        return (self.works-1) // 20 + 1

    def get_work_list(self, page=1):
        """Returns the first 20 works by the author, unless the page is specified

        Args:
            page (int, optional): Page number. Defaults to 1.

        Returns:
            dict: Dictionary representing works {workid: workname}
        """

        if self.loaded_page != page:
            self.soup_works = self.request("https://archiveofourown.org/users/%s/works?page=%i"%(self.username, page))
            self.loaded_page = page
            
        ol = self.soup_works.find("ol", {'class': 'work index group'})
        works = {}
        for work in ol.find_all("li", {'role': 'article'}):
            works[int(self.str_format(work['id'].split("_")[-1]))] = work.a.string.strip()
            
        return works

    @cached_property
    def bio(self):
        """Returns the user's bio

        Returns:
            str: User's bio
        """

        blockquote = self.soup_profile.find("blockquote", {'class': 'userstuff'})
        return BeautifulSoup.getText(blockquote)        
    
    @cached_property
    def url(self):
        """Returns the URL to the user's profile

        Returns:
            str: user profile URL
        """

        return "https://archiveofourown.org/users/%s"%self.username      

    @staticmethod
    def request(url):
        """Request a web page and return a BeautifulSoup object.

        Args:
            url (str): Url to request
            data (dict, optional): Optional data to send in the request. Defaults to {}.

        Returns:
            bs4.BeautifulSoup: BeautifulSoup object representing the requested page's html
        """

        req = requests.get(url)
        if req.status_code == 429:
            raise utils.HTTPError("We are being rate-limited. Try again in a while or reduce the number of requests")
        content = req.content
        soup = BeautifulSoup(content, "lxml")
        return soup

    @staticmethod
    def str_format(string):
        """Formats a given string

        Args:
            string (str): String to format

        Returns:
            str: Formatted string
        """

        return string.replace(",", "")
