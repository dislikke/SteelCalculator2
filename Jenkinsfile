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



  }

  post {
    always {
      sh 'docker rm -f steelcalculator_test || true'
    }
  }
}
