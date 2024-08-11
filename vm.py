import docker
import tarfile
import os
from interface import Interface, port
import interface
import requests
import time
class VirtualMachine:
    """
    A Basic Virtual Machine class that can run commands and copy files to and from the VM.
    """
    def __init__(self, image_name: str):
        self._image_name = image_name
        self._client = docker.from_env()
        self._container_run_params = {}
    
    def __enter__(self):
        self._container = self._client.containers.run(self._image_name, detach=True, tty=True, **self._container_run_params)
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        self._container.remove(force=True)
    
    def run_command(self, command)->str:
        result = self._container.exec_run(command).output.decode('utf-8')
        return result
    
    def run_command_async(self, command):
        self._container.exec_run(command, detach=True)

    def copy_file_to_vm(self, src: str, dst: str):
        with tarfile.open(src + '.tar', 'w') as tar:
            tar.add(src, arcname=os.path.basename(src))
        data = open(src + '.tar', 'rb').read()
        self._container.put_archive(os.path.dirname(dst), data)
        self.run_command(f'mv {os.path.join(os.path.dirname(dst), os.path.basename(src))} {dst}')
        os.remove(src + '.tar')
    
    def copy_file_from_vm(self, src, dst):
        stream, stat = self._container.get_archive(src)
        with open(dst + '.tar', 'wb') as f:
            for chunk in stream:
                f.write(chunk)
        
        with tarfile.open(dst + '.tar') as tar:
            tar.extractall(path=os.path.dirname(dst))
        
        os.rename(os.path.join(os.path.dirname(dst), os.path.basename(src)), dst)
        os.remove(dst + '.tar')
        

class VM_with_interface(VirtualMachine):
    def __init__(self, image_name: str):
        super().__init__(image_name)
        self.interface = Interface()
        self._wrap_interface_methods(self.interface)
        self.container_open_port = port
        self.host_open_port = 5002

        self.host_interface_path = interface.__file__
        self.container_interface_path = '/container_interface.py'

        self._container_run_params['ports'] = {f'{self.container_open_port}/tcp': self.host_open_port}
        
    def __enter__(self):
        super().__enter__()
        self.copy_file_to_vm(self.host_interface_path, self.container_interface_path)
        self.run_command_async(f'python {self.container_interface_path}')
        time.sleep(0.3)
        return self
    
    def method_decorator(self, method):
        def wrapper(*args):
            url = f'http://localhost:{self.host_open_port}/{method.__name__}'
            response = requests.post(url, json=list(args))
            if response.status_code == 200:
                return response.json()
            else:
                return response.text
        return wrapper
    
    def _wrap_interface_methods(self, interface: Interface):
        for attr_name in dir(interface):
            attr = getattr(interface, attr_name)
            if callable(attr) and not attr_name.startswith("__"):
                setattr(interface, attr_name, self.method_decorator(attr))
                
class RepoVM(VM_with_interface):
    def __init__(self, image_name: str, repo_name: str, commit_hash: str):
        super().__init__(image_name)
        self.repo_name = repo_name
        self.commit_hash = commit_hash
        self.repo_path = '/' + self.repo_name.split('/')[-1]
        
    def __enter__(self):
        super().__enter__()
        url = f"https://github.com/{self.repo_name}.git"
        self.run_command(f'git clone {url}')
        self.run_command(f'cd {self.repo_path} && git checkout {self.commit_hash}')
        return self
