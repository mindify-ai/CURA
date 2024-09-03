from cura.vm import RepoVM
from cura.agent_tools import create_tools

test_repo = "sqlfluff/sqlfluff"
test_commit_hash = "c7e791d5ff3bf681a1eb2d717a69c8e166029c42"
image_name = "swe_img:latest"

def test_bash_command():
    with RepoVM(image_name=image_name, repo_name=test_repo, commit_hash=test_commit_hash) as vm:
        tools = create_tools(vm)
        bash_tool = tools['bash_command']
        
        result = bash_tool.invoke(
            {
                "command": "ls /"
            }
        )
        assert "bin" in result
        
        result = bash_tool.invoke(
            {
                "command": "echo $TEST",
                "environment_variables": {"TEST": "Hello, World!"}
            }
        )
        assert result == "Hello, World!\n"
        
        result = bash_tool.invoke(
            {
                "command": "pip --version"
            }
        )
        assert "pip" in result
        
        result = bash_tool.invoke(
            {
                "command": "git --version"
            }
        )
        assert "git" in result
        
        result = bash_tool.invoke(
            {
                "command": "pytest --version"
            }
        )
        assert "pytest" in result

def test_create_file():
    with RepoVM(image_name=image_name, repo_name=test_repo, commit_hash=test_commit_hash) as vm:
        tools = create_tools(vm)
        create_file_tool = tools['create_file']
        directory_tree_tool = tools['directory_tree']
        
        create_file_tool.invoke(
            {
                "file_path": "/test.txt",
                "content": "Hello, World!"
            }
        )
        
        result = vm.run_command("cat /test.txt")
        assert result == "Hello, World!"
        assert vm.interface.file_exists("/test.txt")
        assert vm.interface.get_file_content("/test.txt") == "Hello, World!"
        assert "test.txt" in directory_tree_tool.invoke({"dir_path": "/"})
        
        create_file_tool.invoke(
            {
                "file_path": "/test.txt",
                "content": "Goodbye, World!"
            }
        )
        
        result = vm.run_command("cat /test.txt")
        assert result == "Goodbye, World!"
        assert vm.interface.file_exists("/test.txt")
        assert vm.interface.get_file_content("/test.txt") == "Goodbye, World!"
        assert "test.txt" in directory_tree_tool.invoke({"dir_path": "/"})