import datetime
import requests
from bs4 import BeautifulSoup


class User:
    def __init__(self, username):
        self.username = username
        self.soup_works = self.request("https://archiveofourown.org/users/%s/works?page=1"%(username))
        self.loaded_page = 1
        self.soup_profile = self.request("https://archiveofourown.org/users/%s/profile"%username)

    @property
    def works(self):
        n = self.soup_works.find("h2", {'class': 'heading'}).string.strip().split(" ")[0]
        return int(n)

    @property
    def npages(self):
        return (self.works-1) // 20 + 1

    def get_work_list(self, page=1):
        """Returns the first 20 works by the author, unless the page is specified"""
        if self.loaded_page != page:
            self.soup_works = self.request("https://archiveofourown.org/users/%s/works?page=%i"%(username, page))
            self.loaded_page = page
            
        ol = self.soup_works.find("ol", {'class': 'work index group'})
        works = {}
        for work in ol.find_all("li", {'role': 'article'}):
            works[int(self.str_format(work['id'].split("_")[-1]))] = work.a.string.strip()
            
        return works

    @property
    def bio(self):
        blockquote = self.soup_profile.find("blockquote", {'class': 'userstuff'})
        return BeautifulSoup.getText(blockquote)        
    
    @property
    def url(self):        
        return "https://archiveofourown.org/users/%s"%self.username      

    @staticmethod
    def request(url):
        req = requests.get(url)
        content = req.content
        soup = BeautifulSoup(content, "html.parser")
        return soup

    @staticmethod
    def str_format(string):
        return string.replace(",", "")
        
        
        
