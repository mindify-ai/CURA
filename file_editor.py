import pylint
import pylint.lint
from pylint.reporters.text import TextReporter
import tempfile
import io
import re
class FileEditor:
    def __init__(self, file_path: str, write_file_fn: callable, file_content: str = "", display_lines: int = 30, scroll_line: int = 30):
        self.file_path = file_path
        self._display_lines = display_lines
        self._current_line = 0
        self._scroll_line = scroll_line
        self._write_file = write_file_fn
        self._content_lines = file_content.split("\n")
        
        self.history = [self._content_lines.copy()]
        
    def goto_line(self, line_number: int):
        line_index = line_number - 1
        if line_index < 0:
            self._current_line = 0
        elif line_index >= len(self._content_lines):
            self._current_line = len(self._content_lines) - self._display_lines
        else:
            self._current_line = line_index
        
    def scroll_down(self):
        self.goto_line(self._current_line + self._scroll_line)
        
    def scroll_up(self):
        self.goto_line(self._current_line - self._scroll_line)
        
    def display(self)->str:
        output = "-"*49 + "\n"
        output += f"File Editor: {self.file_path}\n\n"
        
        start = self._current_line
        end = min(len(self._content_lines), start + self._display_lines)
        
        if start > 0:
            output += f"{start} more lines above.\n"
        else:
            output += "Beginning of file. Scroll up unavailable.\n"
        
        for i in range(start, end):
            output += f"{i+1}: {self._content_lines[i]}\n"
        
        if end < len(self._content_lines):
            output += f"{len(self._content_lines) - end} more lines below.\n"
        else:
            output += "End of file. Scroll down unavailable.\n"
        
        output += "-"*49
        return output
    
    def edit(self, begin_line: int, end_line: int, new_content: str)->bool:
        begin_index = begin_line - 1
        end_index = end_line - 1
        if begin_index < 0 or end_index < 0 or begin_index > end_index:
            return False
        while begin_index > len(self._content_lines) or end_index > len(self._content_lines):
            self._content_lines.append("")
        self._content_lines[begin_index:end_index+1] = new_content.split("\n")
        self._write_file(self.get_raw_content())
        self.history.append(self._content_lines.copy())
        return True
    
    def undo(self):
        if len(self.history) > 1:
            self.history.pop()
            self._content_lines = self.history[-1]
            self._write_file("\n".join(self._content_lines))
            return True
        return False
    
    def get_raw_content(self)->str:
        return "\n".join(self._content_lines)

class FileEditor_with_linting(FileEditor): 
    def lint(self)->dict[int, list[str]]:
        lint_errors: dict[int, list[str]] = {}
        with tempfile.NamedTemporaryFile(mode='w', delete=True) as f:
            f.write("\n".join(self._content_lines))
            f.flush()
            
            pylint_output = io.StringIO()
            reporter = TextReporter(output=pylint_output)
            template = "Line {line}: ({symbol}) {msg}"
            pylint.lint.Run([f.name,f'--msg-template={template}'], reporter=reporter, exit=False)
            pylint_output.seek(0)
            for line in pylint_output.readlines():
                match = re.match(r"Line (\d+):", line)
                if match:
                    line_number = int(match.group(1))
                    lint_errors.setdefault(line_number, []).append(line)
            return lint_errors