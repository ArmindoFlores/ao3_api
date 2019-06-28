from datetime import date
import requests
from bs4 import BeautifulSoup
from . import utils


class Work:
    def __init__(self, workid):
        self.chapter_ids = []
        self.chapter_names = []
        self.workid = workid
        self.soup = self.request("https://archiveofourown.org/works/%i?view_adult=true"%workid)
        if "Error 404" in self.soup.text:
            raise requests.HTTPError("Error 404: cannot find work")
        

    def get_chapter_text(self, chapter):
        """Gets the chapter text from the specified chapter.
        Work.load_chapters() must be called first."""
        
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
    
    def load_chapters(self):
        """Loads the urls for all chapters"""
        
        if self.chapters > 1:
            navigate = self.request("https://archiveofourown.org/works/%i/navigate?view_adult=true"%self.workid)
            all_chapters = navigate.find("ol", {'class': 'chapter index group'})
            self.chapter_ids = []
            self.chapter_names = []
            for chapter in all_chapters.find_all("li"):
                self.chapter_ids.append(chapter.a['href'].split("/")[-1])
                self.chapter_names.append(chapter.a.string)
        else:
            self.chapter_ids = [""]
            self.chapter_names = [self.title]

    @property
    def authors(self):
        authors = self.soup.find_all("a", {'rel': 'author'})
        author_list = []
        for author in authors:
            author_list.append(author.string.strip())
            
        return author_list

    @property
    def chapters(self):
        chapters = self.soup.find("dd", {'class': 'chapters'}).string.split("/")[0]
        return int(self.str_format(chapters))

    @property
    def hits(self):
        hits = self.soup.find("dd", {'class': 'hits'}).string
        return int(self.str_format(hits))

    @property
    def kudos(self):
        kudos = self.soup.find("dd", {'class': 'kudos'}).string
        return int(self.str_format(kudos))

    @property
    def comments(self):
        comments = self.soup.find("dd", {'class': 'comments'}).string
        return int(self.str_format(comments))

    @property
    def words(self):
        words = self.soup.find("dd", {'class': 'words'}).string
        return int(self.str_format(words))

    @property
    def language(self):
        language = self.soup.find("dd", {'class': 'language'}).string.strip()
        return language

    @property
    def bookmarks(self):
        bookmarks = self.soup.find("dd", {'class': 'bookmarks'}).string
        return int(self.str_format(bookmarks))

    @property
    def title(self):
        title = self.soup.find("div", {'class': 'preface group'}).h2.string
        return str(title.strip())
    
    @property
    def date_published(self):
        dp = self.soup.find("dd", {'class': 'published'}).string
        return date(*list(map(int, dp.split("-"))))

    @property
    def date_updated(self):
        if self.chapters > 1:
            du = self.soup.find("dd", {'class': 'status'}).string
            return date(*list(map(int, du.split("-"))))
        else:
            return self.date_published
    
    @property
    def tags(self):
        html = self.soup.find("dd", {'class': 'freeform tags'})
        tags = []
        for tag in html.find_all("li"):
            tags.append(tag.a.string)
        return tags

    @property
    def characters(self):
        html = self.soup.find("dd", {'class': 'character tags'})
        characters = []
        for character in html.find_all("li"):
            characters.append(character.a.string)
        return characters

    @property
    def relationships(self):
        html = self.soup.find("dd", {'class': 'relationship tags'})
        relationships = []
        for relationship in html.find_all("li"):
            relationships.append(relationship.a.string)
        return relationships

    @property
    def fandoms(self):
        html = self.soup.find("dd", {'class': 'fandom tags'})
        fandoms = []
        for fandom in html.find_all("li"):
            fandoms.append(fandom.a.string)
        return fandoms

    @property
    def categories(self):
        html = self.soup.find("dd", {'class': 'category tags'})
        categories = []
        for category in html.find_all("li"):
            categories.append(category.a.string)
        return categories

    @property
    def warnings(self):
        html = self.soup.find("dd", {'class': 'warning tags'})
        warnings = []
        for warning in html.find_all("li"):
            warnings.append(warning.a.string)
        return warnings

    @property
    def rating(self):
        html = self.soup.find("dd", {'class': 'rating tags'})
        rating = html.a.string
        return rating

    @property
    def summary(self):
        div = self.soup.find("div", {'class': 'preface group'})
        html = div.find("blockquote", {'class': 'userstuff'})
        return str(BeautifulSoup.getText(html))
    
    @property
    def url(self):        
        return "https://archiveofourown.org/works/%i"%self.workid      

    @staticmethod
    def request(url):
        req = requests.get(url)
        content = req.content
        soup = BeautifulSoup(content, "html.parser")
        return soup

    @staticmethod
    def str_format(string):
        return string.replace(",", "")
        
        
        
