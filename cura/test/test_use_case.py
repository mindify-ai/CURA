from cura.vm import SWEVM
from cura.agent_tools import create_tools
from cura.test.utils import TEST_DATA

def test_add_pytest():
    with SWEVM(data=TEST_DATA) as vm:
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