import time
import uuid
import socket
import sys
import traceback
import os
from config import SandboxConfig
from sandbox import SandboxFactory

def find_free_port():
    """找到一个可用的端口"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]

def demonstrate_file_transfer(sandbox):
    """演示如何上传文件到沙盒和从沙盒下载文件"""
    if not sandbox:
        print("沙盒不可用，无法执行文件传输")
        return
    
    # 创建测试文件
    test_file_path = "test_upload.txt"
    with open(test_file_path, "w") as f:
        f.write("这是一个测试文件，用于演示上传到沙盒容器。\n")
        f.write("包含多行内容...\n")
        f.write("测试完成后会被删除。\n")
    
    try:
        # 上传文件到沙盒
        print("\n1. 上传文件到沙盒")
        container_path = "/tmp"
        success = sandbox.upload_file(test_file_path, container_path)
        
        if success:
            print("文件上传成功")
            
            # 验证文件已上传
            print("\n2. 验证文件已上传")
            process = sandbox.exec(["cat", f"/tmp/{os.path.basename(test_file_path)}"])
            for line in process.stdout:
                print(f"文件内容: {line}", end='')
            
            # 在沙盒中创建一个新文件
            print("\n3. 在沙盒中创建一个新文件")
            process = sandbox.exec([
                "bash", "-c", 
                "echo '这是在沙盒中创建的文件' > /tmp/sandbox_file.txt && "
                "echo '将被下载到宿主机' >> /tmp/sandbox_file.txt && "
                "echo '文件创建完成' && "
                "cat /tmp/sandbox_file.txt"
            ])
            for line in process.stdout:
                print(line, end='')
            
            # 检查文件是否创建成功
            process = sandbox.exec(["ls", "-la", "/tmp/sandbox_file.txt"])
            print("\n验证文件是否创建成功:")
            for line in process.stdout:
                print(f"文件信息: {line}", end='')
            
            # 从沙盒下载文件
            print("\n4. 从沙盒下载文件")
            # 确保下载路径是绝对路径或相对于当前工作目录的路径
            download_path = os.path.abspath("downloaded_from_sandbox.txt")
            print(f"下载路径: {download_path}")
            success = sandbox.download_file("/tmp/sandbox_file.txt", download_path)
            
            if success:
                print("文件下载成功")
                # 显示下载的文件内容
                print("\n5. 显示下载的文件内容:")
                with open(download_path, "r") as f:
                    content = f.read()
                    print(content)
                
                # 清理下载的文件
                if os.path.exists(download_path):
                    os.remove(download_path)
                    print("已删除下载的文件")
                else:
                    print(f"警告: 下载的文件 {download_path} 不存在，无法删除")
            else:
                print("文件下载失败")
        else:
            print("文件上传失败")
    
    finally:
        # 清理测试文件
        if os.path.exists(test_file_path):
            os.remove(test_file_path)
            print("已删除测试上传文件")

def demonstrate_exec(sandbox):
    """演示如何使用exec方法执行命令并流式获取输出"""
    if not sandbox:
        print("沙盒不可用，无法执行命令")
        return
    
    print("\n执行简单命令:")
    process = sandbox.exec(["echo", "Hello from Docker Sandbox"])
    # 读取并打印输出
    for line in process.stdout:
        print(f"输出: {line}", end='')
    # 等待命令完成
    return_code = process.wait()
    print(f"命令退出码: {return_code}")
    
    print("\n执行带环境变量的命令:")
    process = sandbox.exec(
        ["bash", "-c", "echo 环境变量值: $DEMO_VAR"],
        env={"DEMO_VAR": "这是一个测试环境变量"}
    )
    for line in process.stdout:
        print(f"输出: {line}", end='')
    return_code = process.wait()
    print(f"命令退出码: {return_code}")
    
    print("\n执行多行输出命令:")
    process = sandbox.exec(["bash", "-c", "for i in {1..5}; do echo 行 $i; sleep 0.2; done"])
    for line in process.stdout:
        print(f"输出: {line}", end='')
    return_code = process.wait()
    print(f"命令退出码: {return_code}")
    
    print("\n执行指定工作目录的命令:")
    process = sandbox.exec(["pwd"], cwd="/tmp")
    for line in process.stdout:
        print(f"输出: {line}", end='')
    return_code = process.wait()
    print(f"命令退出码: {return_code}")
    
    print("\n执行shell命令:")
    process = sandbox.exec("echo 当前目录内容: && ls -la", shell=True)
    for line in process.stdout:
        print(f"输出: {line}", end='')
    return_code = process.wait()
    print(f"命令退出码: {return_code}")

def main():
    """演示如何使用沙盒系统"""
    try:
        print("=== 沙盒系统演示 ===")

        # 创建配置
        print("\n1. 创建沙盒配置")
        config = SandboxConfig(
            image_name="ubuntu",
            image_tag="latest",
            mem_limit="512m",
            network_disabled=False,  # 允许网络连接以便映射端口
            environment={"DEMO_ENV": "hello_world"},
            vnc_port=5900  # 设置VNC端口
        )
        print(f"配置创建成功: {config}")

        # 获取工厂实例
        print("\n2. 尝试获取沙盒工厂实例")
        try:
            factory = SandboxFactory.get_instance(config)
            print("工厂实例获取成功")
        except Exception as e:
            print(f"获取工厂实例失败: {str(e)}")
            print(f"错误详情: {traceback.format_exc()}")
            sys.exit(1)

        # 启动沙盒
        print("\n3. 创建普通沙盒实例")
        session_id = "demo_session_1"
        print(f"创建沙盒: session_id={session_id}")
        sandbox1 = None
        try:
            sandbox1 = factory.run(session_id)
            if sandbox1:
                print(f"沙盒创建成功: container_id={sandbox1.container_id}")
            else:
                print("沙盒创建失败")
        except Exception as e:
            print(f"创建沙盒出错: {str(e)}")
            print(f"错误详情: {traceback.format_exc()}")
        
        # 演示文件传输功能
        print("\n4. 演示文件传输功能")
        if sandbox1:
            try:
                demonstrate_file_transfer(sandbox1)
            except Exception as e:
                print(f"文件传输时出错: {str(e)}")
                print(f"错误详情: {traceback.format_exc()}")
        
        # 演示在沙盒中执行命令
        print("\n5. 在沙盒中执行命令")
        if sandbox1:
            try:
                demonstrate_exec(sandbox1)
            except Exception as e:
                print(f"执行命令时出错: {str(e)}")
                print(f"错误详情: {traceback.format_exc()}")
        
        # 启动带端口映射的沙盒
        print("\n6. 创建带端口映射的沙盒实例")
        host_port = find_free_port()
        session_id = "demo_session_2"
        print(f"创建沙盒: session_id={session_id}, 映射VNC端口到宿主机端口 {host_port}")
        sandbox2 = None
        try:
            sandbox2 = factory.run(session_id, host_port=host_port)
            if sandbox2:
                print(f"沙盒创建成功: container_id={sandbox2.container_id}, VNC端口映射: 5900 -> {host_port}")
            else:
                print("沙盒创建失败")
        except Exception as e:
            print(f"创建沙盒出错: {str(e)}")
            print(f"错误详情: {traceback.format_exc()}")
        
        # 列出所有沙盒
        print("\n7. 列出所有沙盒")
        try:
            all_sandboxes = factory.list()
            print(f"沙盒总数: {len(all_sandboxes)}")
            for i, sandbox in enumerate(all_sandboxes):
                port_info = f", 端口映射: 5900 -> {sandbox.host_port}" if sandbox.host_port else ""
                print(f"沙盒 {i+1}: session_id={sandbox.session_id}, container_id={sandbox.container_id}{port_info}")
        except Exception as e:
            print(f"列出沙盒时出错: {str(e)}")
            print(f"错误详情: {traceback.format_exc()}")

        # 验证端口映射
        if sandbox2 and sandbox2.host_port:
            print(f"\n8. 验证端口映射 (宿主机端口: {sandbox2.host_port})")
            try:
                import docker
                client = docker.from_env()
                container = client.containers.get(sandbox2.container_id)
                container_info = client.api.inspect_container(container.id)
                port_bindings = container_info['HostConfig']['PortBindings']
                
                if f"{config.vnc_port}/tcp" in port_bindings:
                    mapped_port = port_bindings[f"{config.vnc_port}/tcp"][0]['HostPort']
                    print(f"成功验证端口映射: 容器端口 {config.vnc_port} -> 宿主机端口 {mapped_port}")
                else:
                    print("未找到端口映射配置")
            except Exception as e:
                print(f"验证端口映射时出错: {str(e)}")
                print(f"错误详情: {traceback.format_exc()}")

        # 删除所有沙盒
        print("\n9. 删除所有沙盒")
        try:
            all_sandboxes = factory.list()
            for sandbox in all_sandboxes:
                print(f"删除沙盒: session_id={sandbox.session_id}")
                try:
                    if factory.remove(sandbox.session_id):
                        print("删除成功")
                    else:
                        print("删除失败")
                except Exception as e:
                    print(f"删除沙盒 {sandbox.session_id} 时出错: {str(e)}")
        except Exception as e:
            print(f"获取沙盒列表时出错: {str(e)}")

        print("\n=== 演示结束 ===")
    
    except Exception as e:
        print(f"演示过程中出现未处理的错误: {str(e)}")
        print(f"错误详情: {traceback.format_exc()}")
        sys.exit(1)

if __name__ == "__main__":
    main() 