FROM jenkins/jenkins:lts-jdk17

USER root

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      docker.io git curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# (опционально, но полезно) Docker Compose v2 plugin
RUN mkdir -p /usr/local/lib/docker/cli-plugins \
 && curl -SL https://github.com/docker/compose/releases/download/v2.27.0/docker-compose-linux-x86_64 \
    -o /usr/local/lib/docker/cli-plugins/docker-compose \
 && chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

# проверка что docker реально установился
RUN docker --version && docker compose version || true

USER jenkins
