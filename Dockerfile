FROM ubuntu:16.04
MAINTAINER Read the Docs <support@readthedocs.com>

ENV LANG C.UTF-8

# System dependencies
RUN apt-get -y update && apt-get -y install git-core postgresql-client \
                                            python-pip wget python3 python3-venv \
                                            libxml2-dev libxslt-dev zlib1g-dev docker.io

WORKDIR /app

# UID and GID from readthedocs/user
RUN groupadd --gid 205 docs
RUN useradd -m --uid 1005 --gid 205 docs

# Create directory for user builds
RUN mkdir /app/user_builds
RUN chown -R docs:docs /app/user_builds
VOLUME /app/user_builds

# Download latest pip requirements for the project
RUN pip install -U pip
COPY ./requirements/pip.txt /app/requirements/pip.txt
RUN pip install -r /app/requirements/pip.txt

# Install some python utilities
RUN pip install ipdb dj-cmd

USER 33

CMD ["/bin/bash"]
