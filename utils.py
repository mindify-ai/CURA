import asyncio
from functools import wraps

def timeout(seconds: float):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await asyncio.wait_for(func(*args, **kwargs), timeout=seconds)
        return wrapper
    return decorator