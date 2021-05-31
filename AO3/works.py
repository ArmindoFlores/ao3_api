import warnings
from datetime import datetime
from functools import cached_property

from bs4 import BeautifulSoup

from . import threadable, utils
from .chapters import Chapter
from .comments import Comment
from .requester import requester
from .users import User


class Work:
    """
    AO3 work object
    """

    def __init__(self, workid, session=None, load=True, load_chapters=True):
        """Creates a new AO3 work object

        Args:
            workid (int): AO3 work ID
            session (AO3.Session, optional): Used to access restricted works
            load (bool, optional): If true, the work is loaded on initialization. Defaults to True.
            load_chapters (bool, optional): If false, chapter text won't be parsed, and Work.load_chapters() will have to be called. Defaults to True.

        Raises:
            utils.InvalidIdError: Raised if the work wasn't found
        """

        self._session = session
        self.chapters = []
        self.id = workid
        self._soup = None
        if load:
            self.reload(load_chapters)
            
    def __repr__(self):
        try:
            return f"<Work [{self.title}]>"
        except:
            return f"<Work [{self.id}]>"
    
    def __eq__(self, other):
        return isinstance(other, __class__) and other.id == self.id
    
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
    def reload(self, load_chapters=True):
        """
        Loads information about this work.
        This function is threadable.
        
        Args:
            load_chapters (bool, optional): If false, chapter text won't be parsed, and Work.load_chapters() will have to be called. Defaults to True.
        """
        
        for attr in self.__class__.__dict__:
            if isinstance(getattr(self.__class__, attr), cached_property):
                if attr in self.__dict__:
                    delattr(self, attr)
        
        self._soup = self.request(f"https://archiveofourown.org/works/{self.id}?view_adult=true&view_full_work=true")
        if "Error 404" in self._soup.find("h2", {"class", "heading"}).text:
            raise utils.InvalidIdError("Cannot find work")
        if load_chapters:
            self.load_chapters()
        
    def set_session(self, session):
        """Sets the session used to make requests for this work

        Args:
            session (AO3.Session/AO3.GuestSession): session object
        """
        
        self._session = session 

    def load_chapters(self):
        """Loads chapter objects for each one of this work's chapters
        """
        
        self.chapters = []
        chapters_div = self._soup.find(attrs={"id": "chapters"})
        if chapters_div is None:
            return
        
        if self.nchapters > 1:
            for n in range(1, self.nchapters+1):
                chapter = chapters_div.find("div", {"id": f"chapter-{n}"})
                if chapter is None:
                    continue
                chapter.extract()
                preface_group = chapter.find("div", {"class": ("chapter", "preface", "group")})
                if preface_group is None:
                    continue
                title = preface_group.find("h3", {"class": "title"})
                if title is None:
                    continue
                id_ = int(title.a["href"].split("/")[-1])
                c = Chapter(id_, self, self._session, False)
                c._soup = chapter
                self.chapters.append(c)
        else:
            c = Chapter(None, self, self._session, False)
            c._soup = chapters_div
            self.chapters.append(c)
        
    def get_images(self):
        """Gets all images from this work

        Raises:
            utils.UnloadedError: Raises this error if the work isn't loaded

        Returns:
            dict: key = chapter_n; value = chapter.get_images()
        """
        
        if not self.loaded:
            raise utils.UnloadedError("Work isn't loaded. Have you tried calling Work.reload()?")
        
        chapters = {}
        for chapter in self.chapters:
            images = chapter.get_images()
            if len(images) != 0:
                chapters[chapter.number] = images
        return chapters
            
    def download(self, filetype="PDF"):
        """Downloads this work

        Args:
            filetype (str, optional): Desired filetype. Defaults to "PDF".
            Known filetypes are: AZW3, EPUB, HTML, MOBI, PDF. 

        Raises:
            utils.DownloadError: Raised if there was an error with the download
            utils.UnexpectedResponseError: Raised if the filetype is not available for download

        Returns:
            bytes: File content
        """
        
        if not self.loaded:
            raise utils.UnloadedError("Work isn't loaded. Have you tried calling Work.reload()?")
        download_btn = self._soup.find("li", {"class": "download"})
        for download_type in download_btn.findAll("li"):
            if download_type.a.getText() == filetype.upper():
                url = f"https://archiveofourown.org/{download_type.a.attrs['href']}"
                req = self.get(url)
                if req.status_code == 429:
                    raise utils.HTTPError("We are being rate-limited. Try again in a while or reduce the number of requests")
                if not req.ok:
                    raise utils.DownloadError("An error occurred while downloading the work")
                return req.content
        raise utils.UnexpectedResponseError(f"Filetype '{filetype}' is not available for download")
    
    @threadable.threadable
    def download_to_file(self, filename, filetype="PDF"):
        """Downloads this work and saves it in the specified file.
        This function is threadable.

        Args:
            filename (str): Name of the resulting file
            filetype (str, optional): Desired filetype. Defaults to "PDF".
            Known filetypes are: AZW3, EPUB, HTML, MOBI, PDF.

        Raises:
            utils.DownloadError: Raised if there was an error with the download
            utils.UnexpectedResponseError: Raised if the filetype is not available for download
        """
        with open(filename, "wb") as file:
            file.write(self.download(filetype))
            
    @property
    def metadata(self):
        metadata = {}
        normal_fields = (
            "bookmarks", 
            "categories",
            "nchapters",
            "characters",
            "complete",
            "comments",
            "expected_chapters",
            "fandoms",
            "hits",
            "kudos",
            "language",
            "rating",
            "relationships",
            "restricted",
            "status",
            "summary",
            "tags",
            "title",
            "warnings",
            "id",
            "words"
        )
        string_fields = (
            "date_edited",
            "date_published",
            "date_updated",
        )
        
        for field in string_fields:
            try:
                metadata[field] = str(getattr(self, field))
            except AttributeError:
                pass
            
        for field in normal_fields:
            try:
                metadata[field] = getattr(self, field)
            except AttributeError:
                pass
            
        try:
            metadata["authors"] = list(map(lambda author: author.username, self.authors))
        except AttributeError:
            pass
        try:
            metadata["series"] = list(map(lambda series: series.name, self.series))
        except AttributeError:
            pass
        try:
            metadata["chapter_titles"] = list(map(lambda chapter: chapter.title, self.chapters))
        except AttributeError:
            pass

        return metadata
    
    def get_comments(self, maximum=None):
        """Returns a list of all threads of comments in the work. This operation can take a very long time.
        Because of that, it is recomended that you set a maximum number of comments. 
        Duration: ~ (0.13 * n_comments) seconds or 2.9 seconds per comment page

        Args:
            maximum (int, optional): Maximum number of comments to be returned. None -> No maximum

        Raises:
            ValueError: Invalid chapter number
            IndexError: Invalid chapter number
            utils.UnloadedError: Work isn't loaded

        Returns:
            list: List of comments
        """
        
        if not self.loaded:
            raise utils.UnloadedError("Work isn't loaded. Have you tried calling Work.reload()?")
            
        url = f"https://archiveofourown.org/works/{self.id}?page=%d&show_comments=true&view_adult=true&view_full_work=true"
        soup = self.request(url%1)
        
        pages = 0
        div = soup.find("div", {"id": "comments_placeholder"})
        ol = div.find("ol", {"class": "pagination actions"})
        if ol is None:
            pages = 1
        else:
            for li in ol.findAll("li"):
                if li.getText().isdigit():
                    pages = int(li.getText())   
        
        comments = []
        for page in range(pages):
            if page != 0:
                soup = self.request(url%(page+1))
            ol = soup.find("ol", {"class": "thread"})
            for li in ol.findAll("li", {"role": "article"}, recursive=False):
                if maximum is not None and len(comments) >= maximum:
                    return comments
                id_ = int(li.attrs["id"][8:])
                
                header = li.find("h4", {"class": ("heading", "byline")})
                if header is None or header.a is None:
                    author = None
                else:
                    author = User(str(header.a.text), self._session, False)
                    
                if li.blockquote is not None:
                    text = li.blockquote.getText()
                else:
                    text = ""                  
                
                comment = Comment(id_, self, session=self._session, load=False)           
                setattr(comment, "authenticity_token", self.authenticity_token)
                setattr(comment, "author", author)
                setattr(comment, "text", text)
                comment._thread = None
                comments.append(comment)
        return comments
    
    @threadable.threadable
    def subscribe(self):
        """Subscribes to this work.
        This function is threadable.

        Raises:
            utils.AuthError: Invalid session
        """
        
        if self._session is None or not self._session.is_authed:
            raise utils.AuthError("You can only subscribe to a work using an authenticated session")
        
        utils.subscribe(self, "Work", self._session)
        
    @threadable.threadable
    def unsubscribe(self):
        """Unubscribes from this user.
        This function is threadable.

        Raises:
            utils.AuthError: Invalid session
        """
        
        if not self.is_subscribed:
            raise Exception("You are not subscribed to this work")
        if self._session is None or not self._session.is_authed:
            raise utils.AuthError("You can only unsubscribe from a work using an authenticated session")
        
        utils.subscribe(self, "Work", self._session, True, self._sub_id)
        
    @cached_property
    def text(self):
        """This work's text"""
        
        text = ""
        for chapter in self.chapters:
            text += chapter.text
            text += "\n"
        return text
        
    @cached_property
    def authenticity_token(self):
        """Token used to take actions that involve this work"""
        
        if not self.loaded:
            return None
        
        token = self._soup.find("meta", {"name": "csrf-token"})
        return token["content"]
        
    @cached_property
    def is_subscribed(self):
        """True if you're subscribed to this work"""
        
        if self._session is None or not self._session.is_authed:
            raise utils.AuthError("You can only get a user ID using an authenticated session")
        
        ul = self._soup.find("ul", {"class": "work navigation actions"})
        input_ = ul.find("li", {"class": "subscribe"}).find("input", {"name": "commit", "value": "Unsubscribe"})
        return input_ is not None
    
    @cached_property
    def _sub_id(self):
        """Returns the subscription ID. Used for unsubscribing"""
        
        if self._session is None or not self._session.is_authed:
            raise utils.AuthError("You can only get a user ID using an authenticated session")
        
        ul = self._soup.find("ul", {"class": "work navigation actions"})
        id_ = ul.find("li", {"class": "subscribe"}).form.attrs["action"].split("/")[-1]
        return int(id_)
    
    @threadable.threadable
    def leave_kudos(self):
        """Leave a "kudos" in this work.
        This function is threadable.

        Raises:
            utils.UnexpectedResponseError: Unexpected response received
            utils.InvalidIdError: Invalid ID (work doesn't exist)
            utils.AuthError: Invalid session or authenticity token

        Returns:
            bool: True if successful, False if you already left kudos there
        """
        
        if self._session is None:
            raise utils.AuthError("Invalid session")
        return utils.kudos(self, self._session)
    
    @threadable.threadable
    def comment(self, comment_text, email="", name=""):
        """Leaves a comment on this work.
        This function is threadable.

        Args:
            comment_text (str): Comment text

        Raises:
            utils.UnloadedError: Couldn't load chapters
            utils.AuthError: Invalid session

        Returns:
            requests.models.Response: Response object
        """
        
        if not self.loaded:
            raise utils.UnloadedError("Work isn't loaded. Have you tried calling Work.reload()?")
        
        if self._session is None:
            raise utils.AuthError("Invalid session")
            
        return utils.comment(self, comment_text, self._session, True, email=email, name=name)
    
    @property
    def loaded(self):
        """Returns True if this work has been loaded"""
        return self._soup is not None
    
    @property
    def oneshot(self):
        """Returns True if this work has only one chapter"""
        return self.nchapters == 1
    
    @cached_property
    def series(self):
        """Returns the series this work belongs to"""
        
        from .series import Series
        dd = self._soup.find("dd", {"class": "series"})
        if dd is None:
            return []
        
        s = []
        for span in dd.find_all("span", {"class": "position"}):
            seriesid = int(span.a.attrs["href"].split("/")[-1])
            seriesname = span.a.getText()
            series = Series(seriesid, self._session, False)
            setattr(series, "name", seriesname)
            s.append(series)
        return s

    @cached_property
    def authors(self):
        """Returns the list of the work's author

        Returns:
            list: list of authors
        """

        from .users import User
        authors = self._soup.find_all("h3", {"class": "byline heading"})
        if len(authors) == 0:
            return []
        formatted_authors = authors[0].text.replace("\n", "").split(", ")
        author_list = []
        if authors is not None:
            for author in formatted_authors:
                user = User(author, load=False)
                author_list.append(user)

        return author_list

    @cached_property
    def nchapters(self):
        """Returns the number of chapters of this work

        Returns:
            int: number of chapters
        """
        
        chapters = self._soup.find("dd", {"class": "chapters"})
        if chapters is not None:
            return int(self.str_format(chapters.string.split("/")[0]))
        return 0
    
    @cached_property
    def expected_chapters(self):
        """Returns the number of expected chapters for this work, or None if 
        the author hasn't provided an expected number

        Returns:
            int: number of chapters
        """
        chapters = self._soup.find("dd", {"class": "chapters"})
        if chapters is not None:
            n = self.str_format(chapters.string.split("/")[-1])
            if n.isdigit():
                return int(n)
        return None
    
    @property
    def status(self):
        """Returns the status of this work

        Returns:
            str: work status
        """

        return "Completed" if self.nchapters == self.expected_chapters else "Work in Progress"

    @cached_property
    def hits(self):
        """Returns the number of hits this work has

        Returns:
            int: number of hits
        """

        hits = self._soup.find("dd", {"class": "hits"})
        if hits is not None:
            return int(self.str_format(hits.string))
        return 0

    @cached_property
    def kudos(self):
        """Returns the number of kudos this work has

        Returns:
            int: number of kudos
        """

        kudos = self._soup.find("dd", {"class": "kudos"})
        if kudos is not None:
            return int(self.str_format(kudos.string))
        return 0

    @cached_property
    def comments(self):
        """Returns the number of comments this work has

        Returns:
            int: number of comments
        """

        comments = self._soup.find("dd", {"class": "comments"})
        if comments is not None:
            return int(self.str_format(comments.string))
        return 0
    
    @cached_property
    def restricted(self):
        """Whether this is a restricted work or not
        
        Returns:
            int: True if work is restricted
        """
        return self._soup.find("img", {"title": "Restricted"}) is not None

    @cached_property
    def words(self):
        """Returns the this work's word count

        Returns:
            int: number of words
        """

        words = self._soup.find("dd", {"class": "words"})
        if words is not None:
            return int(self.str_format(words.string))
        return 0

    @cached_property
    def language(self):
        """Returns this work's language

        Returns:
            str: Language
        """

        language = self._soup.find("dd", {"class": "language"})
        if language is not None:
            return language.string.strip()
        else:
            return "Unknown"

    @cached_property
    def bookmarks(self):
        """Returns the number of bookmarks this work has

        Returns:
            int: number of bookmarks
        """

        bookmarks = self._soup.find("dd", {"class": "bookmarks"})
        if bookmarks is not None:
            return int(self.str_format(bookmarks.string))
        return 0

    @cached_property
    def title(self):
        """Returns the title of this work

        Returns:
            str: work title
        """

        title = self._soup.find("div", {"class": "preface group"})
        if title is not None:
            return str(title.h2.text.strip())
        return ""
    
    @cached_property
    def date_published(self):
        """Returns the date this work was published

        Returns:
            datetime.date: publish date
        """

        dp = self._soup.find("dd", {"class": "published"}).string
        return datetime(*list(map(int, dp.split("-"))))

    @cached_property
    def date_edited(self):
        """Returns the date this work was last edited

        Returns:
            datetime.datetime: edit date
        """

        download = self._soup.find("li", {"class": "download"})
        if download is not None and download.ul is not None:
            timestamp = int(download.ul.a["href"].split("=")[-1])
            return datetime.fromtimestamp(timestamp)
        return datetime(self.date_published)

    @cached_property
    def date_updated(self):
        """Returns the date this work was last updated

        Returns:
            datetime.datetime: update date
        """
        update = self._soup.find("dd", {"class": "status"})
        if update is not None:
            split = update.string.split("-")
            return datetime(*list(map(int, split)))
        return self.date_published
    
    @cached_property
    def tags(self):
        """Returns all the work's tags

        Returns:
            list: List of tags
        """

        html = self._soup.find("dd", {"class": "freeform tags"})
        tags = []
        if html is not None:
            for tag in html.find_all("li"):
                tags.append(tag.a.string)
        return tags

    @cached_property
    def characters(self):
        """Returns all the work's characters

        Returns:
            list: List of characters
        """

        html = self._soup.find("dd", {"class": "character tags"})
        characters = []
        if html is not None:
            for character in html.find_all("li"):
                characters.append(character.a.string)
        return characters

    @cached_property
    def relationships(self):
        """Returns all the work's relationships

        Returns:
            list: List of relationships
        """
        
        html = self._soup.find("dd", {"class": "relationship tags"})
        relationships = []
        if html is not None:
            for relationship in html.find_all("li"):
                relationships.append(relationship.a.string)
        return relationships

    @cached_property
    def fandoms(self):
        """Returns all the work's fandoms

        Returns:
            list: List of fandoms
        """

        html = self._soup.find("dd", {"class": "fandom tags"})
        fandoms = []
        if html is not None:
            for fandom in html.find_all("li"):
                fandoms.append(fandom.a.string)
        return fandoms

    @cached_property
    def categories(self):
        """Returns all the work's categories

        Returns:
            list: List of categories
        """

        html = self._soup.find("dd", {"class": "category tags"})
        categories = []
        if html is not None:
            for category in html.find_all("li"):
                categories.append(category.a.string)
        return categories

    @cached_property
    def warnings(self):
        """Returns all the work's warnings

        Returns:
            list: List of warnings
        """

        html = self._soup.find("dd", {"class": "warning tags"})
        warnings = []
        if html is not None:
            for warning in html.find_all("li"):
                warnings.append(warning.a.string)
        return warnings

    @cached_property
    def rating(self):
        """Returns this work's rating

        Returns:
            str: Rating
        """

        html = self._soup.find("dd", {"class": "rating tags"})
        if html is not None:
            rating = html.a.string
            return rating
        return None

    @cached_property
    def summary(self):
        """Returns this work's summary

        Returns:
            str: Summary
        """

        div = self._soup.find("div", {"class": "preface group"})
        if div is None:
            return ""
        html = div.find("blockquote", {"class": "userstuff"})
        if html is None:
            return ""
        return str(BeautifulSoup.getText(html))
    
    @cached_property
    def start_notes(self):
        """Text from this work's start notes"""
        notes = self._soup.find("div", {"class": "notes module"})
        if notes is None:
            return ""
        text = ""
        for p in notes.findAll("p"):
            text += p.getText().strip() + "\n"
        return text

    @cached_property
    def end_notes(self):
        """Text from this work's end notes"""
        notes = self._soup.find("div", {"id": "work_endnotes"})
        if notes is None:
            return ""
        text = ""
        for p in notes.findAll("p"):
            text += p.getText() + "\n"
        return text
    
    @cached_property
    def url(self):
        """Returns the URL to this work

        Returns:
            str: work URL
        """    

        return "https://archiveofourown.org/works/%i"%self.id

    @cached_property
    def complete(self):
        """
        Return True if the work is complete

        Retuns:
            bool: True if a work is complete
        """

        chapterStatus = self._soup.find("dd", {"class": "chapters"}).string.split("/")
        return chapterStatus[0] == chapterStatus[1]
    
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
        if len(req.content) > 650000:
            warnings.warn("This work is very big and might take a very long time to load")
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
