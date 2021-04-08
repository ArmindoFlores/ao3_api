import datetime
from functools import cached_property

import requests
from bs4 import BeautifulSoup

from . import threadable, utils
from .common import get_work_from_banner
from .requester import requester


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
        self._soup_bookmarks = None
        self._works = None
        self._bookmarks = None
        if load:
            self.reload()
            
    def __repr__(self):
        return f"<User [{self.username}]>"
    
    def __eq__(self, other):
        return isinstance(other, __class__) and other.username == self.username
    
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
            token = self._soup_works.find("meta", {"name": "csrf-token"})
            setattr(self, "authenticity_token", token["content"])
           
        @threadable.threadable
        def req_profile(username): 
            self._soup_profile = self.request(f"https://archiveofourown.org/users/{username}/profile")
            token = self._soup_profile.find("meta", {"name": "csrf-token"})
            setattr(self, "authenticity_token", token["content"])

        @threadable.threadable
        def req_bookmarks(username): 
            self._soup_bookmarks = self.request(f"https://archiveofourown.org/users/{username}/bookmarks")
            token = self._soup_bookmarks.find("meta", {"name": "csrf-token"})
            setattr(self, "authenticity_token", token["content"])
            
        rs = [req_works(self.username, threaded=True),
              req_profile(self.username, threaded=True),
              req_bookmarks(self.username, threaded=True)]
        for r in rs:
            r.join()

        self._works = None
        self._bookmarks = None
        
    def get_avatar(self):
        """Returns a tuple containing the name of the file and its data

        Returns:
            tuple: (name: str, img: bytes)
        """
        
        icon = self._soup_profile.find("p", {"class": "icon"})
        src = icon.img.attrs["src"]
        name = src.split("/")[-1].split("?")[0]
        img = self.get(src).content
        return name, img
    
    @threadable.threadable
    def subscribe(self):
        """Subscribes to this user.
        This function is threadable.

        Raises:
            utils.AuthError: Invalid session
        """
        
        if self._session is None or not self._session.is_authed:
            raise utils.AuthError("You can only subscribe to a user using an authenticated session")
        
        utils.subscribe(self, "User", self._session)
        
    @threadable.threadable
    def unsubscribe(self):
        """Unubscribes from this user.
        This function is threadable.

        Raises:
            utils.AuthError: Invalid session
        """
        
        if not self.is_subscribed:
            raise Exception("You are not subscribed to this user")
        if self._session is None or not self._session.is_authed:
            raise utils.AuthError("You can only unsubscribe from a user using an authenticated session")
        
        utils.subscribe(self, "User", self._session, True, self._sub_id)
        
    @property
    def id(self):
        id_ = self._soup_profile.find("input", {"id": "subscription_subscribable_id"})
        return int(id_["value"]) if id_ is not None else None
        
    @cached_property
    def is_subscribed(self):
        """True if you're subscribed to this user"""
        
        if self._session is None or not self._session.is_authed:
            raise utils.AuthError("You can only get a user ID using an authenticated session")
        
        header = self._soup_profile.find("div", {"class": "primary header module"})
        input_ = header.find("input", {"name": "commit", "value": "Unsubscribe"})
        return input_ is not None
    
    @property
    def loaded(self):
        """Returns True if this user has been loaded"""
        return self._soup_profile is not None
    
    # @cached_property
    # def authenticity_token(self):
    #     """Token used to take actions that involve this user"""
        
    #     if not self.loaded:
    #         return None
        
    #     token = self._soup_profile.find("meta", {"name": "csrf-token"})
    #     return token["content"]
    
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
    def _sub_id(self):
        """Returns the subscription ID. Used for unsubscribing"""
        
        if not self.is_subscribed:
            raise Exception("You are not subscribed to this user")
        
        header = self._soup_profile.find("div", {"class": "primary header module"})
        id_ = header.form.attrs["action"].split("/")[-1]
        return int(id_)

    @cached_property
    def works(self):
        """Returns the number of works authored by this user

        Returns:
            int: Number of works
        """

        div = self._soup_works.find("div", {"id": "inner"})
        span = div.find("span", {"class": "current"}).getText().replace("(", "").replace(")", "")
        n = span.split(" ")[1]
        return int(self.str_format(n))   

    @cached_property
    def _works_pages(self):
        pages = self._soup_works.find("ol", {"title": "pagination"})
        if pages is None:
            return 1
        n = 1
        for li in pages.findAll("li"):
            text = li.getText()
            if text.isdigit():
                n = int(text)
        return n
    
    def get_works(self, use_threading=False):
        """
        Get works authored by this user.

        Returns:
            list: List of works
        """
        
        if self._works is None:
            if use_threading:
                self.load_works_threaded()
            else:
                self._works = []
                for page in range(self._works_pages):
                    self._load_works(page=page+1)
        return self._works
    
    @threadable.threadable
    def load_works_threaded(self):
        """
        Get the user's works using threads.
        This function is threadable.
        """ 
        
        threads = []
        self._works = []
        for page in range(self._works_pages):
            threads.append(self._load_works(page=page+1, threaded=True))
        for thread in threads:
            thread.join()

    @threadable.threadable
    def _load_works(self, page=1):
        from .works import Work
        self._soup_works = self.request(f"https://archiveofourown.org/users/{self.username}/works?page={page}")
            
        ol = self._soup_works.find("ol", {"class": "work index group"})

        for work in ol.find_all("li", {"role": "article"}):
            if work.h4 is None:
                continue
            self._works.append(get_work_from_banner(work))

    @cached_property
    def bookmarks(self):
        """Returns the number of works user has bookmarked

        Returns:
            int: Number of bookmarks 
        """

        div = self._soup_bookmarks.find("div", {"id": "inner"})
        span = div.find("span", {"class": "current"}).getText().replace("(", "").replace(")", "")
        n = span.split(" ")[1]
        return int(self.str_format(n))   

    @cached_property
    def _bookmarks_pages(self):
        pages = self._soup_bookmarks.find("ol", {"title": "pagination"})
        if pages is None:
            return 1
        n = 1
        for li in pages.findAll("li"):
            text = li.getText()
            if text.isdigit():
                n = int(text)
        return n

    def get_bookmarks(self, use_threading=False):
        """
        Get this user's bookmarked works. Loads them if they haven't been previously

        Returns:
            list: List of works
        """
        
        if self._bookmarks is None:
            if use_threading:
                self.load_bookmarks_threaded()
            else:
                self._bookmarks = []
                for page in range(self._bookmarks_pages):
                    self._load_bookmarks(page=page+1)
        return self._bookmarks
    
    @threadable.threadable
    def load_bookmarks_threaded(self):
        """
        Get the user's bookmarks using threads.
        This function is threadable.
        """ 
        
        threads = []
        self._bookmarks = []
        for page in range(self._bookmarks_pages):
            threads.append(self._load_bookmarks(page=page+1, threaded=True))
        for thread in threads:
            thread.join()

    @threadable.threadable
    def _load_bookmarks(self, page=1):
        from .works import Work
        self._soup_bookmarks = self.request(f"https://archiveofourown.org/users/{self.username}/bookmarks?page={page}")
            
        ol = self._soup_bookmarks.find("ol", {"class": "bookmark index group"})

        for work in ol.find_all("li", {"role": "article"}):
            authors = []
            if work.h4 is None:
                continue
            self._bookmarks.append(get_work_from_banner(work))
    
    @cached_property
    def bio(self):
        """Returns the user's bio

        Returns:
            str: User's bio
        """

        div = self._soup_profile.find("div", {"class": "bio module"})
        if div is None:
            return ""
        blockquote = div.find("blockquote", {"class": "userstuff"})
        return blockquote.getText() if blockquote is not None else ""    
    
    @cached_property
    def url(self):
        """Returns the URL to the user's profile

        Returns:
            str: user profile URL
        """

        return "https://archiveofourown.org/users/%s"%self.username      

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

    @staticmethod
    def str_format(string):
        """Formats a given string

        Args:
            string (str): String to format

        Returns:
            str: Formatted string
        """

        return string.replace(",", "")

    @property
    def work_pages(self):
        """
        Returns how many pages of works a user has

        Returns:
            int: Amount of pages
        """
        return self._works_pages
