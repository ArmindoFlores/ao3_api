import os
import pickle
import re

import requests
from bs4 import BeautifulSoup

from .requester import requester

_FANDOMS = None
_LANGUAGES = None

class LoginError(Exception):
    def __init__(self, message, errors=[]):
        super().__init__(message)
        self.errors = errors

class UnloadedError(Exception):
    def __init__(self, message, errors=[]):
        super().__init__(message)
        self.errors = errors
        
class UnexpectedResponseError(Exception):
    def __init__(self, message, errors=[]):
        super().__init__(message)
        self.errors = errors
        
class InvalidIdError(Exception):
    def __init__(self, message, errors=[]):
        super().__init__(message)
        self.errors = errors
        
class DownloadError(Exception):
    def __init__(self, message, errors=[]):
        super().__init__(message)
        self.errors = errors
        
class AuthError(Exception):
    def __init__(self, message, errors=[]):
        super().__init__(message)
        self.errors = errors 
        
class DuplicateCommentError(Exception):
    def __init__(self, message, errors=[]):
        super().__init__(message)
        self.errors = errors
        
class PseudError(Exception):
    def __init__(self, message, errors=[]):
        super().__init__(message)
        self.errors = errors
        
class HTTPError(Exception):
    def __init__(self, message, errors=[]):
        super().__init__(message)
        self.errors = errors

class Query:
    def __init__(self):
        self.fields = []
    
    def add_field(self, text):
        self.fields.append(text)

    @property
    def string(self):
        return '&'.join(self.fields)


class Constraint:
    """Represents a bounding box of a value
    """

    def __init__(self, lowerbound=0, upperbound=None):
        """Creates a new Constraint object

        Args:
            lowerbound (int, optional): Constraint lowerbound. Defaults to 0.
            upperbound (int, optional): Constraint upperbound. Defaults to None.
        """
        
        self._lb = lowerbound
        self._ub = upperbound

    @property
    def string(self):
        """Returns the string representation of this constraint

        Returns:
            str: string representation
        """

        if self._lb == 0:
            return f"<{self._ub}"
        elif self._ub is None:
            return f">{self._lb}"
        elif self._ub == self._lb:
            return str(self._lb)
        else:
            return f"{self._lb}-{self._ub}"

    def __str__(self):
        return self.string
    
def word_count(text):
    return len(tuple(filter(lambda w: w != "", re.split(" |\n|\t", text))))
    
def set_rqtw(value):
    """Sets the requests per time window parameter for the AO3 requester"""
    requester.setRQTW(value)
    
def set_timew(value):
    """Sets the time window parameter for the AO3 requester"""
    requester.setTimeW(value)
        
def limit_requests(limit=True):
    """Toggles request limiting"""
    if limit:
        requester.setRQTW(12)
    else:
        requester.setRQTW(-1)
    
def load_fandoms():
    """Loads fandoms into memory

    Raises:
        FileNotFoundError: No resource was found
    """
    
    global _FANDOMS
    
    fandom_path = os.path.join(os.path.dirname(__file__), "resources", "fandoms")
    if not os.path.isdir(fandom_path):
        raise FileNotFoundError("No fandom resources have been downloaded. Try AO3.extra.download()")
    files = os.listdir(fandom_path)
    _FANDOMS = []
    for file in files:
        with open(os.path.join(fandom_path, file), "rb") as f:
            _FANDOMS += pickle.load(f)
            
def load_languages():
    """Loads languages into memory

    Raises:
        FileNotFoundError: No resource was found
    """
    
    global _LANGUAGES
    
    language_path = os.path.join(os.path.dirname(__file__), "resources", "languages")
    if not os.path.isdir(language_path):
        raise FileNotFoundError("No language resources have been downloaded. Try AO3.extra.download()")
    files = os.listdir(language_path)
    _LANGUAGES = []
    for file in files:
        with open(os.path.join(language_path, file), "rb") as f:
            _LANGUAGES += pickle.load(f)
            
def get_languages():
    """Returns all available languages"""
    return _LANGUAGES[:]

def search_fandom(fandom_string):
    """Searches for a fandom that matches the given string

    Args:
        fandom_string (str): query string

    Raises:
        UnloadedError: load_fandoms() wasn't called
        UnloadedError: No resources were downloaded

    Returns:
        list: All results matching 'fandom_string'
    """
    
    if _FANDOMS is None:
        raise UnloadedError("Did you forget to call AO3.utils.load_fandoms()?")
    if _FANDOMS == []:
        raise UnloadedError("Did you forget to download the required resources with AO3.extra.download()?")
    results = []
    for fandom in _FANDOMS:
        if fandom_string.lower() in fandom.lower():
            results.append(fandom)
    return results
        
