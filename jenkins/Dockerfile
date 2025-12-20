FROM jenkins/jenkins:lts-jdk17

USER root

# Install docker CLI
RUN apt-get update \
 && apt-get install -y --no-install-recommends docker.io curl git \
 && rm -rf /var/lib/apt/lists/*

USER jenkins
