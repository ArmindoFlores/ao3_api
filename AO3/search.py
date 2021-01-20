from math import ceil

from bs4 import BeautifulSoup

from . import threadable, utils
from .requester import requester
from .series import Series
from .users import User
from .works import Work


DEFAULT = "_score"
BEST_MATCH = "_score"
AUTHOR = "authors_to_sort_on"
TITLE = "title_to_sort_on"
DATE_POSTED = "created_at"
DATE_UPDATED = "revised_at"
WORD_COUNT = "word_count"
RATING = "rating_ids"
HITS = "hits"
BOOKMARKS = "bookmarks_count"
COMMENTS = "comments_count"
KUDOS = "kudos_count"

DESCENDING = "desc"
ASCENDING = "asc"


class Search:
    def __init__(
        self,
        any_field="",
        title="",
        author="",
        single_chapter=False,
        word_count=None,
        language="",
        fandoms="",
        rating=None,
        hits=None,
        bookmarks=None,
        comments=None,
        completion_status=None,
        page=1,
        sort_column="",
        sort_direction=""):

        self.any_field = any_field
        self.title = title
        self.author = author
        self.single_chapter = single_chapter
        self.word_count = word_count
        self.language = language
        self.fandoms = fandoms
        self.rating = rating
        self.hits = hits
        self.bookmarks = bookmarks
        self.comments = comments
        self.completion_status = completion_status
        self.page = page
        self.sort_column = sort_column
        self.sort_direction = sort_direction

        self.results = None
        self.pages = 0
        self.total_results = 0

    @threadable.threadable
    def update(self):
        """Sends a request to the AO3 website with the defined search parameters, and updates all info.
        This function is threadable.
        """

        soup = search(
            self.any_field, self.title, self.author, self.single_chapter,
            self.word_count, self.language, self.fandoms, self.rating, self.hits,
            self.bookmarks, self.comments, self.completion_status, self.page,
            self.sort_column, self.sort_direction)

        results = soup.find("ol", {'class': 'work index group'})
        if results is None and soup.find("p", text="No results found. You may want to edit your search to make it less specific.") is not None:
            self.results = []
            self.total_results = 0
            self.pages = 0
            return

        works = []
        for work in results.find_all("li", {'class': 'work blurb group'}):
            if work.h4 is None:
                continue

            authors = []
            for a in work.h4.find_all("a"):
                if 'rel' in a.attrs.keys():
                    if "author" in a['rel']:
                        authors.append(User(a.string, load=False))
                elif a.attrs["href"].startswith("/works"):
                    workname = a.string
                    workid = utils.workid_from_url(a['href'])

            fandoms = []
            for a in work.find("h5", class_="fandoms").find_all("a"):
                fandoms.append(a.string)

            warnings = []
            relationships = []
            characters = []
            freeforms = []
            for a in work.find(class_="tags").find_all("li"):
                if "warnings" in a['class']:
                    warnings.append(a.text)
                elif "relationships" in a['class']:
                    relationships.append(a.text)
                elif "characters" in a['class']:
                    characters.append(a.text)
                elif "freeforms" in a['class']:
                    freeforms.append(a.text)

            reqtags = work.find(class_="required-tags")
            rating = reqtags.find(class_="rating").text
            categories = reqtags.find(class_="category").text.split(", ")

            summary_html = work.find(class_="userstuff summary")
            summary = summary_html.text if summary_html else ""

            series = []
            series_list = work.find(class_="series")
            if series_list is not None:
                for a in series_list.find_all("a"):
                    seriesid = int(a.attrs['href'].split("/")[-1])
                    seriesname = a.text
                    s = Series(seriesid, load=False)
                    setattr(s, "name", seriesname)
                    series.append(s)

            stats = work.find(class_="stats")
            language = stats.find("dd", class_="language").text
            words = int(stats.find("dd", class_="words").text.replace(",", ""))
            chapters = int(stats.find("dd", class_="chapters").text.split('/')[0].replace(",", ""))
            hits = int(stats.find("dd", class_="hits").text.replace(",", ""))

            new = Work(workid, load=False)
            setattr(new, "authors", authors)
            setattr(new, "fandoms", fandoms)
            setattr(new, "warnings", warnings)
            setattr(new, "relationships", relationships)
            setattr(new, "characters", characters)
            setattr(new, "tags", freeforms)
            setattr(new, "rating", rating)
            setattr(new, "categories", categories)
            setattr(new, "summary", summary)
            setattr(new, "series", series)
            setattr(new, "language", language)
            setattr(new, "words", words)
            setattr(new, "chapters", chapters)
            setattr(new, "hits", chapters)
            setattr(new, "title", workname)
            works.append(new)

        self.results = works
        maindiv = soup.find("div", {"class": "works-search region", "id": "main"})
        self.total_results = int(maindiv.find("h3", {"class": "heading"}).getText().strip().split(" ")[0])
        self.pages = ceil(self.total_results / 20)

