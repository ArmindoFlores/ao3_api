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
        
        self.id = seriesid
        self._session = session
        self._soup = None
        if load:
            self.reload()
            
    def __eq__(self, other):
        return isinstance(other, __class__) and other.id == self.id
    
    def __repr__(self):
        try:
            return f"<Series [{self.name}]>" 
        except:
            return f"<Series [{self.id}]>"
        
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
                
    def set_session(self, session):
        """Sets the session used to make requests for this series

        Args:
            session (AO3.Session/AO3.GuestSession): session object
        """
        
        self._session = session 
        
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
                    
        self._soup = self.request(f"https://archiveofourown.org/series/{self.id}")
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
        
        utils.subscribe(self, "Series", self._session)
        
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
        
        utils.subscribe(self, "Series", self._session, True, self._sub_id)
        
    @threadable.threadable
    def bookmark(self, notes="", tags=None, collections=None, private=False, recommend=False, pseud=None):
        """Bookmarks this series
        This function is threadable

        Args:
            notes (str, optional): Bookmark notes. Defaults to "".
            tags (list, optional): What tags to add. Defaults to None.
            collections (list, optional): What collections to add this bookmark to. Defaults to None.
            private (bool, optional): Whether this bookmark should be private. Defaults to False.
            recommend (bool, optional): Whether to recommend this bookmark. Defaults to False.
            pseud (str, optional): What pseud to add the bookmark under. Defaults to default pseud.

        Raises:
            utils.UnloadedError: Series isn't loaded
            utils.AuthError: Invalid session
        """
        
        if not self.loaded:
            raise utils.UnloadedError("Series isn't loaded. Have you tried calling Series.reload()?")
        
        if self._session is None:
            raise utils.AuthError("Invalid session")
        
        utils.bookmark(self, self._session, notes, tags, collections, private, recommend, pseud)
        
    @threadable.threadable
    def delete_bookmark(self):
        """Removes a bookmark from this series
        This function is threadable

        Raises:
            utils.UnloadedError: Series isn't loaded
            utils.AuthError: Invalid session
        """
        
        if not self.loaded:
            raise utils.UnloadedError("Series isn't loaded. Have you tried calling Series.reload()?")
        
        if self._session is None:
            raise utils.AuthError("Invalid session")
        
        if self._bookmarkid is None:
            raise utils.BookmarkError("You don't have a bookmark here")
        
        utils.delete_bookmark(self._bookmarkid, self._session, self.authenticity_token)
        
    @cached_property
    def _bookmarkid(self):
        form_div = self._soup.find("div", {"id": "bookmark-form"})
        if form_div is None: 
            return None
        if form_div.form is None:
            return None
        if "action" in form_div.form and form_div.form["action"].startswith("/bookmark"):
            text = form_div.form["action"].split("/")[-1]
            if text.isdigit():
                return int(text)
            return None
        return None
        
    @cached_property
    def url(self):
        """Returns the URL to this series

        Returns:
            str: series URL
        """    

        return f"https://archiveofourown.org/series/{self.id}"
        
    @property
    def loaded(self):
        """Returns True if this series has been loaded"""
        return self._soup is not None
        
    @cached_property
    def authenticity_token(self):
        """Token used to take actions that involve this work"""
        
        if not self.loaded:
            return None
        
        token = self._soup.find("meta", {"name": "csrf-token"})
        return token["content"]
        
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
        book = "0"
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
        #         if "rel" in a.attrs.keys():
        #             if "author" in a["rel"]:
        #                 authors.append(User(a.string, load=False))
        #         elif a.attrs["href"].startswith("/works"):
        #             workname = a.string
        #             workid = utils.workid_from_url(a["href"])
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
