from flask import Flask, request, jsonify, Response
import git
import os
import traceback
from directory_tree import display_tree
from typing import Optional


class Interface:

    def directory_tree(self, dir: str, max_depth: int) -> Optional[str]:
        return display_tree(dir_path=dir, string_rep=True, max_depth=max_depth)

    def find_file(self, file_name: str, dir: str) -> list[str]:
        """Finds all files with the given name in a directory.

        Args:
            file_name (str): Name of the file to search for.
            dir (str): Directory to search in.

        Returns:
            list[str]: A list of file paths.
        """

        result = []
        for root, _, files in os.walk(dir):
            for file in files:
                if file_name in file:
                    result.append(os.path.abspath(os.path.join(root, file)))
        return result

    def search_dir(self, search_term: str, dir: str) -> dict[str, int]:
        """
        Search for a specific term in all files within a directory.

        Args:
            search_term (str): Term to search for within the files.
            dir (str): Directory to search within.

        Returns:
            dict[str, int]: A dictionary containing file paths as keys and match counts as values.
        """
        matches = {}
        total_matches = 0

        for root, _, files in os.walk(dir):
            for file in files:
                if len(matches) >= 50:
                    break
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        contents = f.readlines()
                    match_count = sum(1 for line in contents if search_term in line)
                    if match_count > 0:
                        matches[os.path.abspath(file_path)] = match_count
                        total_matches += match_count
                except Exception:
                    continue

        return matches

    def search_file(self, search_term: str, file_name: str) -> dict[int, str]:
        """
        Search for a specific term in a file and list lines with matches.

        Args:
            search_term (str): Term to search for within the file.
            file_name (str): Name of the file to search within.

        Returns:
            dict[int, str]: A dictionary with line numbers as keys and matching lines as values.
        """
        matches = {}

        with open(file_name, "r", encoding="utf-8") as f:
            contents = f.readlines()

        for i, line in enumerate(contents):
            if search_term in line:
                matches[i + 1] = line.strip()
            if len(matches) >= 50:
                break

        return matches

    def get_patch_file(self, repo_path: str) -> str:
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

    def get_file_content(self, file_path: str) -> str:
        """Returns the content of a file.

        Args:
            file_path (str): The path to the file.

        Returns:
            str: The content of the file.
        """
        if not os.path.exists(file_path):
            raise Exception(f"File path {file_path} does not exist.")
        with open(file_path, "r", encoding="utf-8") as f:
            contents = f.read()
        return contents

    def write_file(self, file_path: str, content: str) -> bool:
        """Writes content to a file.
        
        Args:
            file_path (str): The path to the file.
            content (str): The content to write to the file.
            
        Returns:
            bool: True if the file was written successfully, False otherwise.
        """
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        return os.path.isfile(file_path)
    
    def file_exists(self, file_path: str) -> bool:
        """Checks if a file exists.

        Args:
            file_path (str): The path to the file.

        Returns:
            bool: True if the file exists, False otherwise.
        """
        return os.path.exists(file_path)


app = Flask(__name__)
port = 5001


@app.post("/<command>")
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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=port)
