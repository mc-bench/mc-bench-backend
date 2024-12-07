FROM node:18-slim

RUN apt-get update && apt-get install -y \
    wget \
    curl \
    gcc \
    make \
    libbz2-dev \
    libffi-dev \
    libgdbm-dev \
    libncursesw5-dev \
    libreadline-dev \
    libsqlite3-dev \
    libssl-dev \
    tk-dev \
    xz-utils \
    zlib1g-dev \
    libxi-dev \
    libx11-dev \
    libxext-dev \
    mesa-common-dev \
    libgl1-mesa-dev \
    libpixman-1-dev \
    libcairo2-dev \
    libpango1.0-dev \
    libjpeg-dev \
    libgif-dev \
    librsvg2-dev \
    libgl1-mesa-dev \
    libxi-dev \
    libxrender-dev \
    libxext-dev \
    libx11-dev \
    xvfb \
    ffmpeg \
    libavcodec-extra \
    libavfilter-extra \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Download and install Python 3.12.7
WORKDIR /tmp
RUN wget https://www.python.org/ftp/python/3.12.7/Python-3.12.7.tgz \
    && tar xzf Python-3.12.7.tgz \
    && cd Python-3.12.7 \
    && ./configure --enable-optimizations \
    && make -j $(nproc) \
    && make install \
    && cd .. \
    && rm -rf Python-3.12.7 Python-3.12.7.tgz

# Install pip
RUN curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py \
    && python3 get-pip.py \
    && rm get-pip.py

RUN python3 -m pip install setuptools

RUN ln -s /usr/local/bin/python3 /usr/local/bin/python

WORKDIR /app

COPY package.json package-lock.json ./

RUN npm install

CMD cp /build-scripts/build-script.js build-script.js && xvfb-run -a node build-script.js
