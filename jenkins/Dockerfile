FROM jenkins/jenkins:lts-jdk17

USER root

RUN apt-get update \
 && apt-get install -y --no-install-recommends docker.io docker-compose-plugin curl git \
 && rm -rf /var/lib/apt/lists/* \
 && (command -v docker >/dev/null 2>&1 || true) \
 && (command -v docker-compose >/dev/null 2>&1 || true) \
 && (docker compose version >/dev/null 2>&1 || ln -s /usr/libexec/docker/cli-plugins/docker-compose /usr/local/lib/docker/cli-plugins/docker-compose || true)

USER jenkins

