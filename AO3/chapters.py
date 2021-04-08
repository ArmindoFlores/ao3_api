from functools import cached_property

from . import threadable, utils


class Chapter:
    """
    AO3 chapter object
    """
    
    def __init__(self, chapterid, work, session=None, load=True):
        self._session = session
        self._work = work
        self.id = chapterid
        self._soup = None
        if load:
            self.reload()
            
    def __repr__(self):
        try:
            return f"<Chapter [{self.title} ({self.number})] from [{self.work}]>"
        except:
            return f"<Chapter [{self.id}] from [{self.work}]>"
    
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
                
    def set_session(self, session):
        """Sets the session used to make requests for this chapter

        Args:
            session (AO3.Session/AO3.GuestSession): session object
        """
        
        self._session = session 
                
    @threadable.threadable
    def reload(self):
        """
        Loads information about this chapter.
        This function is threadable.
        """
        
        for attr in self.__class__.__dict__:
            if isinstance(getattr(self.__class__, attr), cached_property):
                if attr in self.__dict__:
                    delattr(self, attr)
        
        self.work.reload()
        
    def get_images(self):
        """Gets all images from this work

        Raises:
            utils.UnloadedError: Raises this error if the chapter isn't loaded

        Returns:
            tuple: Pairs of image urls and the paragraph number
        """
        
        div = self._soup.find("div", {"role": "article"})
        images = []
        line = 0
        for p in div.findAll("p"):
            line += 1
            for img in p.findAll("img"):
                images.append((img.attrs["src"], line))
        return tuple(images)
        
    @property
    def loaded(self):
        """Returns True if this chapter has been loaded"""
        return self._soup is not None
        
    @property
    def authenticity_token(self):
        """Token used to take actions that involve this work"""
        return self.work.authenticity_token
        
    @property
    def work(self):
        """Work this chapter is a part of"""
        return self._work
    
    @cached_property
    def text(self):
        """This chapter's text"""
        text = ""
        div = self._soup.find("div", {"role": "article"})
        for p in div.findAll("p"):
            text += p.getText().replace("\n", "") + "\n"
        return text

    @cached_property
    def title(self):
        """This chapter's title"""
        preface_group = self._soup.find("div", {"class": ("chapter", "preface", "group")})
        if preface_group is None:
            return str(number)
        title = preface_group.find("h3", {"class": "title"})
        if title is None:
            return str(number)
        return tuple(title.strings)[-1].strip()[2:]
        
    @cached_property
    def number(self):
        """This chapter's number"""
        return int(self._soup["id"].split("-")[-1])
    
    @cached_property
    def words(self):
        """Number of words from this chapter"""
        return utils.word_count(self.text)
    
    @cached_property
    def summary(self):
        """Text from this chapter's summary"""
        notes = self._soup.find("div", {"id": "summary"})
        if notes is None:
            return ""
        text = ""
        for p in notes.findAll("p"):
            text += p.getText() + "\n"
        return text

    @cached_property
    def start_notes(self):
        """Text from this chapter's start notes"""
        notes = self._soup.find("div", {"id": "notes"})
        if notes is None:
            return ""
        text = ""
        for p in notes.findAll("p"):
            text += p.getText().strip() + "\n"
        return text

    @cached_property
    def end_notes(self):
        """Text from this chapter's end notes"""
        notes = self._soup.find("div", {"id": f"chapter_{self.number}_endnotes"})
        if notes is None:
            return ""
        text = ""
        for p in notes.findAll("p"):
            text += p.getText() + "\n"
        return text