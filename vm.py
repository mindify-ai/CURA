import docker
import tarfile
import os
class VirtualMachine:
    def __init__(self, image_name: str):
        self._image_name = image_name
        self._client = docker.from_env()
    
    def __enter__(self):
        self._container = self._client.containers.run(self._image_name, detach=True, tty=True)
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        self._container.remove(force=True)
    
    def run_command(self, command)->str:
        result = self._container.exec_run(command).output.decode('utf-8')
        return result

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
    