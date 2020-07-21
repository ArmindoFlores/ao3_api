import requests
from bs4 import BeautifulSoup
from . import utils


class GuestSession:
    """
    AP3 guest session object
    """

    def __init__(self):
        self.is_authed = False
        self.authenticity_token = None
        self.username = ""
        self.session = requests.Session()
        
    def comment(self, chapterid, comment_text, oneshot=False):
        """Leaves a comment on a specific work

        Args:
            chapterid (int): Chapter id
            comment_text (str): Comment text (must have between 1 and 10000 characters)
            oneshot (bool): Should be True if the work has only one chapter. In this case, chapterid becomes workid

        Raises:
            utils.InvalidWorkidError: Invalid workid

        Returns:
            requests.models.Response: Response object
        """
        
        return utils.comment(chapterid, comment_text, self, oneshot)
    
        
    def kudos(self, workid):
        """Leave a 'kudos' in a specific work

        Args:
            workid (int/str): ID of the work

        Raises:
            utils.UnexpectedResponseError: Unexpected response received
            utils.InvalidWorkidError: Invalid workid (work doesn't exist)

        Returns:
            bool: True if successful, False if you already left kudos there
        """
        
        return utils.kudos(workid, self)
        
    def refresh_auth_token(self):
        if self.is_authed:
            req = self.session.get(f"https://archiveofourown.org/users/{self.username}")
        else:
            req = self.session.get("https://archiveofourown.org")
        soup = BeautifulSoup(req.content, "html.parser")
        token = soup.find("input", {"name": "authenticity_token"})
        if token is None:
            return utils.UnexpectedResponseError("Couldn't refresh token")
        self.authenticity_token = token.attrs["value"]
        
    def request(self, url, data={}):
        """Request a web page and return a BeautifulSoup object.

        Args:
            url (str): Url to request
            data (dict, optional): Optional data to send in the request. Defaults to {}.

        Returns:
            bs4.BeautifulSoup: BeautifulSoup object representing the requested page's html
        """

        req = self.session.get(url, data=data)
        content = req.content
        soup = BeautifulSoup(content, "html.parser")
        return soup

    def post(self, *args, **kwargs):
        """Make a post request with the current session

        Returns:
            requests.Request
        """

        return self.session.post(*args, **kwargs)
    
    def __del__(self):
        self.session.close()

class Session(GuestSession):
    """
    AO3 session object
    """

    def __init__(self, username, password):
        """Creates a new AO3 session object

        Args:
            username (str): AO3 username
            password (str): AO3 password

        Raises:
            utils.LoginError: Login was unsucessful (wrong username or password)
        """

        super().__init__()
        self.is_authed = True
        self.username = username
        self.url = "https://archiveofourown.org/users/%s"%self.username
        
        self.session = requests.Session()
        
        soup = self.request("https://archiveofourown.org/users/login")
        self.authenticity_token = soup.find("input", {'name': 'authenticity_token'})['value']
        payload = {'user[login]': username,
                   'user[password]': password,
                   'authenticity_token': self.authenticity_token}
        post = self.session.post("https://archiveofourown.org/users/login", params=payload, allow_redirects=False)
        if not post.status_code == 302:
            raise utils.LoginError("Invalid username or password")

        self._subscriptions_url = "https://archiveofourown.org/users/{0}/subscriptions?type=works&page={1:d}"
        self._bookmarks_url = "https://archiveofourown.org/users/{0}/bookmarks?page={1:d}"

    def get_subscriptions(self, page=1):
        """Get the name of the first 20 work subscriptions. If there are more than 20, you may need to specify the page.
        Must be logged in to use.

        Args:
            page (int, optional): Subscriptions page. Defaults to 1.

        Returns:
            list: List of tuples (workid, workname, authors)
        """
        
        url = self._subscriptions_url.format(self.username, page)
        soup = self.request(url)
        subscriptions = soup.find("dl", {'class': 'subscription index group'})
        subs = []
        for sub in subscriptions.find_all("dt"):
            authors = []
            for a in sub.find_all("a"):
                if 'rel' in a.attrs.keys():
                    if "author" in a['rel']:
                        authors.append(a.string)
                else:
                    workname = a.string
                    workid = utils.workid_from_url(a['href'])
            subs.append((workid, workname, authors))
            
        return subs

    def get_bookmarks(self, page=1):
        """Get the name of the first 20 work bookmarks. If there are more than 20, you may need to specify the page.
        Must be logged in to use.

        Args:
            page (int, optional): Bookmarks page. Defaults to 1.

        Returns:
            list: List of tuples (workid, workname, authors)
        """
        
        url = self._bookmarks_url.format(self.username, page)
        soup = self.request(url)
        bookmarks = soup.find("ol", {'class': 'bookmark index group'})
        bookms = []
        for bookm in bookmarks.find_all("li", {'class': 'bookmark blurb group'}):
            authors = []
            for a in bookm.h4.find_all("a"):
                if 'rel' in a.attrs.keys():
                    if "author" in a['rel']:
                        authors.append(a.string)
                else:
                    workname = a.string
                    workid = utils.workid_from_url(a['href'])
            bookms.append((workid, workname, authors))
            
        return bookms

    def get_n_bookmarks(self):
        """Get the number of your bookmarks.
        Must be logged in to use.

        Returns:
            int: Number of bookmarks
        """

        url = self._bookmarks_url.format(self.username, 1)
        soup = self.request(url)
        div = soup.find("div", {'id': 'inner'})
        span = div.find("span", {'class': 'current'}).getText().replace("(", "").replace(")", "")
        n = span.split(" ")[1]
        
        return int(self.str_format(n))    

    @staticmethod
    def str_format(string):
        """Formats a given string

        Args:
            string (str): String to format

        Returns:
            str: Formatted string
        """

        return string.replace(",", "")
