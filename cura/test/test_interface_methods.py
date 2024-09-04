from cura.vm import VM_with_interface, RepoVM
image_name = "swe_img:latest"
test_repo = "sqlfluff/sqlfluff"
test_commit_hash = "c7e791d5ff3bf681a1eb2d717a69c8e166029c42"

def test_write_file():
    with VM_with_interface(image_name=image_name) as vm:
        file_path = "/test.txt"
        content = "Hello, World!"
        vm.interface.write_file(file_path, content)
        assert vm.run_command(f"cat {file_path}") == content
        
        file_path = "/test/test/test.txt"
        content = "Hello, World!"
        vm.interface.write_file(file_path, content)
        assert vm.run_command(f"cat {file_path}") == content
        
def test_get_file_content():
    with VM_with_interface(image_name=image_name) as vm:
        file_path = "/test.txt"
        content = "Hello, World!"
        vm.interface.write_file(file_path, content)
        vm.interface.get_file_content(file_path)
        assert vm.interface.get_file_content(file_path) == content
        
def test_get_patch_file_modify():
    with RepoVM(image_name=image_name, repo_name=test_repo, commit_hash=test_commit_hash) as vm:
        patch = vm.interface.get_patch_file(vm.repo_path)
        assert patch == ""
        vm.interface.write_file(f"{vm.repo_path}/README.md", "Hello, World!")
        patch = vm.interface.get_patch_file(vm.repo_path)
        assert patch != ""
        
def test_find_file():
    with VM_with_interface(image_name=image_name) as vm:
        file_name = "/test.txt"
        content = "Hello, World!"
        vm.interface.write_file(f"{file_name}", content)
        assert file_name in vm.interface.find_file('test.txt', '/')

def test_search_dir():
    with VM_with_interface(image_name=image_name) as vm:
        file_name = "/tmp/test.txt"
        content = "Hello, World!"
        vm.interface.write_file(f"{file_name}", content)
        assert file_name in vm.interface.search_dir('Hello', '/tmp')
        assert file_name not in vm.interface.search_dir('Goodbye', '/tmp')
        assert vm.interface.search_dir('Hello', '/tmp')[file_name] == 1

def test_search_file():
    with VM_with_interface(image_name=image_name) as vm:
        file_name = "/tmp/test.txt"
        content = "Hello, World!"
        vm.interface.write_file(f"{file_name}", content)
        assert '1' in vm.interface.search_file('Hello', '/tmp/test.txt')

def test_directory_tree():
    with VM_with_interface(image_name=image_name) as vm:
        file_name = "/tmp/test.txt"
        content = "Hello, World!"
        vm.interface.write_file(f"{file_name}", content)
        assert 'test.txt' in vm.interface.directory_tree('/tmp', 3)

def test_file_exists():
    with VM_with_interface(image_name=image_name) as vm:
        file_name = "/tmp/test.txt"
        content = "Hello, World!"
        vm.interface.write_file(f"{file_name}", content)
        assert vm.interface.file_exists(file_name) is True
        assert vm.interface.file_exists("/tmp/missing.txt") is False
        assert vm.interface.file_exists("/missing.txt") is False