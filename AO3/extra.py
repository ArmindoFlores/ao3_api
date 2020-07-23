import functools
import os
import pickle

import requests
from bs4 import BeautifulSoup

from . import utils


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
        req = requests.get(url)
        soup = BeautifulSoup(req.content, "lxml")
        for fandom in soup.find("ol", {"class": "alphabet fandom index group"}).findAll("a", {"class": "tag"}):
            fandoms.append(fandom.getText())
        with open(f"{os.path.join(fandom_path, name)}.pkl", "wb") as file:
            pickle.dump(fandoms, file)
    except AttributeError:
        raise utils.UnexpectedResponseError("Couldn't download the desired resource. Do you have the latest version of ao3-api?")
    print(f"Download complete ({len(fandoms)} fandoms)")
 
    
_RESOURCES = {
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


def download(resource):
    """Downloads the specified resource

    Args:
        resource (str): Resource name

    Raises:
        KeyError: Invalid resource
    """
    
    if resource not in _RESOURCES:
        raise KeyError(f"'{resource}' is not a valid resource")
    _RESOURCES[resource]()
