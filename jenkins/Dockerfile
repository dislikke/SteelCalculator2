FROM jenkins/jenkins:lts-jdk17

USER root

# Docker CLI + git + curl
RUN apt-get update \
 && apt-get install -y --no-install-recommends docker.io git curl \
 && rm -rf /var/lib/apt/lists/*

USER jenkins

