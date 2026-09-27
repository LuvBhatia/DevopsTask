# Task Tracker - Jenkins DevOps Pipeline

This repository is a compact production-style example for the SIT223/753 HD DevOps task. The application is a Python standard-library REST API with CRUD operations, health checks, Prometheus metrics, tests, Docker deployment, security scanning, release tagging, and an alert-delivery demonstration.

## Application endpoints

- `GET /health` - health and environment
- `GET /tasks` - list tasks
- `POST /tasks` - create a task: `{"title":"Demo"}`
- `GET /tasks/<id>` - get one task
- `PUT /tasks/<id>` - update title/completion
- `DELETE /tasks/<id>` - delete a task
- `GET /metrics` - Prometheus metrics
- `POST /simulate-alert` and `/reset-alert` - controlled monitoring demo

## Run the app without Docker

```bash
python3 app.py
```

Open `http://localhost:8000/health`.

## Run tests

```bash
python3 -m unittest discover -s tests -v
```

## Run a local Docker build

```bash
docker build -t task-tracker:local .
docker run --rm -p 8000:8000 -e APP_ENV=local task-tracker:local
```

## Jenkins prerequisites

The Jenkins agent should have: Git, Python 3, Docker, Docker Compose v2, and curl. It must be able to access the Docker daemon. The pipeline itself downloads code-quality/security tools in isolated containers.

Create a Pipeline job using **Pipeline script from SCM**, point it to this Git repository, and set the script path to `Jenkinsfile`.

## Seven assessed pipeline stages

1. **Build** - creates versioned Docker images and archives a compressed Docker-image artefact.
2. **Test** - runs unit/integration tests and a Python compile check.
3. **Code Quality** - runs Ruff and Radon; the custom quality gate fails on C-or-worse cyclomatic complexity.
4. **Security** - runs Bandit source scanning and Trivy container scanning; Critical findings fail the build.
5. **Deploy** - automatically deploys the built image to a staging container on port 8081 and gates on `/health`.
6. **Release** - promotes the exact tested image to a release tag and deploys production on port 8080.
7. **Monitoring** - starts Prometheus + Alertmanager, verifies the live target, triggers a controlled demo alert, and proves webhook delivery.

## Useful demo URLs after a successful pipeline

- Production API: `http://localhost:8080/health`
- Staging API: `http://localhost:8081/health`
- Prometheus: `http://localhost:9090`
- Alertmanager: `http://localhost:9093`
- Alert receiver status: `http://localhost:9095/received`

## Security evidence

Jenkins archives `reports/bandit.json` and `reports/trivy.json`. In the submitted report, describe the actual issues shown by your run. Do not claim a vulnerability was fixed unless the report demonstrates the fix or mitigation.

## Cleanup

```bash
docker compose -p tasktracker-staging -f docker-compose.staging.yml down
docker compose -p tasktracker-prod -f docker-compose.production.yml down
```
