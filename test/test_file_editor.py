from file_editor import FileEditor, FileEditor_with_linting
import pytest

class dummy_file:
    def __init__(self):
        self.content = ""
    def write(self, content):
        self.content = content
    def read(self):
        return self.content

def test_file_editor_init():
    file = dummy_file()
    editor = FileEditor("test.txt", file.write)
    assert editor.file_path == "test.txt"
    assert editor._current_line == 0
    assert editor._content_lines == ['']
    assert editor.history == [['']]
    
def test_read_file():
    file = dummy_file()
    file.content = "Hello World"
    editor = FileEditor("test.txt", file.write, file.read())
    assert editor.get_raw_content() == "Hello World"
    
@pytest.mark.parametrize("begin_line, end_line, new_content", [
    (1, 1, "Hello World"),
    (1, 1, "Hello World\n"),
    (1, 1, "Hello\nWorld"),
    (1, 5, "Hello\nWorld"),
])
def test_edit_file(begin_line, end_line, new_content):
    file = dummy_file()
    editor = FileEditor("test.txt", file.write)
    editor.edit(begin_line, end_line, new_content)
    assert editor.get_raw_content() == new_content
    assert file.content == new_content

def test_undo():
    file = dummy_file()
    editor = FileEditor("test.txt", file.write)
    editor.edit(1, 1, "Hello World")
    editor.edit(2, 2, "Hello World")
    assert editor.get_raw_content() == "Hello World\nHello World"
    editor.undo()
    assert editor.get_raw_content() == "Hello World"
    assert file.content == "Hello World"
    
def test_linting():
    file = dummy_file()
    editor = FileEditor_with_linting("test.py", file.write)
    editor.edit(1, 1, "def test():\n    print('Hello World')\n")
    assert editor.lint() == {}
    editor.edit(1, 2, "def test():\n    print('Hello World'\n")
    assert 2 in editor.lint()
