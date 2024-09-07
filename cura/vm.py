import docker
import tarfile
import os
from cura.interface import Interface, port
from cura import interface
import requests
import time
import socket
import threading
import platform
import shlex
import logging
from cura.code_base import CodeBase
from typing import Optional
from swebench.harness.constants import MAP_REPO_VERSION_TO_SPECS, USE_X86
from swebench.harness.utils import get_environment_yml, get_requirements
from typing import TypedDict

class VirtualMachine:
    """
    A Basic Virtual Machine class that can run commands and copy files to and from the VM.
    """

    def __init__(self, image_name: str, logger: Optional[logging.Logger] = None):
        self._image_name = image_name
        self._client = docker.from_env()
        self._container_run_params = {}
        self.logger = logger if logger is not None else logging.getLogger(VirtualMachine.__name__)
        
    file_lock = threading.Lock()

    def __enter__(self):
        try:
            self.logger.info(f"Running container {self._image_name} with params {self._container_run_params}.")
            self._container = self._client.containers.run(
                self._image_name, detach=True, tty=True, **self._container_run_params
            )
            self.logger.info(f"Container {self._image_name} started with ID {self._container.id}.")
        except Exception as e:
            self.logger.error(f"Error running container: {e}")
            raise e
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._container.remove(force=True)

    def run_command(self, command: str) -> str:
        self.logger.info(f"Running command: {command}")
        result = self._container.exec_run(command)
        if result.exit_code != 0:
            self.logger.info(f"Command failed: {command}\n{result.output.decode('utf-8')}")
            raise Exception(f"Command failed: {command}\n{result.output.decode('utf-8')}")
        self.logger.debug(f"Command output: {result.output.decode('utf-8')}")
        return result.output.decode("utf-8")
    
    def bash_command(self, command: str, working_dir: str = '/') -> str:
        if working_dir != '/':
            command = f"cd {working_dir} && {command}"
        safe_command = shlex.quote(command)
        full_command = f"bash -c {safe_command}"
        return self.run_command(full_command)

    def run_command_async(self, command: str):
        self._container.exec_run(command, detach=True)

    def copy_file_to_vm(self, src: str, dst: str):
        self.logger.info(f"Copying file from local to VM: {src} -> {dst}.")
        with self.file_lock:
            with tarfile.open(src + ".tar", "w") as tar:
                tar.add(src, arcname=os.path.basename(src))
            data = open(src + ".tar", "rb").read()
            self._container.put_archive(os.path.dirname(dst), data)
            self.run_command(
                f"mv {os.path.join(os.path.dirname(dst), os.path.basename(src))} {dst}"
            )
            os.remove(src + ".tar")

    def copy_file_from_vm(self, src, dst):
        self.logger.info(f"Copying file from VM to local: {src} -> {dst}.")
        with self.file_lock:
            stream, stat = self._container.get_archive(src)
            with open(dst + ".tar", "wb") as f:
                for chunk in stream:
                    f.write(chunk)

            with tarfile.open(dst + ".tar") as tar:
                tar.extractall(path=os.path.dirname(dst))

            os.rename(os.path.join(os.path.dirname(dst), os.path.basename(src)), dst)
            os.remove(dst + ".tar")


class VM_with_interface(VirtualMachine):
    def __init__(self, image_name: str, logger: Optional[logging.Logger] = None):
        self.logger = logger if logger is not None else logging.getLogger(VM_with_interface.__name__)
        super().__init__(image_name, self.logger.getChild("vm_base"))
        self.interface = Interface()
        self._wrap_interface_methods(self.interface)
        self.container_open_port = port

        self.host_interface_path = interface.__file__
        self.container_interface_path = "/container_interface.py"

    port_lock = threading.Lock()
    
    def get_available_port(self):
        def is_open_port(port: int)-> bool:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                result = s.connect_ex(('localhost', port))
                return result != 0
        current_port = 1024
        while not is_open_port(current_port):
            current_port += 1
        return current_port
    
    
    def __enter__(self):
        with self.port_lock:
            self.host_open_port = self.get_available_port()
            self.logger.info(f"Host open port: {self.host_open_port}")
            self._container_run_params["ports"] = {
                f"{self.container_open_port}/tcp": self.host_open_port
            }
            super().__enter__()
            time.sleep(0.1)
        self.copy_file_to_vm(self.host_interface_path, self.container_interface_path)
        self.run_command_async(f"bash -c 'python {self.container_interface_path}'")
        self.logger.info("Started interface server.")
        time.sleep(0.3)
        return self

    def method_decorator(self, method):
        def wrapper(*args):
            self.logger.info(f"Calling method {method.__name__} with args {args}.")
            url = f"http://localhost:{self.host_open_port}/{method.__name__}"
            response = requests.post(url, json=list(args))
            if response.status_code == 200:
                self.logger.debug(f"Method {method.__name__} returned {response.json()}.")
                return response.json()
            else:
                error_dict = response.json()
                raise Exception(error_dict["error"], error_dict["traceback"])
                

        return wrapper

    def _wrap_interface_methods(self, interface: Interface):
        for attr_name in dir(interface):
            attr = getattr(interface, attr_name)
            if callable(attr) and not attr_name.startswith("__"):
                setattr(interface, attr_name, self.method_decorator(attr))

