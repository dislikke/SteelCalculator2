FROM jenkins/jenkins:lts-jdk17

USER root

# Устанавливаем Docker CLI + git
RUN apt-get update && \
    apt-get install -y docker.io git curl && \
    rm -rf /var/lib/apt/lists/*

# Добавляем jenkins в группу docker
RUN groupadd -f docker && usermod -aG docker jenkins

USER jenkins

