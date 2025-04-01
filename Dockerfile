FROM ubuntu:22.04
# 安装基础组件
ENV TZ=Asia/Shanghai \
    DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y \
xfce4 x11vnc xvfb \
python3 python3-pip \
novnc websockify \
libgtk-4-1 libgraphene-1.0-0 libxslt1.1 libwoff1 libvpx7 libevent-2.1-7 libgstreamer-gl1.0-0 libgstreamer-plugins-bad1.0-0 libflite1 libharfbuzz-icu0 libenchant-2-2 libhyphen0 libmanette-0.2-0 libgles2 \
fonts-liberation xdg-utils dnsutils ttf-wqy-zenhei
# 安装git、curl
RUN apt-get install git
#安装uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
RUN source $HOME/.local/bin/env
#安装 vi
RUN apt-get install vim

# 配置 VNC 密码
RUN mkdir -p ~/.vnc && echo "mypassword" | x11vnc -storepasswd - ~/.vnc/passwd
# 安装 Python 依赖
RUN pip3 config set global.index-url https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple && pip3 install flask docker
# 启动脚本
COPY start.sh /start.sh
EXPOSE 5900 6080 5000
CMD ["/start.sh"]