class SWEInput(TypedDict):
    repo: str
    instance_id: str
    base_commit: str
    patch: str
    test_patch: str
    problem_statement: str
    hints_text: str
    created_at: str
    version: str
    FAIL_TO_PASS: list
    PASS_TO_PASS: list
    environment_setup_commit: str

class SWEVM(VM_with_interface):
    def __init__(self, data: SWEInput, logger: Optional[logging.Logger] = None, code_base: Optional[CodeBase] = None, create_code_base: bool = True):
        self.logger = logger if logger is not None else logging.getLogger(SWEVM.__name__)
        self.data = data
        super().__init__(self._get_image_name(), self.logger.getChild("vm_interface"))
        self.repo_path = "/" + self.data["repo"].split("/")[-1]
        self.code_base = code_base
        self._create_code_base = create_code_base
    
    @property
    def _repo_name(self):
        return self.data["repo"].replace("/", "_").replace(" ", "-").replace("'", "")

    def __enter__(self):
        super().__enter__()
        self.logger.info(f"Entering SWEVM for {self.data['instance_id']}.")
        self.logger.info(f"Copying repo {self.data['repo']} with commit {self.data['base_commit']} to {self.repo_path}.")
        self._copy_repo(self.data["repo"], self.data["base_commit"])
        self.logger.info(f"Installing environment for {self.data['instance_id']}.")
        self._install_env()
        if self.code_base is None and self._create_code_base:
            self.logger.info(f"Creating code base for {self.data['instance_id']}.")
            self.create_code_base()
        return self
    
    def _copy_repo(self, repo_name: str, commit_hash: str):
        logger = self.logger.getChild("copy_repo")
        logger.info(f"Copying repo {repo_name} with commit {commit_hash} to {self.repo_path}.")
        clone_url = f"https://github.com/{repo_name}.git"
        command = "&&".join([
            f"mkdir {self.repo_path}",
            f"cd {self.repo_path}",
            "git init",
            f"git remote add origin {clone_url}",
            f"git fetch --depth 1 origin {commit_hash}",
            "git checkout FETCH_HEAD",
            "cd .."
        ])
        self.run_command(f"bash -c '{command}'")
        logger.info(f"Copied repo {repo_name} with commit {commit_hash} to {self.repo_path}.")
        
    def _get_image_name(self):
        
        if platform.machine() in {"aarch64", "arm64"}:
            arch = "arm64" if self.data["instance_id"] not in USE_X86 else "x86_64"
        else:
            arch = "x86_64"
        image_name = f"swe:{arch}"
        self.logger.info(f"Getting image name {image_name}.")
        client = docker.from_env()
        if image_name not in [tag for image in client.images.list() for tag in image.tags]:
            self.logger.info(f"Image {image_name} not found, building image.")
            client.images.build(
                path=".",
                dockerfile="docker/swe.Dockerfile",
                buildargs={"TARGETARCH": arch},
                tag=image_name
            )
        else:
            self.logger.info(f"Image {image_name} found.")
        return image_name
            
        
    def _install_env(self):
        logger = self.logger.getChild("install_env")
        logger.info(f"Installing environment for {self.data['instance_id']}.")
        install_configs = MAP_REPO_VERSION_TO_SPECS[self.data["repo"]][self.data["version"]]
        logger.debug(f"Install configs: {install_configs}")
        self.env_name = f"{self._repo_name}__{self.data['version']}"
        logger.debug(f"Environment name: {self.env_name}")
        packages = install_configs.get("packages", "")
        if packages == "requirements.txt":
            logger.info(f"Installing environment from requirements.txt for {self.data['instance_id']}.")
            self.run_command(f"conda create -n {self.env_name} python={install_configs['python']} -y")
            content_reqs = get_requirements(self.data)
            PATH_TO_REQS = "/root/requirements.txt"
            self.interface.write_file(PATH_TO_REQS, content_reqs)
            self.conda_run_command(f"pip install -r {PATH_TO_REQS}")
            self.run_command(f"rm {PATH_TO_REQS}")
            logger.info(f"Installed environment from requirements.txt for {self.data['instance_id']}.")
        elif packages == "environment.yml":
            logger.info(f"Installing environment from environment.yml for {self.data['instance_id']}.")
            self.run_command(f"conda create -c conda-forge -n {self.env_name} python={install_configs['python']} -y",)
            content_env_yml = get_environment_yml(self.data, self.env_name)
            if not install_configs.get("no_use_env"):
                content_env_yml += f'\n  - python={install_configs["python"]}\n'
            PATH_TO_ENV_YML = "/root/environment.yml"
            self.interface.write_file(PATH_TO_ENV_YML, content_env_yml)
            if install_configs.get("no_use_env"):
                self.run_command(f"conda create -c conda-forge -n {self.env_name} python={install_configs['python']} -y")
                self.run_command(f"conda env update -f {PATH_TO_ENV_YML}")
            else:
                self.run_command(f"conda env create --file {PATH_TO_ENV_YML}")
            logger.info(f"Installed environment from environment.yml for {self.data['instance_id']}.")
        else:
            python_env = f"python{install_configs['python']}"
            if self._conda_environment_exists(python_env):
                logger.info(f"Environment {python_env} found, cloning environment.")
                self.run_command(f"conda create --name {self.env_name} --clone {python_env}")
            else:
                logger.info(f"Environment {python_env} not found, creating environment.")
                self.run_command(f"conda create -n {self.env_name} python={install_configs['python']} -y")
        
            if packages.strip():
                logger.info(f"Installing packages {packages} for {self.data['instance_id']}.")
                self.run_command(f"conda install {packages} -y")
                logger.info(f"Installed packages {packages} for {self.data['instance_id']}.")
        
        # Install extra pip packages if specified
        if install_configs.get("pip_packages"):
            logger.info(f"Installing pip packages {install_configs['pip_packages']} for {self.data['instance_id']}.")
            self.conda_run_command(f"pip install {' '.join(install_configs['pip_packages'])}")
            logger.info(f"Installed pip packages {install_configs['pip_packages']} for {self.data['instance_id']}.")
        
        if install_configs.get("pre_install"):
            for pre_install_cmd in install_configs["pre_install"]:
                logger.debug(f"Running pre-install command {pre_install_cmd} for {self.data['instance_id']}.")
                self.conda_run_command(pre_install_cmd, self.repo_path)
        if install_configs.get("install"):
            logger.debug(f"Running install command {install_configs['install']} for {self.data['instance_id']}.")
            self.conda_run_command(install_configs["install"], self.repo_path)
        if install_configs.get("post_install"):
            for post_install_cmd in install_configs["post_install"]:
                logger.debug(f"Running post-install command {post_install_cmd} for {self.data['instance_id']}.")
                self.conda_run_command(post_install_cmd, self.repo_path)
        
        self.conda_run_command("pip install pytest")
        logger.info(f"Installed pytest for {self.data['instance_id']}.")
        
    def conda_run_command(self, command: str, working_dir: str = "/") -> str:
        return self.bash_command(f"source activate {self.env_name} && {command}", working_dir)

    def create_code_base(self):
        logger = self.logger.getChild("create_code_base")
        logger.info(f"Creating code base for {self.data['instance_id']}.")
        code_base_name = f"{self._repo_name}_{self.data['base_commit']}"
        code_base_name = code_base_name.replace(".", "_").replace("-", "_").replace("/", "_").replace(":", "_").replace(" ", "_")
        if len(code_base_name) > 63:
            code_base_name = code_base_name[:63]
        logger.debug(f"Code base name: {code_base_name}")
        self.code_base = CodeBase(code_base_name, self.interface.get_file_content)
        if self.code_base.empty:
            logger.info("Code base is empty, creating new code base.")
            python_files = self.interface.find_file(".py", self.repo_path)
            self.code_base.add_files(python_files)
            logger.info(f"Created code base for {self.data['instance_id']}.")
        else:
            logger.info(f"Code base for {self.data['instance_id']} already exists.")
    def _conda_environment_exists(self, env_name: str) -> bool:
        try:
            self.bash_command(f"conda env list | grep {env_name}")
        except Exception:
            return False
        return True