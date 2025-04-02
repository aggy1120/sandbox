import docker
from docker.errors import NotFound, APIError
import threading
import subprocess
import os
import sys
import tarfile
import io
from typing import Dict, List, Optional, Union, IO
from config import SandboxConfig

class Sandbox:
    """
    沙盒类，代表一个Docker容器实例
    """
    def __init__(self, container_id: str, session_id: str, host_port: Optional[int] = None):
        self.container_id = container_id
        self.session_id = session_id
        self.host_port = host_port
        self._lock = threading.Lock()
        
    def remove(self) -> bool:
        """
        删除沙盒（停止并删除容器）
        """
        with self._lock:
            try:
                client = docker.from_env()
                container = client.containers.get(self.container_id)
                container.stop()
                container.remove()
                return True
            except Exception as e:
                print(f"删除沙盒失败: {str(e)}")
                return False
    
    def upload_file(self, host_path: str, container_path: str) -> bool:
        """
        将文件从宿主机上传到沙盒容器中
        
        参数:
            host_path: 宿主机上的文件或目录路径
            container_path: 容器中的目标路径 (目录)
            
        返回:
            操作是否成功
        """
        try:
            # 检查文件是否存在
            if not os.path.exists(host_path):
                print(f"错误: 文件 {host_path} 不存在")
                return False
                
            # 检查文件大小
            file_size = os.path.getsize(host_path) if os.path.isfile(host_path) else sum(
                os.path.getsize(os.path.join(dirpath, filename))
                for dirpath, _, filenames in os.walk(host_path)
                for filename in filenames
            )
            print(f"上传内容大小: {file_size} 字节")
            
            # 创建tar文件
            tar_stream = io.BytesIO()
            with tarfile.open(fileobj=tar_stream, mode='w') as tar:
                # 如果是目录，添加整个目录
                if os.path.isdir(host_path):
                    basename = os.path.basename(host_path.rstrip('/'))
                    tar.add(host_path, arcname=basename)
                else:
                    # 如果是文件，直接添加
                    tar.add(host_path, arcname=os.path.basename(host_path))
            tar_stream.seek(0)
            
            # 获取容器对象
            client = docker.from_env()
            container = client.containers.get(self.container_id)
            
            # 复制文件到容器
            print(f"正在将 {host_path} 上传到容器 {self.container_id} 的 {container_path} 目录...")
            container.put_archive(container_path, tar_stream)
            print("文件上传成功")
            return True
            
        except Exception as e:
            print(f"上传文件时出错: {str(e)}")
            return False
    
    def download_file(self, container_path: str, host_path: str) -> bool:
        """
        从沙盒容器下载文件到宿主机
        
        参数:
            container_path: 容器中的文件或目录路径
            host_path: 宿主机上的目标路径 (目录)
            
        返回:
            操作是否成功
        """
        try:
            # 确保参数不为空
            if not container_path or not host_path:
                print(f"错误: 容器路径或宿主机路径不能为空")
                return False
                
            # 创建目标目录（如果不存在）
            host_dir = os.path.dirname(host_path)
            if host_dir and not os.path.exists(host_dir):
                os.makedirs(host_dir, exist_ok=True)
                print(f"已创建目录: {host_dir}")
                
            # 获取容器对象
            client = docker.from_env()
            container = client.containers.get(self.container_id)
            
            # 从容器获取文件
            print(f"正在从容器 {self.container_id} 的 {container_path} 下载文件...")
            tar_stream, stat = container.get_archive(container_path)
            
            # 将生成器转换为字节流
            tar_data = b''.join(chunk for chunk in tar_stream)
            tar_stream = io.BytesIO(tar_data)
            
            # 解压文件到宿主机
            with tarfile.open(fileobj=tar_stream) as tar:
                dest_dir = os.path.dirname(host_path)
                members = tar.getmembers()
                
                if len(members) == 1 and not os.path.isdir(host_path):
                    # 如果只有一个文件且目标不是目录，直接提取到目标路径
                    member = members[0]
                    extract_path = dest_dir if dest_dir else "."
                    member.name = os.path.basename(host_path)
                    print(f"将 {member.name} 提取到 {extract_path}")
                    tar.extract(member, path=extract_path)
                else:
                    # 否则提取到目标目录
                    extract_path = host_path if os.path.isdir(host_path) else dest_dir
                    extract_path = extract_path if extract_path else "."
                    print(f"将多个文件提取到 {extract_path}")
                    tar.extractall(path=extract_path)
                
            print(f"文件已成功下载到: {host_path}")
            return True
            
        except Exception as e:
            print(f"下载文件时出错: {str(e)}")
            return False
    
    def exec(self, command: List[str], 
             stdout: Union[int, IO, None] = subprocess.PIPE,
             stderr: Union[int, IO, None] = subprocess.STDOUT,
             shell: bool = False,
             env: Optional[Dict[str, str]] = None,
             cwd: Optional[str] = None,
             universal_newlines: bool = True) -> subprocess.Popen:
        """
        在沙盒内执行命令并返回subprocess.Popen对象，以便于流式获取输出
        
        参数:
            command: 要执行的命令及参数列表
            stdout: 标准输出目标 (默认: subprocess.PIPE)
            stderr: 标准错误输出目标 (默认: subprocess.STDOUT，与标准输出合并)
            shell: 是否使用shell执行命令 (默认: False)
            env: 环境变量字典 (默认: None，使用当前环境)
            cwd: 工作目录 (默认: None)
            universal_newlines: 是否使用通用换行符模式 (默认: True)
            
        返回:
            subprocess.Popen对象，可用于流式获取命令输出
            
        用法示例:
            process = sandbox.exec(["ls", "-la"])
            for line in process.stdout:
                print(line, end='')
            return_code = process.wait()
        """
        try:
            # 构建完整的docker exec命令
            docker_cmd = ["docker", "exec"]
            
            # 如果指定了环境变量，添加到命令中
            if env:
                for key, value in env.items():
                    docker_cmd.extend(["-e", f"{key}={value}"])
            
            # 如果指定了工作目录，添加到命令中
            if cwd:
                docker_cmd.extend(["-w", cwd])
                
            # 添加容器ID
            docker_cmd.append(self.container_id)
            
            # 添加要执行的命令
            if shell:
                # 如果使用shell，将command合并为单个字符串
                if isinstance(command, list):
                    cmd_str = " ".join(command)
                else:
                    cmd_str = command
                docker_cmd.extend(["bash", "-c", cmd_str])
            else:
                # 直接添加命令和参数
                docker_cmd.extend(command)
                
            print(f"执行命令: {' '.join(docker_cmd)}")
            
            # 使用subprocess.Popen执行命令
            process = subprocess.Popen(
                docker_cmd,
                stdout=stdout,
                stderr=stderr,
                universal_newlines=universal_newlines,
                bufsize=1,  # 行缓冲
                env=os.environ.copy()  # 使用当前环境变量
            )
            
            return process
            
        except Exception as e:
            print(f"执行命令时出错: {str(e)}")
            # 创建一个"失败"的Popen对象，避免返回None
            class FailedPopen:
                def __init__(self, error_message):
                    self.returncode = 1
                    self.error_message = error_message
                    self.stdout = open(os.devnull, 'r')  # 一个空的文件对象
                    
                def wait(self):
                    return self.returncode
                    
                def poll(self):
                    return self.returncode
                    
                def communicate(self):
                    return "", self.error_message
            
            return FailedPopen(str(e))

