from cura.vm import VirtualMachine
import tempfile

def test_vm_init():
    with VirtualMachine("ubuntu:latest") as vm:
        assert vm._image_name == "ubuntu:latest"
        assert vm._client is not None
        
def test_vm_run_command():
    with VirtualMachine("ubuntu:latest") as vm:
        assert vm.run_command("ls") is not None
        assert vm.run_command("pwd") == "/\n"
        
def test_vm_run_command_async():
    with VirtualMachine("ubuntu:latest") as vm:
        vm.run_command_async("sleep 5")
        
def test_vm_copy_file_to_vm():
    with VirtualMachine("ubuntu:latest") as vm:
        with tempfile.NamedTemporaryFile() as f:
            f.write(b"Hello, World!")
            f.flush()
            vm.copy_file_to_vm(f.name, "/test.txt")
            assert vm.run_command("cat /test.txt") == "Hello, World!"

def test_vm_copy_file_from_vm():
    with VirtualMachine("ubuntu:latest") as vm:
        with tempfile.NamedTemporaryFile() as f:
            f.write(b"Hello, World!")
            f.flush()
            vm.copy_file_to_vm(f.name, "/test.txt")
            vm.copy_file_from_vm("/test.txt", f.name + "_copy")
            assert open(f.name + "_copy").read() == "Hello, World!"