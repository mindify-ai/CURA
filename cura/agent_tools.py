__import__('pysqlite3')
import sys
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
from langchain_core.tools import tool, BaseTool
from typing import Optional
import asyncio
from cura.vm import RepoVM
from cura.file_editor import FileEditor_with_linting
from cura.utils import timeout
import shlex


def create_tools(vm: RepoVM):

    file_editor: Optional[FileEditor_with_linting] = None

    @tool
    def bash_command(command: str, environment_variables: dict = {}) -> str:
        """Runs a bash command in the VM. The command will be executed in the root directory of the repository. If the command takes longer than 120 seconds, it will be terminated. This tool is useful for running any command that you would run in a terminal. Each command is stateless.

        Args:
            command (str): The command to run.
            environment_variables (dict, optional): Environment variables to set before running the command. Defaults to an empty dictionary.

        Returns:
            str: The output of the command.
        """
        env_vars = ' '.join([f'{shlex.quote(k)}={shlex.quote(v)}' for k, v in environment_variables.items()])
        command_with_env_vars = f"env {env_vars} bash -c {shlex.quote(command)}"

        @timeout(120)
        def run_command_with_timeout(command: str) -> str:
            return vm.run_command(command)

        try:
            result = run_command_with_timeout(command_with_env_vars)
        except asyncio.TimeoutError:
            return "Command timed out after 120 seconds. Please try a different command."
        if len(result) > 2000:
            return result[:2000] + "\nOutput truncated. Please narrow your command."
        return result

    @tool
    def directory_tree(dir_path: str = vm.repo_path, max_depth: int = 1) -> str:
        """Generates a tree of the directory structure starting from the given directory. This tool is useful for understanding the structure of the repo or a specific directory within the repo.

        Args:
            dir_path (str, optional): Directory to print the tree of. Defaults to the root directory of the repo.
            max_depth (int, optional): Maximum depth to print the tree. Defaults to 3.

        Returns:
            str: The directory tree.
        """

        result = vm.interface.directory_tree(dir_path, max_depth)
        if len(result) > 2000:
            return "The directory tree is too large to display. Please specify a smaller max_depth."
        return result

    @tool
    def create_file(file_path: str, content: str = "") -> str:
        """Creates a new file at the given path with the provided content. If the file already exists, it will be overwritten.

        Args:
            file_path (str): Path to the file to create.
            content (str, optional): Content to write to the file. Defaults to an empty string.

        Returns:
            str: The content of the file.
        """
        vm.interface.write_file(file_path, content)
        return "File created successfully."

    @tool
    def find_file(file_name: str, dir: str = vm.repo_path) -> str:
        """Finds all files with the given name in dir. If dir is not provided, searches in the root directory of the repo.

        Args:
            file_name (str): Name of the file to search for.
            dir (str, optional): Directory to search in. Defaults to the root directory of the repo.

        Returns:
            str: The result of the search.
        """
        result = vm.interface.find_file(file_name, dir)
        output = f"Found {len(result)} matches for {file_name} in {dir}:\n"
        output += "\n".join(result)
        return output

    #@tool
    def search_dir(search_term: str, dir: str = vm.repo_path) -> str:
        """Searches for a specific term in all files within a directory. If dir is not provided, searches in the root directory of the repo.

        Args:
            search_term (str): Term to search for within the files.
            dir (str, optional): Directory to search in. Defaults to the root directory of the repo.

        Returns:
            str: The result of the search.
        """
        result = vm.interface.search_dir(search_term, dir)
        output = f"Found {len(result)} matches for {search_term} in {dir}:\n"
        output += "\n".join([f"{k} ({v} matches)" for k, v in result.items()]) + "\n"
        output += f"End of matches for {search_term} in {dir}\n"
        if sum(result.values()) > 50:
            output += "Exceeded 50 matches. Please narrow your search term."
        return output

    @tool
    def search_file(search_term: str, file_path: str) -> str:
        """Searches for a specific term in a file and lists lines with matches.

        Args:
            search_term (str): Term to search for within the file.
            file_path (str): Name of the file to search within.

        Returns:
            str: The result of the search.
        """
        if not vm.interface.file_exists(file_path):
            return f"File does not exist. Make sure you provide a valid file path or create the file first. Your repository path is at: {vm.repo_path}"
        result = vm.interface.search_file(search_term, file_path)
        output = f"Found {len(result)} matches for {search_term} in {file_path}:\n"
        output += "\n".join([f"Line {k}: {v}" for k, v in result.items()]) + "\n"
        output += f"End of matches for {search_term} in {file_path}\n"
        if len(result) > 50:
            output += "Exceeded 50 matches. Please narrow your search term."
        return output
    
    @tool
    def search_file_fuzzy(query: str) -> str:
        """Searches for file paths that match the given fuzzy query. The input query will be transformed into an embedding and compared to the repository's file content embeddings. The closest matches will be returned.

        Args:
            query (str): The query to search for.

        Returns:
            str: The result of the search. It will be a list of file paths.
        """
        result = vm.code_base.retrieve_files(query)
        result_paths = [doc.metadata["file_path"] for doc in result]
        output = f"Found {len(result)} matches for {query}:\n"
        output += "\n".join(result_paths) + "\n"
        output += f"End of matches for {query}\n"
        
        return output

    @tool
    def open_file(file_path: str, line_number: int = 1) -> str:
        """Opens the file at the given path in the editor. If line_number is provided, the window will move to include that line. You create a new empty file by providing a path that does not exist. You can only have one file open at a time.

        Args:
            file_path (str): Path to the file to open.
            line_number (int, optional): Line number to move to. Defaults to 1.

        Returns:
            str: The content of the file.
        """
        global file_editor
        if not vm.interface.file_exists(file_path):
            return f"File does not exist. Make sure you provide a valid file path or create the file first. Your repository path is at: {vm.repo_path}"
        content = vm.interface.get_file_content(file_path)
        file_editor = FileEditor_with_linting(
            file_path=file_path,
            write_file_fn=lambda content: vm.interface.write_file(file_path, content),
            file_content=content,
            display_lines=100,
            scroll_line=100,
        )
        file_editor.goto_line(line_number)
        return file_editor.display()
    
    @tool
    def goto_line(line_number: int) -> str:
        """Moves the window to the given line in the editor. You must open a file first.

        Args:
            line_number (int): Line number to move to.

        Returns:
            str: The content of the editor after moving to the line.
        """
        global file_editor
        if file_editor is None:
            return "No file is currently open, please open a file first."
        file_editor.goto_line(line_number)
        return file_editor.display()

    @tool
    def scroll_down() -> str:
        """Scrolls down in the file editor. You must open a file first.

        Returns:
            str: The new content of the editor after scrolling down.
        """
        global file_editor
        if file_editor is None:
            return "No file is currently open, please open a file first."
        file_editor.scroll_down()
        return file_editor.display()

    @tool
    def scroll_up() -> str:
        """Scrolls up in the file editor. You must open a file first.

        Returns:
            str: The new content of the editor after scrolling up.
        """
        global file_editor
        if file_editor is None:
            return "No file is currently open, please open a file first."
        file_editor.scroll_up()
        return file_editor.display()

    @tool
    def edit(begin_line: int, end_line: int, new_content: str) -> str:
        """Replaces lines n through m (inclusive) with the given text in the open file. All of the new_content will be entered, so make sure your indentation is formatted properly. Python files will be checked for syntax errors after the edit. If an error is found, the edit will not be executed. Reading the error message and modifying your command is recommended as issuing the same command will return the same error.

        Args:
            begin_line (int): The line number to begin editing.
            end_line (int): The line number to end editing.
            new_content (str): The new content to replace the lines with.

        Returns:
            str: The new content of the editor after editing.
        """
        global file_editor
        if file_editor is None:
            return "No file is currently open, please open a file first."
        if file_editor.edit(begin_line, end_line, new_content):
            if file_editor.file_path.endswith(".py"):
                lint_errors_by_line = file_editor.lint()
                lint_error = [
                    error
                    for line in range(begin_line, end_line + 1)
                    if line in lint_errors_by_line
                    for error in lint_errors_by_line[line]
                ]
                if not lint_error:
                    return "Edit successful.\n" + file_editor.display()
                else:
                    file_editor.goto_line(begin_line)
                    after_edit = file_editor.display()
                    file_editor.undo()
                    file_editor.goto_line(begin_line)
                    before_edit = file_editor.display()
                    error_messages = "\n".join(lint_error)
                    return f"""Your proposed edit has introduced new syntax error(s). Please understand the fixes and retry your edit. Errors:
{error_messages}
This is how your edit would have looked if applied:
{after_edit}
This is how the file looked before your edit:
{before_edit}
Your changes have NOT been applied. Please fix your edit command and try again.
DO NOT re-run the same failed edit tool. Running it again will lead to the same error."""
            else:
                return (
                    "Edit successful. Here is the new content:\n"
                    + file_editor.display()
                )
        else:
            return "Invalid line numbers."
    @tool
    def submit() -> str:
        """Submit all the repo changes and close the session. You must use this tool after all the changes are made.

        Returns:
            str: The result of the submission.
        """
        patch_content = vm.interface.get_patch_file(vm.repo_path)
        if not patch_content:
            return ""
        else:
            return patch_content

    return {k: v for k, v in locals().items() if isinstance(v, BaseTool)}
