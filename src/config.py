from dataclasses import dataclass
from typing import Optional, Dict

@dataclass
class SandboxConfig:
    """
    沙盒系统配置类
    """
    # Docker镜像名称
    image_name: str = "ubuntu"
    # Docker镜像标签
    image_tag: str = "latest"
    # 容器默认工作目录
    working_dir: str = "/opt"
    # 容器资源限制
    mem_limit: Optional[str] = None  # 例如: "512m"
    cpu_period: Optional[int] = None
    cpu_quota: Optional[int] = None
    # 容器网络设置
    network_disabled: bool = True
    # 默认开放的VNC端口
    vnc_port: int = 6080
    # 容器安全设置
    privileged: bool = False
    # 容器环境变量
    environment: Optional[Dict[str, str]] = None 