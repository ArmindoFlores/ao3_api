import warnings
from datetime import datetime
from functools import cached_property

from bs4 import BeautifulSoup

from . import threadable, utils
from .chapters import Chapter
from .comments import Comment
from .requester import requester
from .series import Series
from .users import User


class Work:
    """
    AO3 work object
    """

    def __init__(self, workid, session=None, load=True, metadata_only=True):
        """Creates a new AO3 work object

        Args:
            workid (int): AO3 work ID
            session (AO3.Session, optional): Used to access restricted works
            load (bool, optional): If true, the work is loaded on initialization. Defaults to True.
            metadata_only (bool, optional): If false, only the first chapter will be loaded, which excludes chapters, text, images, and comments. Defaults to True.

        Raises:
            utils.InvalidIdError: Raised if the work wasn't found
        """

        self._session = session
        self._chapters = []
        self.id = workid

        self._download_links = None
        self._authenticity_token = None
        self._is_subscribed = None
        self._sub_id = None
        self._bookmarkid = None
        self._series = None
        self._authors = None
        self._nchapters = None
        self._expected_chapters = None
        self._hits = None
        self._kudos = None
        self._comments = None
        self._restricted = None
        self._words = None
        self._language = None
        self._bookmarks = None
        self._title = None
        self._date_published = None
        self._date_edited = None
        self._date_updated = None
        self._tags = None
        self._characters = None
        self._relationships = None
        self._fandoms = None
        self._categories = None
        self._warnings = None
        self._ratings = None
        self._summary = None
        self._start_notes = None
        self._end_notes = None
        self._complete = None

        self._loaded = False
        self._fully_loaded = False
        if load:
            self.reload(metadata_only)

    def __repr__(self):
        try:
            return f"<Work [{self.title}]>"
        except:
            return f"<Work [{self.id}]>"

    def __eq__(self, other):
        return isinstance(other, __class__) and other.id == self.id

    def __getstate__(self):
        state_dict = {}
        for attr in self.__dict__:
            if isinstance(self.__dict__[attr], BeautifulSoup):
                state_dict[attr] = (self.__dict__[attr].encode(), True)
            else:
                state_dict[attr] = (self.__dict__[attr], False)
        return state_dict

    def __setstate__(self, d):
        for attr in d:
            value, issoup = d[attr]
            if issoup:
                self.__dict__[attr] = BeautifulSoup(value, "lxml")
            else:
                self.__dict__[attr] = value

    @threadable.threadable
    def reload(self, metadata_only=True):
        """
        Loads information about this work.
        This function is threadable.

        Args:
            metadata_only (bool, optional): If false, only the first chapter will be loaded, which excludes chapters, text, images, and comments. Defaults to True.
        """

        for attr in self.__class__.__dict__:
            if isinstance(getattr(self.__class__, attr), (property, cached_property)):
                if attr in self.__dict__:
                    delattr(self, attr)

        work_url = f"https://archiveofourown.org/works/{self.id}?view_adult=true&view_full_work={'false' if metadata_only else 'true'}"
        soup = self.request(work_url)
        if "Error 404" in soup.find("h2", {"class", "heading"}).text:
            raise utils.InvalidIdError("Cannot find work")

        first_chapter_loaders = (
            self._load_authenticity_token,
            self._load_authors,
            self._load_bookmarks,
            self._load_categories,
            self._load_characters,
            self._load_comments,
            self._load_complete,
            self._load_date_edited,
            self._load_date_published,
            self._load_date_updated,
            self._load_expected_chapters,
            self._load_fandoms,
            self._load_hits,
            self._load_is_subscribed,
            self._load_kudos,
            self._load_language,
            self._load_nchapters,
            self._load_ratings,
            self._load_relationships,
            self._load_restricted,
            self._load_series,
            self._load_start_notes,
            self._load_summary,
            self._load_tags,
            self._load_title,
            self._load_warnings,
            self._load_words,
        )

        full_work_loaders = (
            self._load_end_notes,
            # self._load_text, # can keep this dynamic if load_chapters is default
            self._load_chapters,  # Not sure if this should be done by default. The alternative is the fetch the work again
        )

        for loader in first_chapter_loaders:
            loader(soup)
        self._loaded = True

        if not metadata_only:
            for loader in full_work_loaders:
                loader(soup)
            self._fully_loaded = True

    def set_session(self, session):
        """Sets the session used to make requests for this work

        Args:
            session (AO3.Session/AO3.GuestSession): session object
        """

        self._session = session

    def _load_chapters(self, soup: BeautifulSoup):
        """Loads chapter objects for each one of this work's chapters"""
        # TODO: call reload() or raise an error?

        self._chapters = []
        chapters_div = soup.find(attrs={"id": "chapters"})
        if chapters_div is None:
            return

        if self.nchapters > 1:
            for chapter_num in range(1, self.nchapters + 1):
                chapter_content = chapters_div.find(
                    "div", {"id": f"chapter-{chapter_num}"}
                )
                if chapter_content is None:
                    continue
                chapter_content.extract()
                preface_group = chapter_content.find(
                    "div", {"class": ("chapter", "preface", "group")}
                )
                if preface_group is None:
                    continue
                title = preface_group.find("h3", {"class": "title"})
                if title is None:
                    continue
                id_ = int(title.a["href"].split("/")[-1])
                chapter = Chapter(id_, self, self._session, False)
                chapter._soup = chapter_content
                self._chapters.append(chapter)
        else:
            chapter = Chapter(None, self, self._session, False)
            chapter._soup = chapters_div
            self._chapters.append(chapter)

    def get_images(self):
        """Gets all images from this work

        Raises:
            utils.UnloadedError: Raises this error if the work isn't loaded

        Returns:
            dict: key = chapter_n; value = chapter.get_images()
        """

        if not self.loaded:
            raise utils.UnloadedError(
                "Work isn't loaded. Have you tried calling Work.reload()?"
            )

        chapters = {}
        for chapter in self._chapters:
            images = chapter.get_images()
            if len(images) != 0:
                chapters[chapter.number] = images
        return chapters

    def _load_download_links(self, soup: BeautifulSoup):
        """Loads download links from soup"""
        download_btn = soup.find("li", {"class": "download"})
        self._download_links = {
            download_type.get_text(): f"https://archiveofourown.org/{download_type.a.attrs['href']}"
            for download_type in download_btn.find_all("li")
        }

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
        self._raise_if_unloaded()

        filetype = filetype.upper()
        if filetype not in self._download_links:
            raise utils.UnexpectedResponseError(
                f"Filetype '{filetype}' is not available for download"
            )

        req = self.get(self._download_links[filetype])
        if req.status_code == 429:
            raise utils.HTTPError(
                "We are being rate-limited. Try again in a while or reduce the number of requests"
            )
        if not req.ok:
            raise utils.DownloadError("An error occurred while downloading the work")
        return req.content

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
        """Get the metadata of a work.

        This metadata is what one might see in the serach results of AO3
        """
        self._raise_if_unloaded()
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
            "words",
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
            metadata["authors"] = list(
                map(lambda author: author.username, self.authors)
            )
        except AttributeError:
            pass
        try:
            metadata["series"] = list(map(lambda series: series.name, self.series))
        except AttributeError:
            pass
        try:
            metadata["chapter_titles"] = list(
                map(lambda chapter: chapter.title, self._chapters)
            )
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

        self._raise_if_unloaded()

        url = f"https://archiveofourown.org/works/{self.id}?page=%d&show_comments=true&view_adult=true&view_full_work=true"
        soup = self.request(url % 1)

        pages = 0
        div = soup.find("div", {"id": "comments_placeholder"})
        action_list = div.find("ol", {"class": "pagination actions"})
        if action_list is None:
            pages = 1
        else:
            for list_item in action_list.findAll("li"):
                if list_item.getText().isdigit():
                    pages = int(list_item.getText())

        comments = []
        for page in range(pages):
            if page != 0:
                soup = self.request(url % (page + 1))
            action_list = soup.find("ol", {"class": "thread"})
            for list_item in action_list.findAll(
                "li", {"role": "article"}, recursive=False
            ):
                if maximum is not None and len(comments) >= maximum:
                    return comments
                id_ = int(list_item.attrs["id"][8:])

                header = list_item.find("h4", {"class": ("heading", "byline")})
                if header is None or header.a is None:
                    author = None
                else:
                    author = User(str(header.a.text), self._session, False)

                if list_item.blockquote is not None:
                    text = list_item.blockquote.getText()
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
            raise utils.AuthError(
                "You can only subscribe to a work using an authenticated session"
            )

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
            raise utils.AuthError(
                "You can only unsubscribe from a work using an authenticated session"
            )

        utils.subscribe(self, "Work", self._session, True, self._sub_id)

    @cached_property
    def text(self):
        """This work's text"""
        self._raise_if_unloaded()

        text = ""
        for chapter in self._chapters:
            text += chapter.text
            text += "\n"
        return text

    def _load_authenticity_token(self, soup: BeautifulSoup):
        """Load authenticity token from soup"""
        token = soup.find("meta", {"name": "csrf-token"})
        self._authenticity_token = token["content"]

    @property
    def authenticity_token(self):
        """Token used to take actions that involve this work"""
        self._raise_if_unloaded()
        return self._authenticity_token

    def _load_is_subscribed(self, soup: BeautifulSoup):
        "Load subscription status from soup" ""
        if not self._is_authenticated:
            return

        unordered_list = soup.find("ul", {"class": "work navigation actions"})
        input_ = unordered_list.find("li", {"class": "subscribe"}).find(
            "input", {"name": "commit", "value": "Unsubscribe"}
        )
        self._is_subscribed = input_ is not None

    @property
    def is_subscribed(self):
        """True if you're subscribed to this work"""

        if not self._is_authenticated:
            raise utils.AuthError(
                "You can only get a user ID using an authenticated session"
            )

        self._raise_if_unloaded()
        return self._is_subscribed

    def _load_sub_id(self, soup: BeautifulSoup):
        """Load subscription IF from soup"""
        if not self._is_authenticated:
            return
        unordered_list = soup.find("ul", {"class": "work navigation actions"})
        id_ = (
            unordered_list.find("li", {"class": "subscribe"})
            .form.attrs["action"]
            .split("/")[-1]
        )
        self._sub_id = int(id_)

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
    def comment(self, comment_text, email="", name="", pseud=None):
        """Leaves a comment on this work.
        This function is threadable.

        Args:
            comment_text (str): Comment text
            email (str, optional): Email to add comment. Needed if not logged in.
            name (str, optional): Name to add comment under. Needed if not logged in.
            pseud (str, optional): Pseud to add the comment under. Defaults to default pseud.

        Raises:
            utils.UnloadedError: Couldn't load chapters
            utils.AuthError: Invalid session

        Returns:
            requests.models.Response: Response object
        """

        if not self.loaded:
            raise utils.UnloadedError(
                "Work isn't loaded. Have you tried calling Work.reload()?"
            )

        if self._session is None:
            raise utils.AuthError("Invalid session")

        return utils.comment(
            self, comment_text, self._session, True, email=email, name=name, pseud=pseud
        )

    @threadable.threadable
    def bookmark(
        self,
        notes="",
        tags=None,
        collections=None,
        private=False,
        recommend=False,
        pseud=None,
    ):
        """Bookmarks this work
        This function is threadable

        Args:
            notes (str, optional): Bookmark notes. Defaults to "".
            tags (list, optional): What tags to add. Defaults to None.
            collections (list, optional): What collections to add this bookmark to. Defaults to None.
            private (bool, optional): Whether this bookmark should be private. Defaults to False.
            recommend (bool, optional): Whether to recommend this bookmark. Defaults to False.
            pseud (str, optional): What pseud to add the bookmark under. Defaults to default pseud.

        Raises:
            utils.UnloadedError: Work isn't loaded
            utils.AuthError: Invalid session
        """

        if not self.loaded:
            raise utils.UnloadedError(
                "Work isn't loaded. Have you tried calling Work.reload()?"
            )

        if self._session is None:
            raise utils.AuthError("Invalid session")

        utils.bookmark(
            self, self._session, notes, tags, collections, private, recommend, pseud
        )

    @threadable.threadable
    def delete_bookmark(self):
        """Removes a bookmark from this work
        This function is threadable

        Raises:
            utils.UnloadedError: Work isn't loaded
            utils.AuthError: Invalid session
        """

        self._raise_if_unloaded()

        if self._session is None:
            raise utils.AuthError("Invalid session")

        if self._bookmarkid is None:
            raise utils.BookmarkError("You don't have a bookmark here")

        utils.delete_bookmark(self._bookmarkid, self._session, self.authenticity_token)

    def _load_bookmardid(self, soup: BeautifulSoup):
        """Returns the bookmark ID. Used for bookmarking"""
        form_div = soup.find("div", {"id": "bookmark-form"})
        if form_div is None or form_div.form is None:
            self._bookmarkid = None
            return
        if "action" in form_div.form.attrs and form_div.form["action"].startswith(
            "/bookmarks"
        ):
            text = form_div.form["action"].split("/")[-1]
            if text.isdigit():
                self._bookmarkid = int(text)
            self._bookmarkid = None
        self._bookmarkid = None

    @property
    def loaded(self):
        """Returns True if this work has been loaded"""
        return self._loaded

    @property
    def entire_work_loaded(self):
        """Returns if the entire work has been loaded"""
        return self._fully_loaded

    @property
    def chapters(self):
        """The number of existing chapters"""
        return self._chapters

    @property
    def oneshot(self):
        """Returns True if this work has only one chapter"""
        self._raise_if_unloaded()
        return self.nchapters == 1

    def _load_series(self, soup: BeautifulSoup):
        """Loads the work series from soup"""

        series_tags = soup.find("dd", {"class": "series"})
        if series_tags is None:
            self._series = None

        work_series = []
        for span in series_tags.find_all("span", {"class": "position"}):
            seriesid = int(span.a.attrs["href"].split("/")[-1])
            seriesname = span.a.getText()
            series = Series(seriesid, self._session, False)
            setattr(series, "name", seriesname)
            work_series.append(series)
        self._series = work_series

    @property
    def series(self):
        """Returns the series this work belongs to"""
        self._raise_if_unloaded()
        return self._series

    def _load_authors(self, soup: BeautifulSoup):
        """Load list of authors from soup"""
        authors = soup.find_all("h3", {"class": "byline heading"})
        if len(authors) == 0:
            self._authors = []
            return
        formatted_authors = authors[0].text.replace("\n", "").split(", ")
        author_list = []
        if authors is not None:
            for author in formatted_authors:
                user = User(author, load=False)
                author_list.append(user)

        self._authors = author_list

    @property
    def authors(self):
        """Returns the list of the work's author

        Returns:
            list: list of authors
        """
        self._raise_if_unloaded()
        return self._authors

    def _load_nchapters(self, soup: BeautifulSoup):
        """Load the number of chapters from soup"""
        chapters = soup.find("dd", {"class": "chapters"})
        if chapters is not None:
            self._nchapters = int(self.drop_commas(chapters.string.split("/")[0]))
        self._nchapters = 0

    @property
    def nchapters(self):
        """Returns the number of chapters of this work

        Returns:
            int: number of chapters
        """
        self._raise_if_unloaded()
        return self._nchapters

    def _load_expected_chapters(self, soup: BeautifulSoup):
        "Load the number of expected chapters from soup"
        chapters = soup.find("DD", {"class": "chapters"})
        if chapters is not None:
            chapter_count = self.drop_commas(chapters.string.split("/")[-1])
            if chapter_count.isdigit():
                self._expected_chapters = int(chapter_count)
        self._expected_chapters = None

    @property
    def expected_chapters(self):
        """Returns the number of expected chapters for this work, or None if
        the author hasn't provided an expected number

        Returns:
            int: number of chapters
        """
        self._raise_if_unloaded()
        return self._expected_chapters

    @property
    def status(self):
        """Returns the status of this work

        Returns:
            str: work status
        """
        self._raise_if_unloaded()

        return (
            "Completed"
            if self.nchapters == self.expected_chapters
            else "Work in Progress"
        )

    def _load_hits(self, soup: BeautifulSoup):
        """Load number of hits from soup"""
        hits = soup.find("dd", {"class": "hits"})
        if hits is not None:
            self._hits = int(self.drop_commas(hits.string))
            return
        self._hits = 0

    @property
    def hits(self):
        """Returns the number of hits this work has

        Returns:
            int: number of hits
        """
        self._raise_if_unloaded()
        return self._hits

    def _load_kudos(self, soup: BeautifulSoup):
        kudos = soup.find("dd", {"class": "kudos"})
        if kudos is not None:
            self._kudos = int(self.drop_commas(kudos.string))
            return
        self._kudos = 0

    @property
    def kudos(self):
        """Returns the number of kudos this work has

        Returns:
            int: number of kudos
        """
        self._raise_if_unloaded()

        return self._kudos

    def _load_comments(self, soup: BeautifulSoup):
        comments = soup.find("dd", {"class": "comments"})
        if comments is not None:
            self._comments = int(self.drop_commas(comments.string))
            return
        self._comments = 0

    @property
    def comments(self):
        """Returns the number of comments this work has

        Returns:
            int: number of comments
        """
        self._raise_if_unloaded()

        return self._comments

    def _load_restricted(self, soup: BeautifulSoup):
        self._restricted = soup.find("img", {"title": "Restricted"}) is not None

    @property
    def restricted(self):
        """Whether this is a restricted work or not

        Returns:
            int: True if work is restricted
        """
        self._raise_if_unloaded()
        return self._restricted

    def _load_words(self, soup: BeautifulSoup):
        words = soup.find("dd", {"class": "words"})
        if words is not None:
            self._words = int(self.drop_commas(words.string))
            return
        self._words = 0

    @property
    def words(self):
        """Returns the number of words this work has

        Returns:
            int: number of words
        """
        self._raise_if_unloaded()

        return self._words

    def _load_language(self, soup: BeautifulSoup):
        language = soup.find("dd", {"class": "language"})
        if language is not None:
            self._language = language.string.strip()
            return
        self._language = "Unknown"

    @property
    def language(self):
        """Returns this work's language

        Returns:
            str: Language
        """
        self._raise_if_unloaded()
        return self._language

    def _load_bookmarks(self, soup: BeautifulSoup):
        bookmarks = soup.find("dd", {"class": "bookmarks"})
        if bookmarks is not None:
            self._bookmarks = int(self.drop_commas(bookmarks.string))
            return
        self._bookmarks = 0

    @property
    def bookmarks(self):
        """Returns the number of bookmarks this work has

        Returns:
            int: number of bookmarks
        """
        self._raise_if_unloaded()

        return self._bookmarks

    def _load_title(self, soup):
        title = soup.find("div", {"class": "preface group"})
        if title is not None:
            self._title = str(title.h2.text.strip())
            return
        self._title = ""

    @property
    def title(self):
        """Returns the title of this work

        Returns:
            str: work title
        """
        self._raise_if_unloaded()
        return self._title

    def _load_date_published(self, soup: BeautifulSoup):
        """Loads the date published from soup"""
        date_published = soup.find("dd", {"class": "published"}).string
        self._date_published = datetime(*list(map(int, date_published.split("-"))))

    @property
    def date_published(self):
        """Returns the date this work was published

        Returns:
            datetime.date: publish date
        """
        self._raise_if_unloaded()
        return self._date_published

    def _load_date_edited(self, soup: BeautifulSoup):
        """Load date edited from soup"""
        download = soup.find("li", {"class": "download"})
        if download is not None and download.ul is not None:
            timestamp = int(download.ul.a["href"].split("=")[-1])
            self._date_edited = datetime.fromtimestamp(timestamp)
            return
        self._date_edited = datetime(self.date_published)

    @property
    def date_edited(self):
        """Returns the date this work was last edited

        Returns:
            datetime.datetime: edit date
        """
        self._raise_if_unloaded()
        return self._date_edited

    def _load_date_updated(self, soup: BeautifulSoup):
        update = soup.find("dd", {"class": "status"})
        if update is not None:
            split = update.string.split("-")
            self._date_updated = datetime(*list(map(int, split)))
            return
        self._load_date_published(soup)
        self._date_updated = self.date_published

    @property
    def date_updated(self):
        """Returns the date this work was last updated

        Returns:
            datetime.datetime: update date
        """
        self._raise_if_unloaded()
        return self._date_updated

    def _load_tags(self, soup: BeautifulSoup):
        """Load the tags from soup"""
        html = soup.find("dd", {"class": "freeform tags"})
        tags = []
        if html is not None:
            for tag in html.find_all("li"):
                tags.append(tag.a.string)
        self._tags = tags

    @property
    def tags(self):
        """Returns all the work's tags

        Returns:
            list: List of tags
        """
        self._raise_if_unloaded()
        return self._tags

    def _load_characters(self, soup: BeautifulSoup):
        """Load the characters from soup"""
        html = soup.find("dd", {"class": "character tags"})
        characters = []
        if html is not None:
            for tag in html.find_all("li"):
                characters.append(tag.a.string)
        self._characters = characters

    @property
    def characters(self):
        """Returns all the work's characters

        Returns:
            list: List of characters
        """
        self._raise_if_unloaded()
        return self._characters

    def _load_relationships(self, soup: BeautifulSoup):
        """Load the relationships from soup"""
        html = soup.find("dd", {"class": "relationship tags"})
        relationships = []
        if html is not None:
            for tag in html.find_all("li"):
                relationships.append(tag.a.string)
        self._relationships = relationships

    @property
    def relationships(self):
        """Returns all the work's relationships

        Returns:
            list: List of relationships
        """
        self._raise_if_unloaded()
        return self._relationships

    def _load_fandoms(self, soup: BeautifulSoup):
        """Load the fandoms from soup"""
        html = soup.find("dd", {"class": "fandom tags"})
        fandoms = []
        if html is not None:
            for tag in html.find_all("li"):
                fandoms.append(tag.a.string)
        self._fandoms = fandoms

    @property
    def fandoms(self):
        """Returns all the work's fandoms

        Returns:
            list: List of fandoms
        """
        self._raise_if_unloaded()
        return self._fandoms

    def _load_categories(self, soup: BeautifulSoup):
        """Load the categories from soup"""
        html = soup.find("dd", {"class": "category tags"})
        categories = []
        if html is not None:
            for tag in html.find_all("li"):
                categories.append(tag.a.string)
        self._categories = categories

    @property
    def categories(self):
        """Returns all the work's categories

        Returns:
            list: List of categories
        """
        self._raise_if_unloaded()
        return self._categories

    def _load_warnings(self, soup: BeautifulSoup):
        """Load the warnings from soup"""
        html = soup.find("dd", {"class": "warning tags"})
        warnings = []
        if html is not None:
            for tag in html.find_all("li"):
                warnings.append(tag.a.string)
        self._warnings = warnings

    @property
    def warnings(self):
        """Returns all the work's warnings

        Returns:
            list: List of warnings
        """
        self._raise_if_unloaded()
        return self._warnings

    def _load_ratings(self, soup: BeautifulSoup):
        """Load the ratings from soup"""
        html = soup.find("dd", {"class": "rating tags"})
        ratings = []
        if html is not None:
            for tag in html.find_all("li"):
                ratings.append(tag.a.string)
        self._ratings = ratings

    @property
    def ratings(self):
        """Returns all the work's ratings

        Returns:
            list: List of ratings
        """
        self._raise_if_unloaded()
        return self._ratings

    def _load_summary(self, soup: BeautifulSoup):
        """Load summary from soup"""
        div = soup.find("div", {"class": "preface group"})
        if div is None:
            self._summary = ""
            return
        html = div.find("blockquote", {"class": "userstuff"})
        if html is None:
            self._summary = ""
            return
        self._summary = str(BeautifulSoup.getText(html))

    @property
    def summary(self):
        """Returns this work's summary

        Returns:
            str: Summary
        """
        self._raise_if_unloaded()

        return self._summary

    def _load_start_notes(self, soup: BeautifulSoup):
        """Load start notes from soup"""
        notes = soup.find("div", {"class": "notes module"})
        if notes is None:
            self._start_notes = ""
            return
        text = ""
        for paragraph in notes.findAll("p"):
            text += paragraph.getText().strip() + "\n"
        self._start_notes = text

    @property
    def start_notes(self):
        """Text from this work's start notes"""
        self._raise_if_unloaded()
        return self._start_notes

    def _load_end_notes(self, soup: BeautifulSoup):
        """Load end notes from soup"""
        notes = soup.find("div", {"id": "work_endnotes"})
        if notes is None:
            self._end_notes = ""
            return
        text = ""
        for paragraph in notes.findAll("p"):
            text += paragraph.getText().strip() + "\n"
        self._end_notes = text

    @property
    def end_notes(self):
        """Text from this work's end notes"""
        # TODO: call reload() or throw an error?
        self._raise_if_unloaded()
        return self._end_notes

    @property
    def url(self):
        """Returns the URL to this work

        Returns:
            str: work URL
        """
        return f"https://archiveofourown.org/works/{self.id}"

    def _load_complete(self, soup: BeautifulSoup):
        chapter_status = soup.find("dd", {"class": "chapters"}).string.split("/")
        self._complete = chapter_status[0] == chapter_status[1]

    @property
    def complete(self):
        """
        Return True if the work is complete

        Retuns:
            bool: True if a work is complete
        """
        self._raise_if_unloaded()
        return self._complete

    def _raise_if_unloaded(self):
        if not self._loaded:
            raise utils.UnloadedError(
                "Work isn't loaded. Have you tried calling Work.reload()?"
            )

    @property
    def _is_authenticated(self):
        return self._session is not None and self._session.is_authed

    def get(self, *args, **kwargs):
        """Request a web page and return a Response object"""

        if self._session is None:
            req = requester.request("get", *args, **kwargs)
        else:
            req = requester.request(
                "get", *args, **kwargs, session=self._session.session
            )
        if req.status_code == 429:
            raise utils.HTTPError(
                "We are being rate-limited. Try again in a while or reduce the number of requests"
            )
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
            warnings.warn(
                "This work is very big and might take a very long time to load"
            )
        soup = BeautifulSoup(req.content, "lxml")
        return soup

    @staticmethod
    def drop_commas(string):
        """Removed commas from a given string

        Args:
            string (str): String to format

        Returns:
            str: Formatted string
        """

        return string.replace(",", "")
