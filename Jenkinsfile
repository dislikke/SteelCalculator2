pipeline {
  agent any

  stages {
    stage('Checkout') {
      steps {
        checkout scm
      }
    }

    stage('Build Docker image') {
      steps {
        sh 'docker build -t steelcalculator:jenkins .'
      }
    }

    stage('Run & Smoke test') {
      steps {
        sh '''
          set -e
          docker rm -f steelcalculator_test || true
          docker run -d --name steelcalculator_test steelcalculator:jenkins

          echo "Checking that container is running..."
          docker ps --filter "name=steelcalculator_test" --format "table {{.Names}}\t{{.Status}}"

          echo "Waiting for app to become ready..."
          for i in $(seq 1 30); do
            # Проверка через Python (curl не нужен)
            if docker exec steelcalculator_test python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/', timeout=1).read(); print('OK')" 2>/dev/null; then
              echo "OK: app is up"
              exit 0
            fi
            sleep 2
          done

          echo "App did not become ready"
          echo "Last logs:"
          docker logs --tail 200 steelcalculator_test || true
          exit 1
        '''
      }
    }
    stage('Deploy (Docker Run)') {
      steps {
        sh '''
          echo "Deploying application via docker run..."

          docker rm -f steelcalculator_prod || true

          docker run -d \
            --name steelcalculator_prod \
            -p 5001:5000 \
            steelcalculator:jenkins

          echo "Application deployed on http://localhost:5001"
        '''
      }
    }
    stage('Deploy (Docker Run + Postgres)') {
      steps {
        sh '''
          echo "Deploying Postgres + App..."

          # Network (create if not exists)
          docker network create steel_net || true

          # Postgres
          docker rm -f steelcalculator_db_prod || true
          docker run -d \
            --name steelcalculator_db_prod \
            --network steel_net \
            -e POSTGRES_DB=db \
            -e POSTGRES_USER=diana \
            -e POSTGRES_PASSWORD=20041902 \
            -p 5540:5432 \
            -v steel_pgdata:/var/lib/postgresql/data \
            postgres:16

          # App (deploy on 5001 to avoid conflicts)
          docker rm -f steelcalculator_prod || true
          docker run -d \
            --name steelcalculator_prod \
            --network steel_net \
            -p 5001:5000 \
            -e POSTGRES_DB=db \
            -e POSTGRES_USER=diana \
            -e POSTGRES_PASSWORD=20041902 \
            -e POSTGRES_HOST=steelcalculator_db_prod \
            -e POSTGRES_PORT=5432 \
            steelcalculator:jenkins

          echo "Deployed:"
          echo " - App: http://localhost:5001"
          echo " - DB:  localhost:5540 (DataGrip)"
        '''
      }
    }







  }

  post {
    always {
      sh 'docker rm -f steelcalculator_test || true'
    }
  }
}
