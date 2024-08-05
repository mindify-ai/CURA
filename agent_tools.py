from langchain_core.tools import tool, BaseTool
from typing import Optional
from vm import VirtualMachine

display_line_count = 100

def view_file_content(file_name: str, content: str, begin_line: int, end_line: int) -> str:
    """
    View the content of a file from the specified beginning line to the ending line.

    Args:
        content (str): The content of the file.
        begin_line (int): The starting line number.
        end_line (int): The ending line number.

    Returns:
        str: A string containing the content of the specified lines in the desired format.
    """
    if begin_line > end_line:
        return "Begin line number should be less than or equal to the end line number."
    if begin_line < 1:
        return "Begin line number should be greater than or equal to 1."
    if end_line < 1:
        return "End line number should be greater than or equal to 1."
    
    
    lines = content.split('\n')
    
    total_lines = len(lines)
    if begin_line > total_lines:
        return "Begin line number should be less than or equal to the total number of lines in the file."
    
    output = "File Viewer - " + file_name + "\n"
    if not content:
        output += "The file is empty."
        return output
    
    if begin_line < 1:
        begin_line = 1
    if end_line > total_lines:
        end_line = total_lines
    
    if begin_line > 1:
        output += f"({begin_line - 1} more lines above)\n\n"
    else:
        output += "Beginning of file\n\n"
    
    for line_no in range(begin_line, end_line + 1):
        output += f"{line_no}:{lines[line_no - 1]}\n"
    
    if end_line < total_lines:
        output += f"\n({total_lines - end_line} more lines below)\n"
    else:
        output += "\n(End of file)"
    
    return output

def create_tools(vm: VirtualMachine):
    
    current_open_file: Optional[str] = None
    current_line_number: Optional[int] = None
    scroll_line_count = 80
    
    def vm_run_tool(tool_name: str, args: list[str] = [])->str:
        args = [f'\"{arg}\"' for arg in args]
        args_str = ' '.join(args)
        return vm.run_command(f"python /tool.py {tool_name} {args_str}")
    
    def get_file_content(file_path: str)->str:
        content = vm_run_tool('view_file', [file_path])
        if len(content) >= 1 and content[-1] == '\n':
            content = content[:-1]
        return content
    
    
    
    @tool
    def open_file(file_name: str, goto_line: int = 1)->str:
        """Opens the file at the given file_path.

        Args:
            file_path (str): The path of the file to open.
            goto_line (int, optional): The line number to go to after opening the file. Defaults to 1.

        Returns:
            str: The content of the file.
        """
        global current_open_file, current_line_number
        current_open_file = file_name
        current_line_number = goto_line
        content = get_file_content(current_open_file)
        return view_file_content(current_open_file, content, current_line_number, current_line_number + display_line_count)

    @tool
    def goto_line(line_number: int)->str:
        """Goes to the specified line number in the currently opened file.

        Args:
            line_number (int): The line number to go to.

        Returns:
            str: The content of the file after going to the specified line.
        """
        global current_open_file, current_line_number
        if current_open_file is None:
            return "No file is open. You must open a file before going to a line."
        current_line_number = line_number
        content = get_file_content(current_open_file)
        return view_file_content(current_open_file, content, current_line_number, current_line_number + display_line_count)

    @tool
    def scroll_down()->str:
        """Scrolls down the currently opened file by the specified number of lines.

        Returns:
            str: The content of the file after scrolling.
        """
        global current_open_file, current_line_number
        if current_open_file is None:
            return "No file is open. You must open a file before scrolling."
        current_line_number += scroll_line_count
        content = get_file_content(current_open_file)
        return view_file_content(current_open_file, content, current_line_number, current_line_number + display_line_count)

    @tool
    def scroll_up()->str:
        """Scrolls up the currently opened file by the specified number of lines.

        Returns:
            str: The content of the file after scrolling.
        """
        global current_open_file, current_line_number
        if current_open_file is None:
            return "No file is open. You must open a file before scrolling."
        current_line_number -= scroll_line_count
        if current_line_number < 1:
            current_line_number = 1
        content = get_file_content(current_open_file)
        return view_file_content(current_open_file, content, current_line_number, current_line_number + display_line_count)

    @tool
    def search_file(search_term: str, file_name: str)->str:
        """Searches for search_term in provided file_name.

        Args:
            search_term (str): The term to search for.
            file_name (str): The name of the file to search

        Returns:
            str: The result of the search.
        """
        return vm_run_tool('search_file', [search_term, file_name])

    @tool
    def search_dir(search_term: str, dir: str)->str:
        """Searches for search_term in provided dir.

        Args:
            search_term (str): The term to search for.
            dir (str): The directory to search in.

        Returns:
            str: The result of the search.
        """
        return vm_run_tool('search_dir', [search_term, dir])

    @tool
    def find_file(file_name: str, dir: str)->str:
        """Finds the file with the given name in the provided directory.

        Args:
            file_name (str): The name of the file to find.
            dir (str): The directory to search in.

        Returns:
            str: The result of the find.
        """
        return vm_run_tool('find_file', [file_name, dir])
    
    @tool
    def run_linux_command(command: str)->str:
        """Runs the provided linux command. You can use this tool to run any linux command like python or ls.
        You are always in the root directory. command cd is not supported.

        Args:
            command (str): The command to run.

        Returns:
            str: The output of the command.
        """
        return vm_run_tool(command)

    @tool
    def edit_file(begin_line: int, end_line: int, new_content: str)->str:
        """Edits the open file from the begin_line to the end_line with the new_content. You must open a file before editing it.

        Args:
            begin_line (int): The line number to start editing from.
            end_line (int): The line number to end editing.
            new_content (str): The new content to replace the lines with.

        Returns:
            str: The output of the tool.
        """
        
        global current_open_file, current_line_number
        if current_open_file is None:
            return "No file is open. You must edit a file after opening it."
        edit_result = vm_run_tool('edit_file', [current_open_file, str(begin_line), str(end_line), new_content])
        file_content = get_file_content(current_open_file)
        current_line_number = begin_line
        return edit_result + "\n" + view_file_content(current_open_file, file_content, current_line_number, current_line_number + display_line_count)

    @tool
    def create_file(file_name: str)->str:
        """This tool creates a new empty file with the given absolute path.

        Args:
            file_name (str): The absolute path of the file to be created.

        Returns:
            str: The output of the tool.
        """
        global current_open_file, current_line_number
        result = vm_run_tool('create_file', [file_name])
        current_open_file = file_name
        current_line_number = 1
        file_content = get_file_content(file_name)
        return result + "\n" + view_file_content(current_open_file, file_content, current_line_number, current_line_number + display_line_count)

    @tool
    def submit()->str:
        """Submit the patch from all previous edits and end the session.

        Returns:
            str: The result of the submission.
        """
        patch_content = vm_run_tool('get_patch_file', [vm.repo_dir])[:-1]
        return patch_content
    
    return {k: v for k, v in locals().items() if isinstance(v, BaseTool)}