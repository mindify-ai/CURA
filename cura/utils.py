from functools import wraps
import time
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor()

def timeout(seconds: float):
    """Decorator to add a timeout to a function. If the function does not return within the timeout, a concurrent.futures.TimeoutError is raised.

    Args:
        seconds (float): The timeout in seconds.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            future = executor.submit(func, *args, **kwargs)
            return future.result(timeout=seconds)
        return wrapper
    return decorator

class TimeRecorder:
    def __init__(self, title: str = "Task"):
        self.t = 0
        self.title = title
    
    def __enter__(self):
        self.t = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        process_time = time.perf_counter() - self.t
        print(f"{self.title} took {process_time:.2f} seconds.")