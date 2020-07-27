import threading


def threadable(func):
    """Allows the function to be ran as a thread using the 'threaded' argument"""
    
    def new(*args, threaded=False, **kwargs):
        if threaded:
            thread = threading.Thread(target=func, args=args, kwargs=kwargs)
            thread.start()
            return thread
        else:
            return func(*args, **kwargs)
        
    new.__doc__ = func.__doc__
    new.__name__ = func.__name__
    new._threadable = True
    return new
            