import requests
from bs4 import BeautifulSoup

from . import utils

class Series:
    def __init__(self, seriesid):
        self.seriesid = seriesid
        self.soup = BeautifulSoup()