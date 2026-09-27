pipeline {
    agent any

    options {
        timestamps()
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '20'))
    }

    environment {
        IMAGE_NAME = 'task-tracker'
        APP_IMAGE = "task-tracker:${BUILD_NUMBER}"
        STAGING_URL = 'http://127.0.0.1:8081'
        PROD_URL = 'http://127.0.0.1:8080'
    }

    stages {
        stage('Build') {
            steps {
                sh '''
                    set -eu
                    mkdir -p dist reports
                    GIT_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo local)
                    docker build --pull -t "$APP_IMAGE" -t "$IMAGE_NAME:git-$GIT_SHA" .
                    docker save "$APP_IMAGE" | gzip > "dist/task-tracker-${BUILD_NUMBER}.tar.gz"
                '''
                archiveArtifacts artifacts: 'dist/*.tar.gz', fingerprint: true
            }
        }

        stage('Test') {
            steps {
                sh '''
                    set -eu
                    python3 -m unittest discover -s tests -v
                    docker run --rm "$APP_IMAGE" python -m py_compile app.py task_store.py
                '''
            }
        }

        stage('Code Quality') {
            steps {
                sh '''
                    set -eu
                    mkdir -p reports
                    docker run --rm -v "$PWD:/src" -w /src python:3.13-alpine sh -c '
                        pip install --no-cache-dir ruff radon >/dev/null &&
                        ruff check app.py task_store.py tests &&
                        radon cc app.py task_store.py -j > reports/radon.json
                    '
                    python3 quality_gate.py reports/radon.json
                '''
                archiveArtifacts artifacts: 'reports/radon.json', fingerprint: true
            }
        }

        stage('Security') {
            steps {
                sh '''
                    set -eu
                    mkdir -p reports
                    docker run --rm -v "$PWD:/src" -w /src python:3.13-alpine sh -c '
                        pip install --no-cache-dir bandit >/dev/null &&
                        bandit -r app.py task_store.py -f json -o reports/bandit.json
                    '
                    docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
                        -v "$PWD/reports:/reports" aquasec/trivy:latest image \
                        --ignore-unfixed --severity CRITICAL --exit-code 1 \
                        --format json --output /reports/trivy.json "$APP_IMAGE"
                '''
            }
            post {
                always {
                    archiveArtifacts artifacts: 'reports/bandit.json,reports/trivy.json', allowEmptyArchive: true, fingerprint: true
                }
            }
        }

        stage('Deploy') {
            steps {
                sh '''
                    set -eu
                    APP_IMAGE="$APP_IMAGE" docker compose -p tasktracker-staging -f docker-compose.staging.yml up -d --force-recreate
                    for i in 1 2 3 4 5 6 7 8 9 10; do
                        if curl -fsS "$STAGING_URL/health"; then exit 0; fi
                        sleep 2
                    done
                    docker compose -p tasktracker-staging -f docker-compose.staging.yml logs
                    exit 1
                '''
            }
        }

        stage('Release') {
            steps {
                sh '''
                    set -eu
                    PREVIOUS_IMAGE=$(docker inspect -f '{{.Config.Image}}' task-tracker-prod 2>/dev/null || true)
                    printf '%s\n' "$PREVIOUS_IMAGE" > dist/previous-prod-image.txt

                    RELEASE_IMAGE="$IMAGE_NAME:release-${BUILD_NUMBER}"
                    docker tag "$APP_IMAGE" "$RELEASE_IMAGE"
                    rm -f monitoring/alerts.log
                    APP_IMAGE="$RELEASE_IMAGE" docker compose \
                        -p tasktracker-prod -f docker-compose.production.yml up -d --force-recreate

                    healthy=0
                    for i in 1 2 3 4 5 6 7 8 9 10; do
                        if curl -fsS "$PROD_URL/health"; then healthy=1; break; fi
                        sleep 2
                    done

                    if [ "$healthy" -ne 1 ]; then
                        echo "New release failed health check."
                        docker compose -p tasktracker-prod -f docker-compose.production.yml logs
                        if [ -n "$PREVIOUS_IMAGE" ]; then
                            echo "Rolling back to $PREVIOUS_IMAGE"
                            APP_IMAGE="$PREVIOUS_IMAGE" docker compose \
                                -p tasktracker-prod -f docker-compose.production.yml up -d --force-recreate
                        fi
                        exit 1
                    fi
                '''
                archiveArtifacts artifacts: 'dist/previous-prod-image.txt', fingerprint: true
            }
        }

        stage('Monitoring') {
            steps {
                sh '''
                    set -eu
                    for i in 1 2 3 4 5 6 7 8 9 10; do
                        if curl -fsS http://127.0.0.1:9090/-/ready >/dev/null && \
                           curl -fsS http://127.0.0.1:9093/-/ready >/dev/null; then break; fi
                        sleep 2
                    done

                    curl -fsS "$PROD_URL/metrics" | grep -q tasktracker_http_requests_total
                    curl -fsS -X POST "$PROD_URL/simulate-alert" >/dev/null

                    delivered=0
                    for i in 1 2 3 4 5 6 7 8 9 10; do
                        COUNT=$(curl -fsS http://127.0.0.1:9095/received | python3 -c 'import json,sys; print(json.load(sys.stdin)["count"])')
                        if [ "$COUNT" -gt 0 ]; then delivered=1; break; fi
                        sleep 3
                    done
                    curl -fsS -X POST "$PROD_URL/reset-alert" >/dev/null
                    test "$delivered" -eq 1
                    echo "Prometheus is scraping successfully and Alertmanager delivered the simulated incident."
                '''
            }
        }
    }

    post {
        failure {
            sh '''
                echo "Pipeline failed. Staging logs:"
                docker compose -p tasktracker-staging -f docker-compose.staging.yml logs --tail=100 || true
                echo "Production logs:"
                docker compose -p tasktracker-prod -f docker-compose.production.yml logs --tail=100 || true
            '''
        }
        always {
            archiveArtifacts artifacts: 'monitoring/alerts.log', allowEmptyArchive: true, fingerprint: true
        }
    }
}
