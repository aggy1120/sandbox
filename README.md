# SandboxFactory 和 Sandbox 类接口文档

## 概述

沙盒系统由两个主要类组成：`SandboxFactory` 和 `Sandbox`。`SandboxFactory` 负责创建和管理docker沙盒实例，采用单例模式确保整个应用中只有一个工厂实例。`Sandbox` 类代表一个Docker容器实例，提供了容器操作的各种方法。

## SandboxConfig 类

配置类，用于定义沙盒的各项参数。

```python
@dataclass
class SandboxConfig:
    image_name: str = "ubuntu"          # Docker镜像名称
    image_tag: str = "latest"           # Docker镜像标签
    working_dir: str = "/opt"           # 容器默认工作目录
    default_command: str = "tail -f /dev/null"  # 容器默认命令
    mem_limit: Optional[str] = None     # 内存限制，如"512m"
    cpu_period: Optional[int] = None    # CPU周期限制
    cpu_quota: Optional[int] = None     # CPU配额限制
    network_disabled: bool = True       # 是否禁用网络
    vnc_port: int = 5900                # VNC端口，用于端口映射
    privileged: bool = False            # 是否使用特权模式
    environment: Optional[Dict[str, str]] = None  # 环境变量
```

## SandboxFactory 类

### 说明

`SandboxFactory` 是一个单例类，负责创建和管理沙盒实例。所有沙盒实例都通过此工厂创建，确保资源的统一管理和状态跟踪。

### 方法

#### get_instance

```python
@classmethod
def get_instance(cls, config: Optional[SandboxConfig] = None) -> 'SandboxFactory'
```

**描述**：获取SandboxFactory的单例实例  
**参数**：
- `config`：可选，沙盒配置对象，仅在首次创建实例时使用  
**返回**：SandboxFactory实例  
**异常**：
- 如果首次调用时未提供config，会抛出ValueError
- 如果创建或初始化过程中出现错误，会打印错误信息并抛出异常

#### run

```python
def run(self, session_id: str, host_port: Optional[int] = None) -> Optional[Sandbox]
```

**描述**：创建并启动一个新的沙盒实例  
**参数**：
- `session_id`：会话ID，用于唯一标识沙盒
- `host_port`：可选，宿主机端口，用于映射容器的VNC端口(5900)  
**返回**：Sandbox对象，如果创建失败则返回None  
**线程安全**：是，使用内部锁确保线程安全  
**说明**：
- 如果已存在相同session_id的沙盒，则直接返回现有沙盒
- 如果指定了host_port，会自动启用网络并设置端口映射

#### remove

```python
def remove(self, session_id: str) -> bool
```

**描述**：删除指定的沙盒  
**参数**：
- `session_id`：会话ID  
**返回**：操作是否成功  
**线程安全**：是  
**说明**：
- 会停止并删除对应的Docker容器
- 从内部映射中移除沙盒实例
- 即使发生错误也会打印信息并返回False，不会抛出异常

#### list

```python
def list(self) -> List[Sandbox]
```

**描述**：获取所有沙盒列表  
**参数**：无  
**返回**：沙盒对象列表  
**线程安全**：是  
**说明**：
- 返回工厂管理的所有沙盒实例的列表
- 如果发生错误，返回空列表

## Sandbox 类

### 说明

`Sandbox` 类代表一个Docker容器实例，提供了对容器的各种操作方法。

### 属性

- `container_id`：Docker容器ID
- `session_id`：会话ID，用于标识沙盒
- `host_port`：可选，映射到宿主机的端口

### 方法

#### remove

```python
def remove(self) -> bool
```

**描述**：删除沙盒（停止并删除容器）  
**参数**：无  
**返回**：操作是否成功  
**线程安全**：是  
**说明**：
- 会先停止容器再删除，确保资源完全释放
- 如果操作失败会打印错误信息并返回False

#### exec

```python
def exec(self, command: List[str], 
         stdout: Union[int, IO, None] = subprocess.PIPE,
         stderr: Union[int, IO, None] = subprocess.STDOUT,
         shell: bool = False,
         env: Optional[Dict[str, str]] = None,
         cwd: Optional[str] = None,
         universal_newlines: bool = True) -> subprocess.Popen
```

**描述**：在沙盒内执行命令并返回subprocess.Popen对象，便于流式获取输出  
**参数**：
- `command`：要执行的命令及参数列表，或shell命令字符串
- `stdout`：标准输出目标
- `stderr`：标准错误输出目标
- `shell`：是否使用shell执行命令
- `env`：环境变量字典
- `cwd`：工作目录
- `universal_newlines`：是否使用通用换行符模式  
**返回**：subprocess.Popen对象，可用于流式获取命令输出  
**说明**：
- 即使执行失败也返回一个模拟的Popen对象，避免返回None导致调用代码崩溃
- 支持shell模式执行复杂命令

**用法示例**：
```python
process = sandbox.exec(["ls", "-la"])
for line in process.stdout:
    print(line, end='')
return_code = process.wait()
```

#### upload_file

```python
def upload_file(self, host_path: str, container_path: str) -> bool
```

**描述**：将文件从宿主机上传到沙盒容器中  
**参数**：
- `host_path`：宿主机上的文件或目录路径
- `container_path`：容器中的目标路径（目录）  
**返回**：操作是否成功  
**说明**：
- 支持上传单个文件或整个目录
- 会自动计算上传内容的大小
- 如果文件不存在或操作失败会返回False

#### download_file

```python
def download_file(self, container_path: str, host_path: str) -> bool
```

**描述**：从沙盒容器下载文件到宿主机  
**参数**：
- `container_path`：容器中的文件或目录路径
- `host_path`：宿主机上的目标路径  
**返回**：操作是否成功  
**说明**：
- 支持下载单个文件或整个目录
- 会自动创建必要的目标目录
- 智能处理不同的下载情况（文件到文件、文件到目录等）
- 如果参数为空或操作失败会返回False

## 使用示例

### 基本使用

```python
# 创建配置
config = SandboxConfig(
    image_name="ubuntu",
    image_tag="latest",
    mem_limit="512m",
    network_disabled=False
)

# 获取工厂实例
factory = SandboxFactory.get_instance(config)

# 创建沙盒实例
sandbox = factory.run("user_session_123")

# 在沙盒中执行命令
process = sandbox.exec(["echo", "Hello world"])
for line in process.stdout:
    print(line, end='')

# 删除沙盒
factory.remove("user_session_123")
```

### 文件传输示例

```python
# 上传文件到容器
sandbox.upload_file("local_file.txt", "/tmp")

# 验证文件内容
process = sandbox.exec(["cat", "/tmp/local_file.txt"])
for line in process.stdout:
    print(line, end='')

# 在容器创建文件
sandbox.exec(["bash", "-c", "echo 'Test content' > /tmp/container_file.txt"])

# 从容器下载文件
sandbox.download_file("/tmp/container_file.txt", "downloaded_file.txt")
```

### 端口映射示例

```python
# 创建带端口映射的沙盒
host_port = 6080
sandbox = factory.run("vnc_session", host_port=host_port)

# 该沙盒现在可以通过宿主机的6080端口访问容器的5900端口服务
print(f"VNC服务可通过 localhost:{host_port} 访问")
```

## 注意事项

1. `SandboxFactory` 是单例模式，整个应用只应有一个实例
2. 所有沙盒实例由工厂创建和管理，不应直接实例化 `Sandbox` 类
3. 操作完成后应调用 `remove` 方法释放资源
4. 所有方法都有线程安全保障，可以在多线程环境中使用
5. 端口映射功能需要关闭网络隔离（将 `network_disabled` 设为 `False`）
