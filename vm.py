import docker
import tarfile
import os
class VirtualMachine:
    def __init__(self, image_name: str, tool_file_path: str | None = None):
        self._image_name = image_name
        self._client = docker.from_env()
        self._current_dir = '/'
        self._tool_file_path = tool_file_path
    
    def __enter__(self):
        self._container = self._client.containers.run(self._image_name, detach=True, tty=True)
        if self._tool_file_path:
            self.copy_file(self._tool_file_path, '/tool.py')
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        self._container.remove(force=True)
        
    def init_repo_env(self, repo_name: str, commit_hash: str)->None:
        repo_url = f"https://github.com/{repo_name}.git"
        self.run_command(f"git clone {repo_url}")
        self.repo_dir = repo_name.split('/')[-1]
        self.run_command(f"cd {self.repo_dir} && git checkout {commit_hash}")
    
    def run_command(self, command)->str:
        command_with_cd = f"cd {self._current_dir} && {command}"
        result = self._container.exec_run(f"bash -c '{command_with_cd}'").output.decode('utf-8')
        return result
    
    def cd(self, path)->None:
        self._current_dir = path
        
    def run_tool(self, tool_name: str, args: list[str] = [])->str:
        args = [f'\"{arg}\"' for arg in args]
        args_str = ' '.join(args)
        return self.run_command(f"python /tool.py {tool_name} {args_str}")

    def copy_file(self, src, dst):
        self.run_command(f'touch {dst}')
        tar = tarfile.open(src + '.tar', mode='w')
        try:
            tar.add(src)
        finally:
            tar.close()

        data = open(src + '.tar', 'rb').read()
        self._container.put_archive(os.path.dirname(dst), data)
        self.run_command(f'mv {os.path.dirname(dst)}/{os.path.basename(src)} {dst}')
        os.remove(src + '.tar')
    