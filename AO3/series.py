from datetime import date
from functools import cached_property

import requests
from bs4 import BeautifulSoup

from . import utils


class Series:
    def __init__(self, seriesid, session=None):
        self.seriesid = seriesid
        self._session = session
        self.soup = self.request(f"https://archiveofourown.org/series/{self.seriesid}")
        if "Error 404" in self.soup.text:
            raise utils.InvalidIdError("Cannot find series")
        
    @cached_property
    def creator(self):
        dl = self.soup.find("dl", {"class": "series meta group"})
        return [author.getText() for author in dl.findAll("a", {"rel": "author"})]
    
    @cached_property
    def series_begun(self):
        dl = self.soup.find("dl", {"class": "series meta group"})
        info = dl.findAll(("dd", "dt"))
        last_dt = None
        for field in info:
            if field.name == "dt":
                last_dt = field.getText().strip()
            elif last_dt == "Series Begun:":
                date_str = field.getText().strip()
                break
        return date(*list(map(int, date_str.split("-"))))
    
    @cached_property
    def series_updated(self):
        dl = self.soup.find("dl", {"class": "series meta group"})
        info = dl.findAll(("dd", "dt"))
        last_dt = None
        for field in info:
            if field.name == "dt":
                last_dt = field.getText().strip()
            elif last_dt == "Series Updated:":
                date_str = field.getText().strip()
                break
        return date(*list(map(int, date_str.split("-"))))
    
    @cached_property
    def words(self):
        dl = self.soup.find("dl", {"class": "series meta group"})
        stats = dl.find("dl", {"class": "stats"}).findAll(("dd", "dt"))
        last_dt = None
        for field in stats:
            if field.name == "dt":
                last_dt = field.getText().strip()
            elif last_dt == "Words:":
                words = field.getText().strip()
                break
        return int(words.replace(",", ""))
    
    @cached_property
    def nworks(self):
        dl = self.soup.find("dl", {"class": "series meta group"})
        stats = dl.find("dl", {"class": "stats"}).findAll(("dd", "dt"))
        last_dt = None
        for field in stats:
            if field.name == "dt":
                last_dt = field.getText().strip()
            elif last_dt == "Works:":
                works = field.getText().strip()
                break
        return int(works.replace(",", ""))
    
    @cached_property
    def complete(self):
        dl = self.soup.find("dl", {"class": "series meta group"})
        stats = dl.find("dl", {"class": "stats"}).findAll(("dd", "dt"))
        last_dt = None
        for field in stats:
            if field.name == "dt":
                last_dt = field.getText().strip()
            elif last_dt == "Complete:":
                complete = field.getText().strip()
                break
        return True if complete == "Yes" else False
    
    @cached_property
    def description(self):
        dl = self.soup.find("dl", {"class": "series meta group"})
        info = dl.findAll(("dd", "dt"))
        last_dt = None
        desc = ""
        for field in info:
            if field.name == "dt":
                last_dt = field.getText().strip()
            elif last_dt == "Description:":
                desc = field.getText().strip()
                break
        return desc
    
    @cached_property
    def notes(self):
        dl = self.soup.find("dl", {"class": "series meta group"})
        info = dl.findAll(("dd", "dt"))
        last_dt = None
        notes = ""
        for field in info:
            if field.name == "dt":
                last_dt = field.getText().strip()
            elif last_dt == "Notes:":
                notes = field.getText().strip()
                break
        return notes
    
    @cached_property
    def nbookmarks(self):
        dl = self.soup.find("dl", {"class": "series meta group"})
        stats = dl.find("dl", {"class": "stats"}).findAll(("dd", "dt"))
        last_dt = None
        for field in stats:
            if field.name == "dt":
                last_dt = field.getText().strip()
            elif last_dt == "Bookmarks:":
                book = field.getText().strip()
                break
        return int(book.replace(",", ""))   
    
    @cached_property
    def work_list(self):
        ul = self.soup.find("ul", {"class": "series work index group"})
        works = []
        for work in ul.find_all("li", {'class': 'work blurb group'}):
            authors = []
            for a in work.h4.find_all("a"):
                if 'rel' in a.attrs.keys():
                    if "author" in a['rel']:
                        authors.append(a.string)
                else:
                    workname = a.string
                    workid = utils.workid_from_url(a['href'])
            works.append((workid, workname, authors))
        return works
    
    def request(self, url):
        """Request a web page and return a BeautifulSoup object.

        Args:
            url (str): Url to request
            data (dict, optional): Optional data to send in the request. Defaults to {}.

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
