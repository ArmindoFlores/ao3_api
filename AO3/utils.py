class LoginError(Exception):
    def __init__(self, message, errors=[]):
        super().__init__(message)
        self.errors = errors

class UnloadedError(Exception):
    def __init__(self, message, errors=[]):
        super().__init__(message)
        self.errors = errors


class Query:
    def __init__(self):
        self.fields = []
    
    def add_field(self, text):
        self.fields.append(text)

    @property
    def string(self):
        return '&'.join(self.fields)


class Constraint:
    """Represents a bounding box of a value
    """

    def __init__(self, lowerbound=0, upperbound=None):
        """Creates a new Constraint object

        Args:
            lowerbound (int, optional): Constraint lowerbound. Defaults to 0.
            upperbound (int, optional): Constraint upperbound. Defaults to None.
        """
        
        self._lb = lowerbound
        self._ub = upperbound

    @property
    def string(self):
        """Returns the string representation of this constraint

        Returns:
            str: string representation
        """

        if self._lb == 0:
            return f"<{self._ub}"
        elif self._ub is None:
            return f">{self._lb}"
        elif self._ub == self._lb:
            return str(self._lb)
        else:
            return f"{self._lb}-{self._ub}"

    def __str__(self):
        return self.string
        

def workid_from_url(url):
    """Get the workid from an archiveofourown.org website url

    Args:
        url (str): Work URL 

    Returns:
        int: Work ID
    """
    split_url = url.split("/")
    try:
        index = split_url.index("works")
    except ValueError:
        return
    if len(split_url) >= index+1:
        if split_url[index+1].isdigit():
            return int(split_url[index+1])
    return
    