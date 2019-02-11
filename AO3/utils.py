class LoginError(Exception):
    def __init__(self, message, errors=[]):
        super().__init__(message)
        self.errors = errors

class UnloadedError(Exception):
    def __init__(self, message, errors=[]):
        super().__init__(message)
        self.errors = errors
        

def workid_from_url(url):
    """Get the workid from an archiveofourown.org website url"""
    split_url = url.split("/")
    try:
        index = split_url.index("works")
    except ValueError:
        return
    if len(split_url) >= index+1:
        if split_url[index+1].isdigit():
            return int(split_url[index+1])
    return
