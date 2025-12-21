pipeline {
  agent any

  environment {
    STACK_DIR = "deploy"
    COMPOSE_FILE = "docker-compose.jenkins.yml"
    IMAGE_TAG = "${env.BUILD_NUMBER}"
    POSTGRES_DB = "db"
    POSTGRES_USER = "diana"
    POSTGRES_PASSWORD = "20041902"
  }

  stages {
    stage('Checkout') {
      steps { checkout scm }
    }

    stage('Build web image') {
      steps {
        sh '''
          set -e
          docker build -t steel_web:${IMAGE_TAG} .
        '''
      }
    }

    stage('Deploy (web + db)') {
      steps {
        sh '''
          set -e
          cd "${STACK_DIR}"

          export IMAGE_TAG="${IMAGE_TAG}"
          export POSTGRES_DB="${POSTGRES_DB}"
          export POSTGRES_USER="${POSTGRES_USER}"
          export POSTGRES_PASSWORD="${POSTGRES_PASSWORD}"

          docker compose -f "${COMPOSE_FILE}" up -d --remove-orphans
          docker compose -f "${COMPOSE_FILE}" ps
        '''
      }
    }
    stage('DB migrate') {
      steps {
        sh '''
          set -e
          cd deploy

          # узнаём имя сети, которую создал compose
          NET=$(docker network ls --format "{{.Name}}" | grep -E '^deploy_default$' || true)
          if [ -z "$NET" ]; then
            NET="deploy_default"
          fi

          # запускаем миграцию отдельным контейнером с теми же env
          docker run --rm --network "$NET" --env-file ../env steel_web:${IMAGE_TAG} flask db upgrade
        '''
      }
    }



    stage('Smoke test') {
      steps {
        sh '''
          set -e
          echo "Waiting for app inside steel_web (http://127.0.0.1:5000/) ..."

          for i in $(seq 1 40); do
            if docker exec steel_web python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/', timeout=2).read(); print('OK')" 2>/dev/null; then
              echo "OK: app is up"
              exit 0
            fi
            sleep 2
          done

          echo "App did not become ready"
          echo "--- APP LOGS ---"
          docker logs --tail 200 steel_web || true
          echo "--- DB LOGS ---"
          docker logs --tail 200 steel_db || true
          exit 1
        '''
      }
    }

  }
}

