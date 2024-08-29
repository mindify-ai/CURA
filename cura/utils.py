import asyncio
from functools import wraps
import time

def timeout(seconds: float):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await asyncio.wait_for(func(*args, **kwargs), timeout=seconds)
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