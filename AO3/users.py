import datetime
from functools import cached_property

import requests
from bs4 import BeautifulSoup

from . import threadable, utils
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
        self._works = None
        if load:
            self.reload()
            
    def __repr__(self):
        return f"<User [{self.username}]>"
    
    def __eq__(self, other):
        return isinstance(other, User) and other.username == self.username
    
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
           
        @threadable.threadable
        def req_profile(username): 
            self._soup_profile = self.request(f"https://archiveofourown.org/users/{username}/profile")
            
        w, p = req_works(self.username, threaded=True), req_profile(self.username, threaded=True)
        w.join()
        p.join()
        self._works = None
        
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
        
        utils.subscribe(self.user_id, "User", self._session)
        
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
        
        utils.subscribe(self.user_id, "User", self._session, True, self._sub_id)
        
    @cached_property
    def is_subscribed(self):
        """True if you're subscribed to this user"""
        
        if self._session is None or not self._session.is_authed:
            raise utils.AuthError("You can only get a user ID using an authenticated session")
        
        header = self._soup_profile.find("div", {"class": "primary header module"})
        input_ = header.find("input", {"name": "commit", "value": "Unsubscribe"})
        return input_ is not None
    
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

        div = self._soup_works.find("div", {'id': 'inner'})
        span = div.find("span", {'class': 'current'}).getText().replace("(", "").replace(")", "")
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
        Get works authored by this user. Loads them if they haven't been previously

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
            
        ol = self._soup_works.find("ol", {'class': 'work index group'})

        for work in ol.find_all("li", {'role': 'article'}):
            authors = []
            for a in work.h4.find_all("a"):
                if 'rel' in a.attrs.keys():
                    if "author" in a['rel']:
                        authors.append(User(a.string, load=False))
                elif a.attrs["href"].startswith("/works"):
                    name = a.string
                    id_ = utils.workid_from_url(a['href'])
            new = Work(id_, load=False)
            setattr(new, "title", name)
            setattr(new, "authors", authors)
            if new not in self._works:
                self._works.append(new)
    
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
