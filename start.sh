#!/bin/bash
# 启动虚拟显示和 VNC
Xvfb :1 -screen 0 1280x720x16 &
export DISPLAY=:1
x11vnc -display :1 -forever -shared -rfbport 5900 -passwd mypassword &
# 启动 noVNC（将 VNC 转换为 WebSocket）
websockify -D --web /usr/share/novnc 6080 localhost:5900 &
tail -f /dev/null
