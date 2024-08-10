from flask import Flask, request, jsonify, Response
import git
import os
import traceback

class Interface:
    def find_file(self, file_name: str, dir: str)->str:
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
    
    def search_dir(self, search_term: str, dir: str) -> str:
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

    def search_file(self, search_term: str, file_name: str) -> str:
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
    def get_patch_file(self, repo_path: str)->str:
        """Returns the diff of the current version of the software.

        Args:
            repo_path (str): The path to the repository.

        Returns:
            str: The diff of the current version of the software.
        """
        if not os.path.exists(repo_path):
            raise Exception(f"Repository path {repo_path} does not exist.")
        repo = git.Repo(repo_path)
        diff = repo.git.diff()
        return diff
        
    def get_file_content(self, file_path: str)->str:
        """Returns the content of a file.

        Args:
            file_path (str): The path to the file.

        Returns:
            str: The content of the file.
        """
        if not os.path.exists(file_path):
            raise Exception(f"File path {file_path} does not exist.")
        with open(file_path, 'r', encoding='utf-8') as f:
            contents = f.read()
        return contents
    
    def write_file(self, file_path: str, content: str):
        """Writes content to a file.

        Args:
            file_path (str): The path to the file.
            content (str): The content to write to the file.
        """
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

app = Flask(__name__)
port = 5001

@app.post('/<command>')
def execute_command(command):
    try:
        args = request.get_json()
        interface = Interface()
        func = getattr(interface, command)
        result = func(*args)
        return jsonify(result)
    except Exception as e:
        error_message = f"{str(e)}\n{traceback.format_exc()}"
        return Response(error_message, status=400)
   
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=port)