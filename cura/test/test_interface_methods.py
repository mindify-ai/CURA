from cura.vm import VM_with_interface, SWEVM
from cura.test.utils import IMAGE_NAME, TEST_DATA
import pytest


def test_raise_exception():
    with VM_with_interface(image_name=IMAGE_NAME) as vm:
        with pytest.raises(Exception):
            vm.interface.get_file_content("/missing.txt")
        vm.interface.write_file("/test.txt", "Hello, World!")
        assert vm.run_command("cat /test.txt") == "Hello, World!"
        
def test_write_file():
    with VM_with_interface(image_name=IMAGE_NAME) as vm:
        file_path = "/test.txt"
        content = "Hello, World!"
        vm.interface.write_file(file_path, content)
        assert vm.run_command(f"cat {file_path}") == content
        
        file_path = "/test/test/test.txt"
        content = "Hello, World!"
        vm.interface.write_file(file_path, content)
        assert vm.run_command(f"cat {file_path}") == content
        
def test_get_file_content():
    with VM_with_interface(image_name=IMAGE_NAME) as vm:
        file_path = "/test.txt"
        content = "Hello, World!"
        vm.interface.write_file(file_path, content)
        vm.interface.get_file_content(file_path)
        assert vm.interface.get_file_content(file_path) == content
        
def test_get_patch_file_modify():
    with VM_with_interface(image_name=IMAGE_NAME) as vm:
        vm.bash_command("git config --global user.email 'test@example.com'")
        vm.bash_command("git config --global user.name 'Test User'")
        vm.bash_command("mkdir /test")
        vm.bash_command("cd /test && git init")
        patch = vm.interface.get_patch_file("/test")
        assert patch == ""
        vm.interface.write_file("/test/.gitignore", "Hello, World!")
        vm.bash_command("cd /test && git add .gitignore && git commit -m 'Add .gitignore'")
        patch = vm.interface.get_patch_file("/test")
        assert patch == ""
        vm.interface.write_file("/test/.gitignore", "Hello, World! Modified")
        patch = vm.interface.get_patch_file("/test")
        assert patch != ""
        
def test_find_file():
    with VM_with_interface(image_name=IMAGE_NAME) as vm:
        file_name = "/test.txt"
        content = "Hello, World!"
        vm.interface.write_file(f"{file_name}", content)
        assert file_name in vm.interface.find_file('test.txt', '/')

def test_search_dir():
    with VM_with_interface(image_name=IMAGE_NAME) as vm:
        file_name = "/tmp/test.txt"
        content = "Hello, World!"
        vm.interface.write_file(f"{file_name}", content)
        assert file_name in vm.interface.search_dir('Hello', '/tmp')
        assert file_name not in vm.interface.search_dir('Goodbye', '/tmp')
        assert vm.interface.search_dir('Hello', '/tmp')[file_name] == 1

def test_search_file():
    with VM_with_interface(image_name=IMAGE_NAME) as vm:
        file_name = "/tmp/test.txt"
        content = "Hello, World!"
        vm.interface.write_file(f"{file_name}", content)
        assert '1' in vm.interface.search_file('Hello', '/tmp/test.txt')

def test_directory_tree():
    with VM_with_interface(image_name=IMAGE_NAME) as vm:
        file_name = "/tmp/test.txt"
        content = "Hello, World!"
        vm.interface.write_file(f"{file_name}", content)
        assert 'test.txt' in vm.interface.directory_tree('/tmp', 3)

def test_file_exists():
    with VM_with_interface(image_name=IMAGE_NAME) as vm:
        file_name = "/tmp/test.txt"
        content = "Hello, World!"
        vm.interface.write_file(f"{file_name}", content)
        assert vm.interface.file_exists(file_name) is True
        assert vm.interface.file_exists("/tmp/missing.txt") is False
        assert vm.interface.file_exists("/missing.txt") is False