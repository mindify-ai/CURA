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