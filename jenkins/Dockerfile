FROM jenkins/jenkins:lts-jdk17

USER root

# Базовые утилиты
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      ca-certificates curl gnupg lsb-release git \
 && rm -rf /var/lib/apt/lists/*

# Docker CLI (docker-ce-cli) из официального репозитория Docker
RUN install -m 0755 -d /etc/apt/keyrings \
 && curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg \
 && chmod a+r /etc/apt/keyrings/docker.gpg \
 && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
    > /etc/apt/sources.list.d/docker.list \
 && apt-get update \
 && apt-get install -y --no-install-recommends docker-ce-cli \
 && rm -rf /var/lib/apt/lists/*

# Docker Compose v2 plugin (чтобы работало `docker compose ...`)
RUN mkdir -p /usr/local/lib/docker/cli-plugins \
 && curl -SL https://github.com/docker/compose/releases/download/v2.27.0/docker-compose-linux-x86_64 \
    -o /usr/local/lib/docker/cli-plugins/docker-compose \
 && chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

# Самопроверка на этапе сборки (очень полезно)
RUN docker --version && docker compose version

USER jenkins