def workid_from_url(url):
    """Get the workid from an archiveofourown.org website url

    Args:
        url (str): Work URL 

    Returns:
        int: Work ID
    """
    split_url = url.split("/")
    try:
        index = split_url.index("works")
    except ValueError:
        return
    if len(split_url) >= index+1:
        workid = split_url[index+1].split("?")[0]
        if workid.isdigit():
            return int(workid)
    return

def comment(commentable, comment_text, sess, fullwork=False, commentid=None, email="", name=""):
    """Leaves a comment on a specific work

    Args:
        commentable (Work/Chapter): Chapter/Work object
        comment_text (str): Comment text (must have between 1 and 10000 characters)
        fullwork (bool): Should be True if the work has only one chapter or if the comment is to be posted on the full work.
        sess (AO3.Session/AO3.GuestSession): Session object to request with.
        commentid (str/int): If specified, the comment is posted as a reply to this comment. Defaults to None.
        email (str): Email to post with. Only used if sess is None. Defaults to "".
        name (str): Name that will appear on the comment. Only used if sess is None. Defaults to "".

    Raises:
        utils.InvalidIdError: Invalid ID
        utils.UnexpectedResponseError: Unknown error
        utils.PseudoError: Couldn't find a valid pseudonym to post under
        utils.DuplicateCommentError: The comment you're trying to post was already posted
        ValueError: Invalid name/email

    Returns:
        requests.models.Response: Response object
    """

    if commentable.authenticity_token is not None:
        at = commentable.authenticity_token
    else:
        at = sess.authenticity_token
    headers = {
        "x-requested-with": "XMLHttpRequest",
        "x-newrelic-id": "VQcCWV9RGwIJVFFRAw==",
        "x-csrf-token": at
    }
    
    data = {}
    if fullwork:
        data["work_id"] = str(commentable.id)
    else:
        data["chapter_id"] = str(commentable.id)
    if commentid is not None:
        data["comment_id"] = commentid
        
    if sess.is_authed:
        if fullwork:
            referer = f"https://archiveofourown.org/works/{commentable.id}"
        else:
            referer = f"https://archiveofourown.org/chapters/{commentable.id}"
            
        soup = sess.request(referer)   
        pseud = soup.find("input", {"name": "comment[pseud_id]"})
        if pseud is None:
            pseud = soup.find("select", {"name": "comment[pseud_id]"})
            if pseud is None:
                raise PseudError("Couldn't find your pseud's id")
            pseud_id = None
            for option in pseud.findAll("option"):
                if "selected" in option.attrs and option.attrs["selected"] == "selected":
                    pseud_id = option.attrs["value"]
                    break
        else:
            pseud_id = pseud.attrs["value"]
            
        if pseud_id is None:
            raise PseudError("Couldn't find your pseud's id")
            
        data.update({
            "authenticity_token": at,
            "comment[pseud_id]": pseud_id,
            "comment[comment_content]": comment_text,
        })
            
    else:
        if email == "" or name == "":
            raise ValueError("You need to specify both an email and a name!")
        
        data.update({
            "authenticity_token": at,
            "comment[email]": email,
            "comment[name]": name,
            "comment[comment_content]": comment_text,
        })

    response = sess.post(f"https://archiveofourown.org/comments.js", headers=headers, data=data)
    if response.status_code == 429:
        raise HTTPError("We are being rate-limited. Try again in a while or reduce the number of requests")
    if response.status_code == 404:
        if len(response.content) > 0:
            return response
        else:
            raise InvalidIdError(f"Invalid {'work ID' if fullwork else 'chapter ID'}")
    
    if response.status_code == 422:
        json = response.json()
        if "errors" in json:
            if "auth_error" in json["errors"]:
                raise AuthError("Invalid authentication token. Try calling session.refresh_auth_token()")
        raise UnexpectedResponseError(f"Unexpected json received:\n"+str(json))
    elif response.status_code == 200:
        raise DuplicateCommentError("You have already left this comment here")

    raise UnexpectedResponseError(f"Unexpected HTTP status code received ({response.status_code})")