def search(
    any_field="",
    title="",
    author="",
    single_chapter=False,
    word_count=None,
    language="",
    fandoms="",
    rating=None,
    hits=None,
    bookmarks=None,
    comments=None,
    completion_status=None,
    page=1,
    sort_column="",
    sort_direction=""):
    """Returns the results page for the search as a Soup object

    Args:
        any_field (str, optional): Generic search. Defaults to "".
        title (str, optional): Title of the work. Defaults to "".
        author (str, optional): Authors of the work. Defaults to "".
        single_chapter (bool, optional): Only include one-shots. Defaults to False.
        word_count (AO3.utils.Constraint, optional): Word count. Defaults to None.
        language (str, optional): Work language. Defaults to "".
        fandoms (str, optional): Fandoms included in the work. Defaults to "".
        rating (int, optional): Rating for the work. 9 for Not Rated, 10 for General Audiences, 11 for Teen And Up Audiences, 12 for Mature, 13 for Explicit. Defaults to None.
        hits (AO3.utils.Constraint, optional): Number of hits. Defaults to None.
        bookmarks (AO3.utils.Constraint, optional): Number of bookmarks. Defaults to None.
        comments (AO3.utils.Constraint, optional): Number of comments. Defaults to None.
        page (int, optional): Page number. Defaults to 1.
        sort_column (str, optional): Which column to sort on. Defaults to "".
        sort_direction (str, optional): Which direction to sort. Defaults to "".

    Returns:
        bs4.BeautifulSoup: Search result's soup
    """

    query = utils.Query()
    if page != 1:
        query.add_field(f"page={page}")
    if any_field != "":
        query.add_field(f"work_search[query]={any_field}")
    if title != "":
        query.add_field(f"work_search[title]={title}")
    if author != "":
        query.add_field(f"work_search[creators]={author}")
    if single_chapter:
        query.add_field(f"work_search[single_chapter]=1")
    if word_count is not None:
        query.add_field(f"work_search[word_count]={word_count}")
    if language != "":
        query.add_field(f"work_search[language_id]={language}")
    if fandoms != "":
        query.add_field(f"work_search[fandom_names]={fandoms}")
    if rating is not None:
        query.add_field(f"work_search[rating_ids]={rating}")
    if hits is not None:
        query.add_field(f"work_search[hits_count]={hits}")
    if bookmarks is not None:
        query.add_field(f"work_search[bookmarks_count]={bookmarks}")
    if comments is not None:
        query.add_field(f"work_search[comments_count]={comments}")
    if completion_status is not None:
        query.add_field(f"work_search[complete]={'T' if completion_status else 'F'}")
    if sort_column != "":
        query.add_field(f"work_search[sort_column]={sort_column}")
    if sort_direction != "":
        query.add_field(f"work_search[sort_direction]={sort_direction}")

    url = f"https://archiveofourown.org/works/search?{query.string}"

    req = requester.request("get", url)
    if req.status_code == 429:
        raise utils.HTTPError("We are being rate-limited. Try again in a while or reduce the number of requests")
    soup = BeautifulSoup(req.content, features="lxml")
    return soup
