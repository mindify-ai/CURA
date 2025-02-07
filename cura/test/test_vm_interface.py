from cura.vm import VM_with_interface
import threading
import time
from cura.test.utils import IMAGE_NAME


def test_vm_init():
    with VM_with_interface(image_name=IMAGE_NAME) as vm:
        assert vm._image_name == IMAGE_NAME
        assert vm.interface is not None
        assert vm.run_command(f"cat {vm.container_interface_path}") == open(vm.host_interface_path).read()
        
def test_vm_parrallel_init():
    def init_vm():
        with VM_with_interface(image_name=IMAGE_NAME) as vm:
            assert vm._image_name == IMAGE_NAME
            assert vm.interface is not None
            assert vm.run_command(f"cat {vm.container_interface_path}") == open(vm.host_interface_path).read()
            time.sleep(3)
    threads = []
    for _ in range(10):
        threads.append(threading.Thread(target=init_vm))
    
    for thread in threads:
        thread.start()
    
    for thread in threads:
        thread.join()
    
    