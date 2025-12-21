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
      docker rm -f steelcalculator_test || true
      docker run -d --name steelcalculator_test steelcalculator:jenkins

      for i in $(seq 1 30); do
        if docker exec steelcalculator_test curl -fsS http://127.0.0.1:5000/ > /dev/null; then
          echo "OK: app is up"
          exit 0
        fi
        sleep 2
      done

      echo "App did not become ready"
      docker logs steelcalculator_test || true
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
