FROM ubuntu:20.04
ARG DEBIAN_FRONTEND="noninteractive"

ARG WGET_ARGS="-q --show-progress --progress=bar:force:noscroll"

RUN apt-get -y update && \
    apt-get -y upgrade && \
    apt-get install -y --no-install-recommends git python3-dev python3-pip \
    python3-setuptools python3-wheel python3.8-venv && \
    apt-get -y clean && \
    apt-get -y autoremove && \
    rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir --upgrade pip && \
pip3 install --no-cache-dir rich==12.5.1 && \
pip3 install --no-cache-dir click==8.1.3 && \
pip3 install --no-cache-dir rich_click==1.5.2 && \
pip3 install --no-cache-dir requests==2.28.1

WORKDIR /home/project