def delete_comment(comment, session):
    """Deletes the specified comment

    Args:
        comment (AO3.Comment): Comment object
        session (AO3.Session): Session object

    Raises:
        PermissionError: You don't have permission to delete the comment
        utils.AuthError: Invalid auth token
        utils.UnexpectedResponseError: Unknown error
    """
    
    if session is None or not session.is_authed:
        raise PermissionError("You don't have permission to do this")
    
    if comment.authenticity_token is not None:
        at = comment.authenticity_token
    else:
        at = session.authenticity_token
    
    data = {
        "authenticity_token": at,
        "_method": "delete"
    }
    
    req = session.post(f"https://archiveofourown.org/comments/{comment.id}", data=data)
    if req.status_code == 429:
        raise HTTPError("We are being rate-limited. Try again in a while or reduce the number of requests")
    else:
        soup = BeautifulSoup(req.content, "lxml")
        if "auth error" in soup.title.getText().lower():
            raise AuthError("Invalid authentication token. Try calling session.refresh_auth_token()")
        else:
            error = soup.find("div", {"id": "main"}).getText()
            if "you don't have permission" in error.lower():
                raise PermissionError("You don't have permission to do this")
            
def kudos(work, session):
    """Leave a 'kudos' in a specific work

    Args:
        work (Work): Work object

    Raises:
        utils.UnexpectedResponseError: Unexpected response received
        utils.InvalidIdError: Invalid ID (work doesn't exist)
        utils.AuthError: Invalid authenticity token

    Returns:
        bool: True if successful, False if you already left kudos there
    """
    
    if work.authenticity_token is not None:
        at = work.authenticity_token
    else:
        at = session.authenticity_token
    data = {
        "authenticity_token": at,
        "kudo[commentable_id]": work.id,
        "kudo[commentable_type]": "Work"
    }
    headers = {
        "x-csrf-token": work.authenticity_token,
        "x-requested-with": "XMLHttpRequest",
        "referer": f"https://archiveofourown.org/work/{work.id}"
    }
    response = session.post("https://archiveofourown.org/kudos.js", headers=headers, data=data)
    if response.status_code == 429:
        raise HTTPError("We are being rate-limited. Try again in a while or reduce the number of requests")
    
    if response.status_code == 201:
        return True  # Success
    elif response.status_code == 422:
        json = response.json()
        if "errors" in json:
            if "auth_error" in json["errors"]:
                raise AuthError("Invalid authentication token. Try calling session.refresh_auth_token()")
            elif "user_id" in json["errors"] or "ip_address" in json["errors"]:
                return False  # User has already left kudos
            elif "no_commentable" in json["errors"]:
                raise InvalidIdError("Invalid ID")
        raise UnexpectedResponseError(f"Unexpected json received:\n"+str(json))
    else:
        raise UnexpectedResponseError(f"Unexpected HTTP status code received ({response.status_code})")
    
def subscribe(subscribable, worktype, session, unsubscribe=False, subid=None):
    """Subscribes to a work. Be careful, you can subscribe to a work multiple times

    Args:
        subscribable (Work/Series/User): AO3 object
        worktype (str): Type of the work (Series/Work/User)
        session (AO3.Session): Session object
        unsubscribe (bool, optional): Unsubscribe instead of subscribing. Defaults to False.
        subid (str/int, optional): Subscription ID, used when unsubscribing. Defaults to None.

    Raises:
        AuthError: Invalid auth token
        AuthError: Invalid session
        InvalidIdError: Invalid ID / worktype
        InvalidIdError: Invalid subid
    """
    
    if session is None or not session.is_authed:
        raise AuthError("Invalid session")
    
    if subscribable.authenticity_token is not None:
        at = subscribable.authenticity_token
    else:
        at = session.authenticity_token
    
    data = {
        "authenticity_token": at,
        "subscription[subscribable_id]": subscribable.id,
        "subscription[subscribable_type]": worktype.capitalize()
    }

    url = f"https://archiveofourown.org/users/{session.username}/subscriptions"
    if unsubscribe:
        if subid is None:
            raise InvalidIdError("When unsubscribing, subid cannot be None")
        url += f"/{subid}"
        data["_method"] = "delete"
    req = session.session.post(url, data=data, allow_redirects=False)
    if unsubscribe:
        return req
    if req.status_code == 302:
        if req.headers["Location"] == "https://archiveofourown.org/auth_error":
            raise AuthError("Invalid authentication token. Try calling session.refresh_auth_token()")
    else:
        raise InvalidIdError(f"Invalid ID / worktype")
