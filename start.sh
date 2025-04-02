#!/bin/bash

echo "=== 开始执行启动脚本 ==="
echo "当前目录: $(pwd)"
echo "脚本路径: $0"

# 创建日志目录
echo "创建日志目录..."
mkdir -p /var/log/vnc
echo "日志目录创建完成"

# 记录启动时间
echo "=== 容器启动时间: $(date) ===" > /var/log/vnc/start.log

# 启动虚拟显示和 VNC
echo "启动 Xvfb..."
Xvfb :1 -screen 0 1280x720x16 &
echo "Xvfb 启动完成"

export DISPLAY=:1
echo "设置 DISPLAY=:1"

echo "启动 x11vnc..."
x11vnc -display :1 -forever -shared -rfbport 5900 -passwd mypassword &
echo "x11vnc 启动完成"

# 启动 noVNC（将 VNC 转换为 WebSocket）
echo "启动 websockify..."
websockify -D --web /usr/share/novnc 6080 localhost:5900 &
echo "websockify 启动完成"

# 保持容器运行
echo "所有服务启动完成，保持容器运行"
exec tail -f /var/log/vnc/start.log
