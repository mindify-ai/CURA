from utils import timeout
import asyncio

def test_timeout():
    @timeout(1)
    async def test():
        await asyncio.sleep(2)
    try:
        asyncio.run(test())
    except asyncio.TimeoutError:
        pass
    else:
        assert False, "Should have raised a TimeoutError"
        
    @timeout(1)
    async def test():
        await asyncio.sleep(0.5)
    try:
        asyncio.run(test())
    except asyncio.TimeoutError:
        assert False, "Should not have raised a TimeoutError"
    else:
        pass