from datetime import date
from functools import cached_property

import requests
from bs4 import BeautifulSoup

from . import utils
from .comments import Comment


class Work:
    """
    AO3 work object
    """

    def __init__(self, workid, session=None):
        """Creates a new AO3 work object

        Args:
            workid (int): AO3 work ID
            session (AO3.Session, optional): Used to access restricted works

        Raises:
            utils.InvalidIdError: Raised if the work wasn't found
        """

        self._session = session
        self.chapter_ids = []
        self.chapter_names = []
        self.workid = workid
        self.soup = self.request("https://archiveofourown.org/works/%i?view_adult=true"%workid)
        if "Error 404" in self.soup.text:
            raise utils.InvalidIdError("Cannot find work")

    def get_chapter_text(self, chapter):
        """Gets the chapter text from the specified chapter.
        Work.load_chapters() must be called first.

        Args:
            chapter (int): Work chapter

        Raises:
            utils.UnloadedError: Raises this error if the chapters aren't loaded

        Returns:
            str: Chapter text
        """
        
        if chapter > 0 and chapter <= self.chapters and self.chapters > 1:
            if len(self.chapter_ids) == self.chapters:
                chapter_html = self.request("https://archiveofourown.org/works/%i/chapters/%s?view_adult=true"%(self.workid, self.chapter_ids[chapter-1]))
                div = chapter_html.find("div", {'role': 'article'})
                return str(BeautifulSoup.getText(div))
            else:
                raise utils.UnloadedError("Work.load_chapters() must be called first")

        elif chapter == 1:
            div = self.soup.find("div", {'role': 'article'})
            return str(BeautifulSoup.getText(div))
        else:
            raise utils.UnloadedError("Work.load_chapters() must be called first")
    
    def load_chapters(self, session=None):
        """
        Loads the urls for all chapters
        """
        
        if not self.oneshot:
            navigate = self.request("https://archiveofourown.org/works/%i/navigate?view_adult=true"%self.workid)
            all_chapters = navigate.find("ol", {'class': 'chapter index group'})
            if all_chapters is None:
                raise utils.AuthError("This work is only available to registered users of the Archive")
            self.chapter_ids = []
            self.chapter_names = []
            for chapter in all_chapters.findAll("li"):
                self.chapter_ids.append(chapter.a['href'].split("/")[-1])
                self.chapter_names.append(chapter.a.string)
        else:
            self.chapter_ids = [""]
            self.chapter_names = [self.title]
            
    def download(self, filetype="PDF"):
        """Downloads this work

        Args:
            filetype (str, optional): Desired filetype. Defaults to "PDF".

        Raises:
            utils.DownloadError: Raised if there was an error with the download
            utils.UnexpectedResponseError: Raised if the filetype is not available for download

        Returns:
            bytes: File content
        """
        
        download_btn = self.soup.find("li", {"class": "download"})
        for download_type in download_btn.findAll("li"):
            if download_type.a.getText() == filetype:
                url = f"https://archiveofourown.org/{download_type.a.attrs['href']}"
                req = requests.get(url)
                if req.status_code == 429:
                    raise utils.HTTPError("We are being rate-limited. Try again in a while or reduce the number of requests")
                if not req.ok:
                    raise utils.DownloadError("An error occurred while downloading the work")
                return req.content
        raise utils.UnexpectedResponseError(f"Filetype '{filetype}' is not available for download")
    
    def get_comments(self, chapter=None, maximum=None):
        """Returns a list of all threads of comments in the specified chapter. This operation can take a very long time.
        Because of that, it is recomended that you set a maximum number of comments. 
        Duration: ~ (0.13 * n_comments) seconds or 2.9 seconds per comment page

        Args:
            chapter (int/str, optional): Chapter number, only required if work is not a oneshot. Defaults to None.
            maximum (int, optional): Maximum number of comments to be returned. None -> No maximum

        Raises:
            ValueError: Invalid chapter number
            IndexError: Invalid chapter number
            utils.UnloadedError: Work.load_chapters() must be called first

        Returns:
            list: List of comments
        """
        
        if self.oneshot:
            chapter_id = self.workid
        else:
            if chapter is None:
                raise IndexError("chapter cannot be 'None'")
            if chapter <= 0 or chapter >= self.chapters:
                raise IndexError("Invalid chapter number")
            if len(self.chapter_ids) != self.chapters:
                raise utils.UnloadedError("Work.load_chapters() must be called first")
            
            chapter_id = self.chapter_ids[chapter-1]
            
        url = f"https://archiveofourown.org/comments/show_comments?page=%d&chapter_id={chapter_id}"
        soup = self.request(url%1)
        
        pages = 0
        div = soup.find("div", {"id": "comments_placeholder"})
        ol = div.find("ol", {"class": "pagination actions"})
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
                comments.append(Comment(id_, chapter_id))
        return comments
    
    def leave_kudos(self, session):
        """Leave a 'kudos' in this work

        Args:
            session (AO3.Session/AO3.GuestSession): session object

        Raises:
            utils.UnexpectedResponseError: Unexpected response received
            utils.InvalidIdError: Invalid workid (work doesn't exist)
            utils.AuthError: Invalid authenticity token

        Returns:
            bool: True if successful, False if you already left kudos there
        """
        
        return utils.kudos(self.workid, session)
    
    def comment(self, chapter, comment_text, session, email="", name=""):
        """Leaves a comment on this work

        Args:
            chapter (int): Chapter number
            comment_text (str): Comment text
            session (AO3.Session, optional): Session object. Defaults to None (posts anonimously).

        Raises:
            IndexError: Invalid chapter number
            utils.UnloadedError: Couldn't load chapter ids. Call Work.load_chapters() first

        Returns:
            requests.models.Response: Response object
        """
        
        if chapter < 1 or chapter > self.chapters:
            raise IndexError(f"Invalid chapter number")
        
        if len(self.chapter_ids) != self.chapters:
            raise utils.UnloadedError("Work.load_chapters() must be called first")
        
        if self.chapters == 1:
            chapterid = self.workid
        else:
            chapterid = self.chapter_ids[chapter-1]
            
        return utils.comment(chapterid, comment_text, self.oneshot, email=email, name=name)
    
    @property
    def oneshot(self):
        return self.chapters == 1

    @cached_property
    def authors(self):
        """Returns the list of the work's author

        Returns:
            list: list of authors
        """

        authors = self.soup.find_all("a", {'rel': 'author'})
        author_list = []
        if authors is not None:
            for author in authors:
                author_list.append(author.string.strip())
            
        return author_list

    @cached_property
    def chapters(self):
        """Returns the number of chapters of this work

        Returns:
            int: number of chapters
        """
        
        chapters = self.soup.find("dd", {'class': 'chapters'})
        if chapters is not None:
            return int(self.str_format(chapters.string.split("/")[0]))
        return 0

    @cached_property
    def hits(self):
        """Returns the number of hits this work has

        Returns:
            int: number of hits
        """

        hits = self.soup.find("dd", {'class': 'hits'})
        if hits is not None:
            return int(self.str_format(hits.string))
        return 0

    @cached_property
    def kudos(self):
        """Returns the number of kudos this work has

        Returns:
            int: number of kudos
        """

        kudos = self.soup.find("dd", {'class': 'kudos'})
        if kudos is not None:
            return int(self.str_format(kudos.string))
        return 0

    @cached_property
    def comments(self):
        """Returns the number of comments this work has

        Returns:
            int: number of comments
        """

        comments = self.soup.find("dd", {'class': 'comments'})
        if comments is not None:
            return int(self.str_format(comments.string))
        return 0

    @cached_property
    def words(self):
        """Returns the this work's word count

        Returns:
            int: number of words
        """

        words = self.soup.find("dd", {'class': 'words'})
        if words is not None:
            return int(self.str_format(words.string))
        return 0

    @cached_property
    def language(self):
        """Returns this work's language

        Returns:
            str: Language
        """

        language = self.soup.find("dd", {'class': 'language'})
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

        bookmarks = self.soup.find("dd", {'class': 'bookmarks'})
        if bookmarks is not None:
            return int(self.str_format(bookmarks.string))
        return 0

    @cached_property
    def title(self):
        """Returns the title of this work

        Returns:
            str: work title
        """

        title = self.soup.find("div", {'class': 'preface group'})
        if title is not None:
            return str(title.h2.string.strip())
        return ""
    
    @cached_property
    def date_published(self):
        """Returns the date this work was published

        Returns:
            datetime.date: publish date
        """

        dp = self.soup.find("dd", {'class': 'published'}).string
        return date(*list(map(int, dp.split("-"))))

    @cached_property
    def date_updated(self):
        """Returns the date this work was last updated

        Returns:
            datetime.date: update date
        """

        if self.chapters > 1:
            du = self.soup.find("dd", {'class': 'status'}).string
            return date(*list(map(int, du.split("-"))))
        else:
            return self.date_published
    
    @cached_property
    def tags(self):
        """Returns all the work's tags

        Returns:
            list: List of tags
        """

        html = self.soup.find("dd", {'class': 'freeform tags'})
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

        html = self.soup.find("dd", {'class': 'character tags'})
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
        
        html = self.soup.find("dd", {'class': 'relationship tags'})
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

        html = self.soup.find("dd", {'class': 'fandom tags'})
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

        html = self.soup.find("dd", {'class': 'category tags'})
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

        html = self.soup.find("dd", {'class': 'warning tags'})
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

        html = self.soup.find("dd", {'class': 'rating tags'})
        if html is not None:
            rating = html.a.string
            return rating
        return "Unknown"

    @cached_property
    def summary(self):
        """Returns this work's summary

        Returns:
            str: Summary
        """

        div = self.soup.find("div", {'class': 'preface group'})
        if div is None:
            return ""
        html = div.find("blockquote", {'class': 'userstuff'})
        if html is None:
            return ""
        return str(BeautifulSoup.getText(html))
    
    @cached_property
    def url(self):
        """Returns the URL to this work

        Returns:
            str: work URL
        """    

        return "https://archiveofourown.org/works/%i"%self.workid      

    def request(self, url):
        """Request a web page and return a BeautifulSoup object.

        Args:
            url (str): Url to request
            data (dict, optional): Optional data to send in the request. Defaults to {}.

        Returns:
            bs4.BeautifulSoup: BeautifulSoup object representing the requested page's html
        """

        if self._session is None:
            req = requests.get(url)
        else:
            req = self._session.session.get(url)
        if req.status_code == 429:
            raise utils.HTTPError("We are being rate-limited. Try again in a while or reduce the number of requests")
        content = req.content
        soup = BeautifulSoup(content, "html.parser")
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
