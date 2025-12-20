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
          docker run -d --name steelcalculator_test -p 5000:5000 steelcalculator:jenkins
          for i in $(seq 1 20); do
            if curl -fsS http://localhost:5000/ > /dev/null; then
              echo "OK: app is up"
              exit 0
            fi
            sleep 2
          done
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
