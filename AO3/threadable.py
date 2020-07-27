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
            
class ThreadPool:
    def __init__(self, maximum=None):
        self.maximum = maximum
        self._tasks = []
        self._threads = []
    
    def add_task(self, task):
        self._tasks.append(task)
        
    @threadable
    def start(self):
        while len(self._threads) != 0 or len(self._tasks) != 0:
            self._threads[:] = filter(lambda thread: thread.is_alive(), self._threads)
            for _ in range(min(self.maximum-len(self._threads), len(self._tasks))):
                self._threads.append(self._tasks.pop(0)(threaded=True))
