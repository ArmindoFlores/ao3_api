import functools
import os
import pathlib
import pickle

from bs4 import BeautifulSoup

from . import threadable, utils
from .requester import requester


def _download_languages():
    path = os.path.dirname(__file__)
    languages = []
    try:
        rsrc_path = os.path.join(path, "resources")
        if not os.path.isdir(rsrc_path):
            os.mkdir(rsrc_path)
        language_path = os.path.join(rsrc_path, "languages")
        if not os.path.isdir(language_path):
            os.mkdir(language_path)
        url = "https://archiveofourown.org/languages"
        print(f"Downloading from {url}")
        req = requester.request("get", url)
        soup = BeautifulSoup(req.content, "lxml")
        for dt in soup.find("dl", {"class": "language index group"}).findAll("dt"):
            if dt.a is not None: 
                alias = dt.a.attrs["href"].split("/")[-1]
            else:
                alias = None
            languages.append((dt.getText(), alias))
        with open(f"{os.path.join(language_path, 'languages')}.pkl", "wb") as file:
            pickle.dump(languages, file)
    except AttributeError:
        raise utils.UnexpectedResponseError("Couldn't download the desired resource. Do you have the latest version of ao3-api?")
    print(f"Download complete ({len(languages)} languages)")

def _download_fandom(fandom_key, name):
    path = os.path.dirname(__file__)
    fandoms = []
    try:
        rsrc_path = os.path.join(path, "resources")
        if not os.path.isdir(rsrc_path):
            os.mkdir(rsrc_path)
        fandom_path = os.path.join(rsrc_path, "fandoms")
        if not os.path.isdir(fandom_path):
            os.mkdir(fandom_path)
        url = f"https://archiveofourown.org/media/{fandom_key}/fandoms"
        print(f"Downloading from {url}")
        req = requester.request("get", url)
        soup = BeautifulSoup(req.content, "lxml")
        for fandom in soup.find("ol", {"class": "alphabet fandom index group"}).findAll("a", {"class": "tag"}):
            fandoms.append(fandom.getText())
        with open(f"{os.path.join(fandom_path, name)}.pkl", "wb") as file:
            pickle.dump(fandoms, file)
    except AttributeError:
        raise utils.UnexpectedResponseError("Couldn't download the desired resource. Do you have the latest version of ao3-api?")
    print(f"Download complete ({len(fandoms)} fandoms)")
 

_FANDOM_RESOURCES = {
    "anime_manga_fandoms": functools.partial(
        _download_fandom, 
        "Anime%20*a*%20Manga", 
        "anime_manga_fandoms"),
    "books_literature_fandoms": functools.partial(
        _download_fandom, 
        "Books%20*a*%20Literature", 
        "books_literature_fandoms"),
    "cartoons_comics_graphicnovels_fandoms": functools.partial(
        _download_fandom, 
        "Cartoons%20*a*%20Comics%20*a*%20Graphic%20Novels", 
        "cartoons_comics_graphicnovels_fandoms"),
    "celebrities_real_people_fandoms": functools.partial(
        _download_fandom, 
        "Celebrities%20*a*%20Real%20People", 
        "celebrities_real_people_fandoms"),
    "movies_fandoms": functools.partial(
        _download_fandom, 
        "Movies", 
        "movies_fandoms"),
    "music_bands_fandoms": functools.partial(
        _download_fandom, 
        "Music%20*a*%20Bands", 
        "music_bands_fandoms"),
    "other_media_fandoms": functools.partial(
        _download_fandom, 
        "Other%20Media", 
        "other_media_fandoms"),
    "theater_fandoms": functools.partial(
        _download_fandom, 
        "Theater", 
        "theater_fandoms"),
    "tvshows_fandoms": functools.partial(
        _download_fandom, 
        "TV%20Shows", 
        "tvshows_fandoms"),
    "videogames_fandoms": functools.partial(
        _download_fandom, 
        "Video%20Games", 
        "videogames_fandoms"),
    "uncategorized_fandoms": functools.partial(
        _download_fandom, 
        "Uncategorized%20Fandoms", 
        "uncategorized_fandoms")
}

_LANGUAGE_RESOURCES = {
    "languages": _download_languages
}

_RESOURCE_DICTS = [("fandoms", _FANDOM_RESOURCES),
                   ("languages", _LANGUAGE_RESOURCES)]

@threadable.threadable
def download(resource):
    """Downloads the specified resource.
    This function is threadable.

    Args:
        resource (str): Resource name

    Raises:
        KeyError: Invalid resource
    """
    
    for _, resource_dict in _RESOURCE_DICTS:
        if resource in resource_dict:
            resource_dict[resource]()
            return
    raise KeyError(f"'{resource}' is not a valid resource")

def get_resources():
    """Returns a list of every resource available for download"""
    
    d = {}
    for name, resource_dict in _RESOURCE_DICTS:
        d[name] = list(resource_dict.keys())
    return d

def has_resource(resource):
    """Returns True if resource was already download, False otherwise"""
    path = os.path.join(os.path.dirname(__file__), "resources")
    return len(list(pathlib.Path(path).rglob(resource+".pkl"))) > 0

@threadable.threadable
def download_all(redownload=False):
    """Downloads every available resource.
    This function is threadable."""
    
    types = get_resources()
    for rsrc_type in types:
        for rsrc in types[rsrc_type]:
            if redownload or not has_resource(rsrc):
                download(rsrc)

@threadable.threadable    
def download_all_threaded(redownload=False):
    """Downloads every available resource in parallel (about ~3.7x faster).
    This function is threadable."""
    
    threads = []
    types = get_resources()
    for rsrc_type in types:
        for rsrc in types[rsrc_type]:
            if redownload or not has_resource(rsrc):
                threads.append(download(rsrc, threaded=True))
    for thread in threads:
        thread.join()
