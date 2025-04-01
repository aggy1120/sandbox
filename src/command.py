import docker
from docker.errors import NotFound, APIError
import sys
import subprocess

def check_container_status(client, container_id_or_name):
    """
    检查容器运行状态
    
    参数:
        client: Docker客户端对象
        container_id_or_name: 容器ID或名称
    """
    try:
        container = client.containers.get(container_id_or_name)
        print(f"容器 {container_id_or_name} 状态: {container.status}")
        print(f"容器详细信息: {container.attrs['State']}")
        
        if container.status == "running":
            print("容器启动成功！")
            return True, container
        else:
            print(f"容器未运行，当前状态: {container.status}")
            # 检查容器日志，查看是否有错误信息
            logs = container.logs().decode('utf-8')
            if logs:
                print(f"容器日志:\n{logs}")
            return False, container
    except NotFound:
        print(f"容器 {container_id_or_name} 不存在")
        return False, None
    except APIError as e:
        print(f"检查容器状态失败: {e.explanation if hasattr(e, 'explanation') else str(e)}")
        return False, None

def execute_command_in_docker():
    """
    在Docker容器中执行命令并实时获取格式化输出
    """
    try:
        # 定义要执行的命令，移除-it参数
        command = [
            'docker', 'exec', 'a08bfe6cb272',
            'bash', '-c', 'DISPLAY=:1 /opt/OpenManus/.venv/bin/python /opt/OpenManus/demo.py'
        ]

        print(f"执行命令: {' '.join(command)}")
        
        # 使用 subprocess.Popen 来执行命令并实时获取输出
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # 将stderr重定向到stdout
            universal_newlines=True    # 使用通用换行符
        )

        # 实时读取输出
        for line in process.stdout:
            print(line, end='')  # 直接打印输出，保持原有格式

        # 等待进程完成并获取返回码
        rc = process.wait()
        return rc
    except Exception as e:
        print(f"执行命令时出错: {str(e)}")
        return 1

try:
    # 尝试连接到Docker守护进程
    client = docker.from_env()
    print("成功连接到Docker")
    
    # 检查镜像是否存在
    try:
        client.images.get("a346c75fc52e2c96c37ee9e523df3dbb95ab923726de9ebcc3eacb54cfa1c879")
        print("镜像已存在")
    except docker.errors.ImageNotFound:
        print("镜像不存在，正在拉取...")
        client.images.pull("ubuntu")
        print("镜像拉取完成")
    
    # 检查是否有同名容器已存在
    try:
        existing = client.containers.get("a08bfe6cb272")
        print(f"已存在同名容器，状态: {existing.status}")
        if existing.status != "running":
            print("尝试删除已有的非运行容器...")
            existing.remove(force=True)
            print("已删除同名容器")
    except NotFound:
        print("无同名容器存在，可以创建新容器")
    
    
    # 检查容器状态
    is_running, container = check_container_status(client, "sandbox_test")
    
    if is_running and container:
        # 在容器中执行命令
        print("尝试在容器中执行命令...")
        execute_command_in_docker()
        # exec_result = container.exec_run("sh /opt/OpenManus/run.sh")
        # exec_output = container.exec_run(cmd='sh /opt/OpenManus/run.sh', stdout=True, stderr=True, stream=True)
        # 处理输出流
        # for line in exec_output:
        #     print(line.decode('utf-8', 'replace').strip())
        # print(f"命令执行结果: {exec_result.output.decode('utf-8')}")
    else:
        print("容器未成功启动，无法执行命令")

except Exception as e:
    print(f"出现错误: {str(e)}")
    sys.exit(1) 
