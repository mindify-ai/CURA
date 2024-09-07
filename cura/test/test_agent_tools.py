from cura.vm import SWEVM
from cura.agent_tools import create_tools
from cura.test.utils import TEST_DATA


def test_bash_command():
    with SWEVM(data=TEST_DATA, create_code_base=False) as vm:
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
    with SWEVM(data=TEST_DATA, create_code_base=False) as vm:
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