class SandboxFactory:
    """
    沙盒工厂类，单例模式
    """
    _instance = None
    _lock = threading.RLock()  # 使用可重入锁
    
    def __new__(cls, *args, **kwargs):
        # 使用更简单的单例实现，避免可能的死锁
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    try:
                        cls._instance = super().__new__(cls)
                        print("成功创建 SandboxFactory 实例")
                    except Exception as e:
                        print(f"创建 SandboxFactory 实例时出错: {str(e)}")
                        raise
        return cls._instance
    
    def __init__(self, config: SandboxConfig):
        """
        初始化沙盒工厂
        
        参数:
            config: 沙盒配置对象
        """
        # 使用更安全的初始化方式
        try:
            with self._lock:
                if not hasattr(self, 'initialized') or not self.initialized:
                    print("初始化 SandboxFactory...")
                    self.config = config
                    self.client = docker.from_env()
                    self.sandboxes: Dict[str, Sandbox] = {}  # session_id -> Sandbox
                    self._sandbox_lock = threading.RLock()  # 使用可重入锁
                    self._initialize_image()
                    self.initialized = True
                    print("SandboxFactory 初始化完成")
        except Exception as e:
            print(f"初始化 SandboxFactory 时出错: {str(e)}")
            raise
    
    def _initialize_image(self):
        """
        初始化Docker镜像
        """
        try:
            image_name = f"{self.config.image_name}:{self.config.image_tag}"
            self.client.images.get(image_name)
            print(f"镜像 {image_name} 已存在")
        except docker.errors.ImageNotFound:
            print(f"镜像 {image_name} 不存在，正在拉取...")
            self.client.images.pull(image_name)
            print("镜像拉取完成")
        except Exception as e:
            print(f"初始化镜像时出错: {str(e)}")
            raise
    
    def run(self, session_id: str, host_port: Optional[int] = None) -> Optional[Sandbox]:
        """
        创建并启动一个新的沙盒
        
        参数:
            session_id: 会话ID，用于唯一标识沙盒
            host_port: 宿主机端口，用于映射容器的VNC端口 (5900)，如果为None则不进行端口映射
            
        返回:
            Sandbox对象，如果创建失败则返回None
        """
        try:
            with self._sandbox_lock:
                # 检查是否已存在相同session_id的沙盒
                if session_id in self.sandboxes:
                    print(f"会话 {session_id} 已存在沙盒")
                    return self.sandboxes[session_id]
                
                try:
                    # 准备端口映射配置
                    ports = {}
                    if host_port is not None:
                        # 将容器的VNC端口映射到宿主机指定端口
                        container_port = self.config.vnc_port
                        ports = {f"{container_port}/tcp": host_port}
                        print(f"设置端口映射: 容器端口 {container_port} -> 宿主机端口 {host_port}")
                    
                    # 创建容器
                    container = self.client.containers.run(
                        f"{self.config.image_name}:{self.config.image_tag}",
                        working_dir=self.config.working_dir,
                        detach=True,
                        mem_limit=self.config.mem_limit,
                        cpu_period=self.config.cpu_period,
                        cpu_quota=self.config.cpu_quota,
                        network_disabled=False if host_port else self.config.network_disabled,  # 如果映射端口，需要启用网络
                        privileged=self.config.privileged,
                        environment=self.config.environment,
                        ports=ports  # 添加端口映射
                    )
                    
                    # 创建沙盒对象
                    sandbox = Sandbox(container.id, session_id, host_port)
                    self.sandboxes[session_id] = sandbox
                    print(f"创建沙盒成功: session_id={session_id}, container_id={container.id}" + 
                        (f", 端口映射: {self.config.vnc_port} -> {host_port}" if host_port else ""))
                    return sandbox
                    
                except Exception as e:
                    print(f"创建沙盒失败: {str(e)}")
                    # 尝试清理可能部分创建的容器
                    try:
                        containers = self.client.containers.list(all=True)
                        for container in containers:
                            if session_id in container.name:
                                print(f"清理部分创建的容器: {container.id}")
                                container.remove(force=True)
                    except Exception as cleanup_error:
                        print(f"清理容器时出错: {str(cleanup_error)}")
                    return None
        except Exception as e:
            print(f"运行沙盒时发生未预期的错误: {str(e)}")
            return None
    
    def remove(self, session_id: str) -> bool:
        """
        删除指定的沙盒
        
        参数:
            session_id: 会话ID
            
        返回:
            是否删除成功
        """
        try:
            with self._sandbox_lock:
                if session_id in self.sandboxes:
                    sandbox = self.sandboxes[session_id]
                    if sandbox.remove():
                        del self.sandboxes[session_id]
                        return True
                return False
        except Exception as e:
            print(f"删除沙盒时出错: {str(e)}")
            return False
    
    def list(self) -> List[Sandbox]:
        """
        获取所有沙盒列表
        
        返回:
            沙盒对象列表
        """
        try:
            with self._sandbox_lock:
                return list(self.sandboxes.values())
        except Exception as e:
            print(f"列出沙盒时出错: {str(e)}")
            return []
    
    @classmethod
    def get_instance(cls, config: Optional[SandboxConfig] = None) -> 'SandboxFactory':
        """
        获取SandboxFactory单例
        
        参数:
            config: 配置对象，仅在首次创建实例时使用
            
        返回:
            SandboxFactory实例
        """
        try:
            if cls._instance is None and config is not None:
                return cls(config)
            elif cls._instance is None:
                raise ValueError("首次创建实例时必须提供配置对象")
            return cls._instance
        except Exception as e:
            print(f"获取 SandboxFactory 实例时出错: {str(e)}")
            raise 