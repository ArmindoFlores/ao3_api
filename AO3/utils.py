import requests
from bs4 import BeautifulSoup


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
        if split_url[index+1].isdigit():
            return int(split_url[index+1])
    return

def comment(chapterid, comment_text, sess, oneshot=False, commentid=None, email="", name=""):
    """Leaves a comment on a specific work

    Args:
        chapterid (int): Chapter id
        comment_text (str): Comment text (must have between 1 and 10000 characters)
        oneshot (bool): Should be True if the work has only one chapter. In this case, chapterid becomes workid
        sess (AO3.Session/AO3.GuestSession): Session object to request with.
        commentid (str/int): If specified, the comment is posted as a reply to this comment. Defaults to None.
        email (str): Email to post with. Only used if sess is None. Defaults to "".
        name (str): Name that will appear on the comment. Only used if sess is None. Defaults to "".

    Raises:
        utils.InvalidIdError: Invalid workid
        utils.UnexpectedResponseError: Unknown error
        utils.PseudoError: Couldn't find a valid pseudonym to post under
        utils.DuplicateCommentError: The comment you're trying to post was already posted
        ValueError: Invalid name/email

    Returns:
        requests.models.Response: Response object
    """

    headers = {
        "x-requested-with": "XMLHttpRequest",
        "x-newrelic-id": "VQcCWV9RGwIJVFFRAw==",
        "x-csrf-token": sess.authenticity_token
    }
    
    data = {}
    if oneshot:
        data["work_id"] = str(chapterid)
    else:
        data["chapter_id"] = str(chapterid)
    if commentid is not None:
        data["comment_id"] = commentid
        
    if sess.is_authed:
        if oneshot:
            referer = f"https://archiveofourown.org/works/{chapterid}"
        else:
            referer = f"https://archiveofourown.org/chapters/{chapterid}"
            
        soup = sess.request(referer)            
        pseud = soup.find("input", {"name": "comment[pseud_id]"})
        if pseud is None:
            pseud = soup.find("select", {"name": "comment[pseud_id]"})
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
            "authenticity_token": sess.authenticity_token,
            "comment[pseud_id]": pseud_id,
            "comment[comment_content]": comment_text,
        })
            
    else:
        if email == "" or name == "":
            raise ValueError("You need to specify both an email and a name!")
        
        data.update({
            "authenticity_token": sess.authenticity_token,
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
            raise InvalidIdError(f"Invalid {'workid' if oneshot else 'chapterid'}")
    
    if response.status_code == 422:
        json = response.json()
        if "errors" in json:
            if "auth_error" in json["errors"]:
                raise AuthError("Invalid authentication token. Try calling session.refresh_auth_token()")
        raise UnexpectedResponseError(f"Unexpected json received:\n"+str(json))
    elif response.status_code == 200:
        raise DuplicateCommentError("You have already left this comment here")

    raise UnexpectedResponseError(f"Unexpected HTTP status code received ({response.status_code})")

def delete_comment(commentid, session):
    """Deletes the specified comment

    Args:
        commentid (int/str): Comment id
        session (AO3.Session): Session object

    Raises:
        PermissionError: You don't have permission to delete the comment
        utils.AuthError: Invalid auth token
        utils.UnexpectedResponseError: Unknown error
    """
    
    if not session.is_authed:
        raise PermissionError("You don't have permission to do this")
    
    data = {
        "authenticity_token": session.authenticity_token,
        "_method": "delete"
    }
    
    req = session.post(f"https://archiveofourown.org/comments/{commentid}", data=data, allow_redirects=False)
    if req.status_code == 429:
        raise HTTPError("We are being rate-limited. Try again in a while or reduce the number of requests")
    if req.status_code == 302:
        return
    else:
        soup = BeautifulSoup(req.content, "html.parser")
        if "auth error" in soup.title.getText().lower():
            raise AuthError("Invalid authentication token. Try calling session.refresh_auth_token()")
        else:
            error = soup.find("div", {"id": "main"}).getText()
            if "you don't have permission" in error.lower():
                raise PermissionError("You don't have permission to do this")
    raise UnexpectedResponseError("An unexpected error has occurred")
            
    
def kudos(workid, session):
    """Leave a 'kudos' in a specific work

    Args:
        workid (int/str): ID of the work

    Raises:
        utils.UnexpectedResponseError: Unexpected response received
        utils.InvalidIdError: Invalid workid (work doesn't exist)
        utils.AuthError: Invalid authenticity token

    Returns:
        bool: True if successful, False if you already left kudos there
    """
    
    data = {
        "authenticity_token": session.authenticity_token,
        "kudo[commentable_id]": workid,
        "kudo[commentable_type]": "Work"
    }
    headers = {
        "x-csrf-token": session.authenticity_token,
        "x-requested-with": "XMLHttpRequest",
        "referer": "https://archiveofourown.org/work/{workid}"
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
                raise InvalidIdError("Invalid workid")
        raise UnexpectedResponseError(f"Unexpected json received:\n"+str(json))
    else:
        raise UnexpectedResponseError(f"Unexpected HTTP status code received ({response.status_code})")
