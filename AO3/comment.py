import requests
from bs4 import BeautifulSoup

from . import utils


class Comment:
    """
    AO3 comment object
    """
    
    def __init__(self, comment_id, chapter_id=None, oneshot=False):
        """Creates a new AO3 comment object

        Args:
            comment_id (int/str): Comment id
            chapter_id (int/str, optional): Id of the chapter this comment was posted in. Defaults to None.
            oneshot (bool, optional): Should be True if the work only has one chapter. Defaults to False.
        """
        
        self.comment_id = comment_id
        self.chapter_id = chapter_id
        self.reply_id = None
        self.oneshot = oneshot
        self._cache = {}
        
    def get_text(self, refresh=False):
        """Returns the chapter text, and caches it.

        Args:
            refresh (bool, optional): True to update cache. Defaults to False.

        Returns:
            str: Comment text
        """
        
        if "comment_text" in self._cache and not refresh:
            return self._cache["comment_text"]
        else:
            req = requests.get(f"https://archiveofourown.org/comments/{self.comment_id}")
            soup = BeautifulSoup(req.content, features="html.parser")
            thread = soup.find("ol", {"class": "thread"})
            first = thread.find("li", {"id": f"comment_{self.comment_id}"})
            text = first.blockquote.getText()
            self._cache["comment_text"] = text
            return text
        
    def clear_cache(self):
        """
        Clears the cache
        """
        
        self._cache = {}
        
    def _get_thread(self, parent, soup):
        comments = soup.findAll("li", recursive=False)
        l = [self] if parent is None else []
        for comment in comments:
            if "role" in comment.attrs:
                id_ = int(comment.attrs["id"][8:])
                c = Comment(id_, self.chapter_id)
                c._cache["thread"] = []
                if parent is not None:
                    c.reply_id = parent.comment_id
                    c._cache["comment_text"] = comment.blockquote.getText()
                    l.append(c)
                else:
                    c.reply_id = self.comment_id
                    l[0]._cache["comment_text"] = comment.blockquote.getText()
            else:
                self._get_thread(l[-1], comment.ol)
        if parent is not None:
            parent._cache["thread"] = l
            
    def get_thread_iterator(self, refresh=False):
        """Returns a generator that allows you to iterate through the entire thread

        Args:
            refresh (bool, optional): True to update cache. Defaults to False.

        Returns:
            generator: The generator object
        """
        
        if "thread" in self._cache and not refresh:
            return threadIterator(self)
        else:
            self.get_thread()
            return threadIterator(self)
        
    def get_thread(self, refresh=False):
        """Returns all the replies to this comment, and all subsequent replies recursively.

        Args:
            refresh (bool, optional): True to update cache. Defaults to False.

        Raises:
            utils.InvalidIdError: The specified comment_id was invalud

        Returns:
            list: Thread
        """
        
        if "thread" in self._cache and not refresh:
            return self._cache["thread"]
        else:
            req = requests.get(f"https://archiveofourown.org/comments/{self.comment_id}")
            if req.status_code == 404:
                raise utils.InvalidIdError("Invalid comment id")
            soup = BeautifulSoup(req.content, features="html.parser")
            thread = soup.find("ol", {"class": "thread"})
            first = thread.find("li", {"id": f"comment_{self.comment_id}"})
            text = first.blockquote.getText()
            self._cache["comment_text"] = text
            self._get_thread(None, thread)
            if "thread" in self._cache:
                return self._cache["thread"]
            else:
                self._cache["thread"] = []
                return []
        
    def reply(self, comment_text, session, email="", name=""):
        """[summary]

        Args:
            comment_text ([type]): [description]
            session ([type]): [description]
            email (str, optional): [description]. Defaults to "".
            name (str, optional): [description]. Defaults to "".

        Raises:
            utils.InvalidIdError: Invalid workid
            utils.UnexpectedResponseError: Unknown error
            utils.PseudoError: Couldn't find a valid pseudonym to post under
            utils.DuplicateCommentError: The comment you're trying to post was already posted
            ValueError: Invalid name/email
            ValueError: self.chapter_id cannot be None

        Returns:
            requests.models.Response: Response object
        """
        
        if self.chapter_id is None:
            raise ValueError("self.chapter_id cannot be 'None'")
        return utils.comment(self.chapter_id, comment_text, session, self.oneshot, self.comment_id, email, name)
    
    def delete(self, session):
        """Deletes this comment

        Args:
            session (AO3.Session): A session object
            
        Raises:
            PermissionError: You don't have permission to delete the comment
            utils.AuthError: Invalid auth token
            utils.UnexpectedResponseError: Unknown error
        """
        
        utils.delete_comment(self.comment_id, session)
    
def threadIterator(comment):
    if "thread" not in comment._cache or len(comment._cache["thread"]) == 0:
        yield comment
    else:
        for c in comment._cache["thread"]:
            yield c
            for sub in threadIterator(c):
                if c != sub:
                    yield sub