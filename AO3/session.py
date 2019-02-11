import requests
from bs4 import BeautifulSoup
from . import utils


class Session:
    def __init__(self, username, password):
        self.username = username
        self.url = "https://archiveofourown.org/users/%s"%self.username
        
        self.session = requests.Session()
        
        soup = self.request("https://archiveofourown.org/users/login")
        self.token = soup.find("input", {'name': 'authenticity_token'})['value']
        payload = {'user[login]': username,
                   'user[password]': password,
                   'authenticity_token': self.token}
        post = self.session.post("https://archiveofourown.org/users/login", params=payload)
        if not "Successfully logged in" in str(post.content):
            raise utils.LoginError("Invalid username or password")

        self._subscriptions_url = "https://archiveofourown.org/users/{0}/subscriptions?type=works&page={1:d}"
        self._bookmarks_url = "https://archiveofourown.org/users/{0}/bookmarks?page={1:d}"

    def __del__(self):
        self.session.close()

    def get_subscriptions(self, page=1):
        """Get the name of the first 20 work subscriptions. If there are more than 20, you may need to specify the page.
        Must be logged in to use."""
        
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
        Must be logged in to use."""
        
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
        """Get the number of bookmarks.
        Must be logged in to use."""

        url = self._bookmarks_url.format(self.username, 1)
        soup = self.request(url)
        h2 = soup.find("div", {'id': 'main'}).h2.string.strip()
        n = h2.split(" ")[0]
        
        return int(self.str_format(n))

        
    def request(self, url, data={}):
        """Request a web page and return a BeautifulSoup object."""
        req = self.session.get(url, data=data)
        content = req.content
        soup = BeautifulSoup(content, "html.parser")
        return soup

    def post(self, *args, **kwargs):
        return self.session.post(*args, **kwargs)

    @staticmethod
    def str_format(string):
        return string.replace(",", "")
