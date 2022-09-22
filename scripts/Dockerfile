FROM ubuntu:20.04
ARG DEBIAN_FRONTEND="noninteractive"

ARG WGET_ARGS="-q --show-progress --progress=bar:force:noscroll"

RUN apt-get -y update && \
    apt-get -y upgrade && \
    apt-get install -y --no-install-recommends make git python3-dev python3-pip \
    python3-setuptools python3-wheel python3.8-venv && \
    apt-get -y clean && \
    apt-get -y autoremove && \
    rm -rf /var/lib/apt/lists/*

WORKDIR .
COPY requirements.txt .
COPY requirements-dev.txt .

# pip 22.2.2. supports editable installs for pyproject.toml
RUN pip install --no-cache-dir pip==22.2.2 && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir -r requirements-dev.txt

WORKDIR /home/project
