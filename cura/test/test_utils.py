from cura.utils import timeout
import time
from concurrent.futures import TimeoutError

def test_timeout():
    @timeout(1)
    def test():
        time.sleep(2)
    try:
        test()
    except TimeoutError:
        pass
    else:
        assert False, "Should have raised a TimeoutError"
        
    @timeout(1)
    def test():
        time.sleep(0.5)
        return "Success"
    try:
        result = test()
        assert result == "Success"
    except TimeoutError:
        assert False, "Should not have raised a TimeoutError"
    else:
        pass