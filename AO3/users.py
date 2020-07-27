import datetime
from functools import cached_property

import requests
from bs4 import BeautifulSoup

from . import threadable, utils


class User:
    """
    AO3 user object
    """

    def __init__(self, username, session=None, load=True):
        """Creates a new AO3 user object

        Args:
            username (str): AO3 username
            session (AO3.Session, optional): Used to access additional info
            load (bool, optional): If true, the user is loaded on initialization. Defaults to True.
        """

        self.username = username
        self._session = session
        self._soup_works = None
        self._soup_profile = None
        if load:
            self.reload()
        self.loaded_page = 1
        
    def set_session(self, session):
        """Sets the session used to make requests for this work

        Args:
            session (AO3.Session/AO3.GuestSession): session object
        """
        
        self._session = session 
        
    @threadable.threadable
    def reload(self):
        """
        Loads information about this user.
        This function is threadable.
        """
        
        for attr in self.__class__.__dict__:
            if isinstance(getattr(self.__class__, attr), cached_property):
                if attr in self.__dict__:
                    delattr(self, attr)
        
        @threadable.threadable
        def req_works(username):
            self._soup_works = self.request(f"https://archiveofourown.org/users/{username}/works")
           
        @threadable.threadable
        def req_profile(username): 
            self._soup_profile = self.request(f"https://archiveofourown.org/users/{username}/profile")
            
        w, p = req_works(self.username, threaded=True), req_profile(self.username, threaded=True)
        w.join()
        p.join()
        
    def get_avatar(self):
        """Returns a tuple containing the name of the file and its data

        Returns:
            tuple: (name: str, img: bytes)
        """
        
        icon = self._soup_profile.find("p", {"class": "icon"})
        src = icon.img.attrs["src"]
        name = src.split("/")[-1].split("?")[0]
        img = requests.get(src).content
        return name, img
    
    @cached_property
    def user_id(self):
        if self._session is None or not self._session.is_authed:
            raise utils.AuthError("You can only get a user ID using an authenticated session")
        
        header = self._soup_profile.find("div", {"class": "primary header module"})
        input_ = header.find("input", {"name": "subscription[subscribable_id]"})
        if input_ is None:
            raise utils.UnexpectedResponseError("Couldn't fetch user ID")
        return int(input_.attrs["value"])

    @cached_property
    def works(self):
        """Returns the number of works authored by this user

        Returns:
            int: Number of works
        """

        div = self._soup_works.find("div", {'id': 'inner'})
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
            self._soup_works = self.request("https://archiveofourown.org/users/%s/works?page=%i"%(self.username, page))
            self.loaded_page = page
            
        ol = self._soup_works.find("ol", {'class': 'work index group'})
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

        blockquote = self._soup_profile.find("blockquote", {'class': 'userstuff'})
        return blockquote.getText() if blockquote is not None else ""    
    
    @cached_property
    def url(self):
        """Returns the URL to the user's profile

        Returns:
            str: user profile URL
        """

        return "https://archiveofourown.org/users/%s"%self.username      

    def request(self, url):
        """Request a web page and return a BeautifulSoup object.

        Args:
            url (str): Url to request

        Returns:
            bs4.BeautifulSoup: BeautifulSoup object representing the requested page's html
        """

        if self._session is None:
            req = requests.get(url)
        else:
            req = self._session.session.get(url)
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
