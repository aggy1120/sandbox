FROM ubuntu:22.04
# 安装基础组件
ENV TZ=Asia/Shanghai \
    DEBIAN_FRONTEND=noninteractive

# 只执行一次 apt-get update
RUN apt-get update

# 安装 Python 3.12 和依赖
RUN apt-get install -y \
    build-essential \
    libssl-dev \
    zlib1g-dev \
    libbz2-dev \
    libreadline-dev \
    libsqlite3-dev \
    wget \
    curl \
    llvm \
    libncurses5-dev \
    libncursesw5-dev \
    xz-utils \
    tk-dev \
    libffi-dev \
    liblzma-dev \
    git \
    ca-certificates && \
    cd /tmp && \
    wget https://www.python.org/ftp/python/3.12.0/Python-3.12.0.tgz && \
    tar -xf Python-3.12.0.tgz && \
    cd Python-3.12.0 && \
    ./configure --enable-optimizations && \
    make -j $(nproc) && \
    make altinstall && \
    cd .. && \
    rm -rf Python-3.12.0 Python-3.12.0.tgz && \
    ln -sf /usr/local/bin/python3.12 /usr/bin/python && \
    ln -sf /usr/local/bin/pip3.12 /usr/bin/pip && \
    ln -sf /usr/local/bin/pip3.12 /usr/bin/pip3 && \
    python -m pip install --upgrade pip

# 安装其他基础组件
RUN apt-get install -y \
    xfce4 x11vnc xvfb \
    novnc websockify \
    libgtk-4-1 libgraphene-1.0-0 libxslt1.1 libwoff1 libvpx7 libevent-2.1-7 libgstreamer-gl1.0-0 libgstreamer-plugins-bad1.0-0 libflite1 libharfbuzz-icu0 libenchant-2-2 libhyphen0 libmanette-0.2-0 libgles2 \
    fonts-liberation xdg-utils dnsutils ttf-wqy-zenhei

# 安装 vi
RUN apt-get install -y vim

# 配置 VNC 密码
RUN mkdir -p ~/.vnc && echo "mypassword" | x11vnc -storepasswd - ~/.vnc/passwd

# 安装 Python 依赖
RUN pip config set global.index-url https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple && \
    pip install flask docker browser-use playwright && \
    playwright install chromium

# 启动脚本
COPY start.sh /start.sh
RUN chmod +x /start.sh
RUN mkdir -p /var/log/vnc && chmod 777 /var/log/vnc
EXPOSE 5900 6080 5000
CMD ["/bin/bash", "-c", "set -x && /start.sh"]