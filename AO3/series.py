from datetime import date
from functools import cached_property

import requests
from bs4 import BeautifulSoup

from . import threadable, utils
from .users import User
from .works import Work


class Series:
    def __init__(self, seriesid, session=None, load=True):
        """Creates a new series object

        Args:
            seriesid (int/str): ID of the series
            session (AO3.Session, optional): Session object. Defaults to None.
            load (bool, optional): If true, the work is loaded on initialization. Defaults to True.

        Raises:
            utils.InvalidIdError: Invalid series ID
        """
        self.seriesid = seriesid
        self._session = session
        self._soup = None
        if load:
            self.reload()
        
    @threadable.threadable
    def reload(self):
        """
        Loads information about this series.
        This function is threadable.
        """
        
        for attr in self.__class__.__dict__:
            if isinstance(getattr(self.__class__, attr), cached_property):
                if attr in self.__dict__:
                    delattr(self, attr)
                    
        self._soup = self.request(f"https://archiveofourown.org/series/{self.seriesid}")
        if "Error 404" in self._soup.text:
            raise utils.InvalidIdError("Cannot find series")
        
    @threadable.threadable
    def subscribe(self):
        """Subscribes to this series.
        This function is threadable.

        Raises:
            utils.AuthError: Invalid session
        """
        
        if self._session is None or not self._session.is_authed:
            raise utils.AuthError("You can only subscribe to a series using an authenticated session")
        
        utils.subscribe(self.seriesid, "Series", self._session)
        
    @threadable.threadable
    def unsubscribe(self):
        """Unubscribes from this series.
        This function is threadable.

        Raises:
            utils.AuthError: Invalid session
        """
        
        if not self.is_subscribed:
            raise Exception("You are not subscribed to this series")
        if self._session is None or not self._session.is_authed:
            raise utils.AuthError("You can only unsubscribe from a series using an authenticated session")
        
        utils.subscribe(self.seriesid, "Series", self._session, True, self.sub_id)
        
    @cached_property
    def is_subscribed(self):
        """True if you're subscribed to this series"""
        
        if self._session is None or not self._session.is_authed:
            raise utils.AuthError("You can only get a series ID using an authenticated session")
        
        form = self._soup.find("form", {"data-create-value": "Subscribe"})
        input_ = form.find("input", {"name": "commit", "value": "Unsubscribe"})
        return input_ is not None
    
    @cached_property
    def sub_id(self):
        """Returns the subscription ID. Used for unsubscribing"""
        
        if not self.is_subscribed:
            raise Exception("You are not subscribed to this series")
        
        form = self._soup.find("form", {"data-create-value": "Subscribe"})
        id_ = form.attrs["action"].split("/")[-1]
        return int(id_)
        
    @cached_property
    def creator(self):
        dl = self._soup.find("dl", {"class": "series meta group"})
        return [author.getText() for author in dl.findAll("a", {"rel": "author"})]
    
    @cached_property
    def series_begun(self):
        dl = self._soup.find("dl", {"class": "series meta group"})
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
        dl = self._soup.find("dl", {"class": "series meta group"})
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
        dl = self._soup.find("dl", {"class": "series meta group"})
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
        dl = self._soup.find("dl", {"class": "series meta group"})
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
        dl = self._soup.find("dl", {"class": "series meta group"})
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
        dl = self._soup.find("dl", {"class": "series meta group"})
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
        dl = self._soup.find("dl", {"class": "series meta group"})
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
        dl = self._soup.find("dl", {"class": "series meta group"})
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
        ul = self._soup.find("ul", {"class": "series work index group"})
        works = []
        for work in ul.find_all("li", {'class': 'work blurb group'}):
            authors = []
            for a in work.h4.find_all("a"):
                if 'rel' in a.attrs.keys():
                    if "author" in a['rel']:
                        authors.append(User(a.string, load=False))
                elif a.attrs["href"].startswith("/works"):
                    workname = a.string
                    workid = utils.workid_from_url(a['href'])
            new = Work(workid, load=False)
            setattr(new, "title", workname)
            setattr(new, "authors", authors)
            works.append(new)
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
