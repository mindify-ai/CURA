from cura.vm import RepoVM
from cura.agent_tools import create_tools

test_repo = "sqlfluff/sqlfluff"
test_commit_hash = "c7e791d5ff3bf681a1eb2d717a69c8e166029c42"
image_name = "swe_img:latest"

def test_add_pytest():
    with RepoVM(image_name=image_name, repo_name=test_repo, commit_hash=test_commit_hash) as vm:
        tools = create_tools(vm)
        create_file_tool = tools['create_file']
        directory_tree_tool = tools['directory_tree']
        file_path = "/test/test_hello.py"
        
        result = vm.run_command("pytest --version")
        assert "pytest" in result
        
        
        create_file_tool.invoke(
            {
                "file_path": file_path,
                "content": "def test_hello():\n    assert True\n"
            }
        )
        assert vm.interface.file_exists(file_path)
        
        assert "test_hello.py" in directory_tree_tool.invoke({"dir_path": "/test", "max_depth": 1})
        
        result = vm.run_command("pytest /test/test_hello.py -v")
        assert "1 passed" in result
        assert "test_hello" in result
        assert "test_hello.py" in result
        assert "test_hello.py::test_hello" in result
        assert "test_hello.py::test_hello PASSED" in result
        assert "test_hello.py::test_hello FAILED" not in result