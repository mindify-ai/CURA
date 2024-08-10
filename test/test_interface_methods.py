from vm import VM_with_interface, RepoVM
image_name = "swe_img:latest"
test_repo = "sqlfluff/sqlfluff"
test_commit_hash = "c7e791d5ff3bf681a1eb2d717a69c8e166029c42"

def test_write_file():
    with VM_with_interface(image_name=image_name) as vm:
        file_path = "/test.txt"
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