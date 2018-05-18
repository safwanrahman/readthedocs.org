FROM ubuntu:16.04
MAINTAINER Read the Docs <support@readthedocs.com>

ENV LANG C.UTF-8

# System dependencies
RUN apt-get -y update && apt-get -y install git-core postgresql-client \
                                            python-pip wget python3 python3-venv \
                                            libxml2-dev libxslt-dev zlib1g-dev \
    apt-transport-https \
    ca-certificates \
    curl \
    software-properties-common

RUN curl -fsSL https://download.docker.com/linux/ubuntu/gpg | apt-key add -

RUN add-apt-repository \
   "deb [arch=amd64] https://download.docker.com/linux/ubuntu \
   $(lsb_release -cs) \
   stable"

RUN apt-get -y update
RUN apt-get -y install docker-ce

WORKDIR /app

# UID and GID from readthedocs/user
RUN groupadd --gid 205 docs
RUN useradd -m --uid 1005 --gid 205 docs

# Create directory for user builds
RUN mkdir -m 777 /app/user_builds

# Download latest pip requirements for the project
RUN pip install -U pip
COPY ./requirements/pip.txt /app/requirements/pip.txt
RUN pip install -r /app/requirements/pip.txt

# Install some python utilities
RUN pip install ipdb dj-cmd

USER 33

CMD ["/bin/bash"]