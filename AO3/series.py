from datetime import date
from functools import cached_property

from bs4 import BeautifulSoup

from . import threadable, utils
from .common import get_work_from_banner
from .requester import requester
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
            
    def __eq__(self, other):
        return isinstance(other, Series) and other.seriesid == self.seriesid
    
    def __repr__(self):
        try:
            return f"<Series [{self.name}]>" 
        except:
            return f"<Series [{self.seriesid}]>"
        
    def __getstate__(self):
        d = {}
        for attr in self.__dict__:
            if isinstance(self.__dict__[attr], BeautifulSoup):
                d[attr] = (self.__dict__[attr].encode(), True)
            else:
                d[attr] = (self.__dict__[attr], False)
        return d
                
    def __setstate__(self, d):
        for attr in d:
            value, issoup = d[attr]
            if issoup:
                self.__dict__[attr] = BeautifulSoup(value, "lxml")
            else:
                self.__dict__[attr] = value
        
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
        
        utils.subscribe(self.seriesid, "Series", self._session, True, self._sub_id)
        
    @cached_property
    def is_subscribed(self):
        """True if you're subscribed to this series"""
        
        if self._session is None or not self._session.is_authed:
            raise utils.AuthError("You can only get a series ID using an authenticated session")
        
        form = self._soup.find("form", {"data-create-value": "Subscribe"})
        input_ = form.find("input", {"name": "commit", "value": "Unsubscribe"})
        return input_ is not None
    
    @cached_property
    def _sub_id(self):
        """Returns the subscription ID. Used for unsubscribing"""
        
        if not self.is_subscribed:
            raise Exception("You are not subscribed to this series")
        
        form = self._soup.find("form", {"data-create-value": "Subscribe"})
        id_ = form.attrs["action"].split("/")[-1]
        return int(id_)
    
    @cached_property
    def name(self):
        div = self._soup.find("div", {"class": "series-show region"})
        return div.h2.getText().replace("\t", "").replace("\n", "")
        
    @cached_property
    def creators(self):
        dl = self._soup.find("dl", {"class": "series meta group"})
        return [User(author.getText(), load=False) for author in dl.findAll("a", {"rel": "author"})]
    
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
        for work in ul.find_all("li", {"role": "article"}):
            if work.h4 is None:
                continue
            works.append(get_work_from_banner(work))
        #     authors = []
        #     if work.h4 is None:
        #         continue
        #     for a in work.h4.find_all("a"):
        #         if 'rel' in a.attrs.keys():
        #             if "author" in a['rel']:
        #                 authors.append(User(a.string, load=False))
        #         elif a.attrs["href"].startswith("/works"):
        #             workname = a.string
        #             workid = utils.workid_from_url(a['href'])
        #     new = Work(workid, load=False)
        #     setattr(new, "title", workname)
        #     setattr(new, "authors", authors)
        #     works.append(new)
        return works
    
    def get(self, *args, **kwargs):
        """Request a web page and return a Response object"""  
        
        if self._session is None:
            req = requester.request("get", *args, **kwargs)
        else:
            req = requester.request("get", *args, **kwargs, session=self._session.session)
        if req.status_code == 429:
            raise utils.HTTPError("We are being rate-limited. Try again in a while or reduce the number of requests")
        return req

    def request(self, url):
        """Request a web page and return a BeautifulSoup object.

        Args:
            url (str): Url to request

        Returns:
            bs4.BeautifulSoup: BeautifulSoup object representing the requested page's html
        """

        req = self.get(url)
        soup = BeautifulSoup(req.content, "lxml")
        return soup
