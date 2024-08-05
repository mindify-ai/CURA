import argparse
import os
import git

def find_file(file_name: str, dir: str)->str:
    """find files with the given name.

    Args:
        file_name (str): name of the file to search for

    Returns:
        str: a string containing the list of files found
    """
    
    result = f'Files with the name "{file_name}" in {os.path.abspath(dir)}:\n'
    for root, _, files in os.walk(dir):
        for file in files:
            if file_name in file:
                result += os.path.abspath(os.path.join(root, file)) + '\n'
    return result

def search_dir(search_term: str, dir: str) -> str:
    """
    Search for a specific term in all files within a directory.

    Args:
        search_term (str): Term to search for within the files.

    Returns:
        str: A string containing the list of files and matches found.
    """
    matches = []
    total_matches = 0

    for root, _, files in os.walk(dir):
        for file in files:
            if len(matches) >= 50:
                break
            file_path = os.path.join(root, file)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    contents = f.readlines()
                match_count = sum(1 for line in contents if search_term in line)
                if match_count > 0:
                    matches.append(f"{os.path.abspath(file_path)}: {match_count} matches")
                    total_matches += match_count
            except Exception:
                continue

    result = f'Found {total_matches} matches for "{search_term}" in {os.path.abspath(dir)}:\n'
    result += "\n".join(matches)
    result += f'\n\nEnd of matches for "{search_term}" in {os.path.abspath(dir)}.\n'
    if len(matches) == 50:
        result += "Found too many matches. Please narrow down your search.\n"
    return result

def search_file(search_term: str, file_name: str) -> str:
    """
    Search for a specific term in all files within a directory and list lines with matches.

    Args:
        search_term (str): Term to search for within the files.
        file_name (str): Name of the file to search within.

    Returns:
        str: A string containing the list of files and lines with matches found.
    """
    matches = []
    total_matches = 0

    with open(file_name, 'r', encoding='utf-8') as f:
        contents = f.readlines()
    for i, line in enumerate(contents):
        if search_term in line:
            matches.append(f"Line {i+1}: {line.strip()}")
            total_matches += 1
        if len(matches) >= 50:
            break
            
    result = f'Found {total_matches} matches for "{search_term}" in {os.path.abspath(file_name)}:\n'
    result += "\n".join(matches)
    result += f'\n\nEnd of matches for "{search_term}" in {file_name}.\n'
    if len(matches) == 50:
        result += "Found too many matches. Please narrow down your search.\n"
    return result
        

def create_file(file_name: str) -> str:
    """
    Create a new file with the given name.

    Args:
        file_name (str): Name of the file to create.

    Returns:
        str: A message indicating the success or failure of the operation.
    """
    try:
        with open(file_name, 'w'):
            pass
        return f"File created successfully at {os.path.abspath(file_name)}"
    except Exception as e:
        return f"An error occurred: {e}"
    
def edit_file(file_name: str, start_line: str, end_line: str, new_content: str)->str:
    """
    Edit a file by replacing lines within a specified range.

    Args:
        file_name (str): Name of the file to edit.
        start_line (str): Starting line number to replace.
        end_line (str): Ending line number to replace.
        new_content (str): New content to write in place of the old lines.

    Returns:
        str: A message indicating the success or failure of the operation.
    """
    try:
        new_content += '\n'
        start_line = int(start_line)
        end_line = int(end_line)
        with open(file_name, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # Replace the specified range of lines with the new content
        lines[start_line-1:end_line] = new_content.splitlines(keepends=True)

        # Write the updated lines back to the file
        with open(file_name, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        return f"File edited successfully: {os.path.abspath(file_name)}"
    except Exception as e:
        return f"An error occurred: {e}"
    
def view_file(file_name: str) -> str:
    """
    View the contents of a file.

    Args:
        file_name (str): Name of the file to view.

    Returns:
        str: The contents of the file, or an error message if the file could not be read.
    """
    try:
        with open(file_name, 'r', encoding='utf-8') as f:
            contents = f.read()
        return contents
    except Exception as e:
        return f"An error occurred: {e}"
    
def get_patch_file(repo_path: str)->str:
    """
    Get the patch file for the current version of the software.

    Returns:
        str: The contents of the patch file, or an error message if the file could not be read.
    """
    try:
        repo = git.Repo(repo_path)
        diff = repo.git.diff()
        return diff
    except Exception as e:
        return f"An error occurred: {e}"

def execute_command(command: str, *args):
    # Retrieve the corresponding function
    func = globals().get(command)
    if callable(func):
        # Call the function and return the result
        return func(*args)
    else:
        raise ValueError(f"'{command}' is not a valid command")

def main():
    parser = argparse.ArgumentParser(description="Multi-functional command-line tool")
    parser.add_argument('command', type=str, help="The command to execute")
    parser.add_argument('args', nargs='*', type=str, help="Arguments for the command")
    
    args = parser.parse_args()
    command = args.command
    command_args = args.args
    
    try:
        result = execute_command(command, *command_args)
        print(result)
    except ValueError as e:
        print(e)
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == '__main__':
    main()