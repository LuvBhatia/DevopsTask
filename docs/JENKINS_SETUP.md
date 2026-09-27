# Jenkins setup checklist

1. Install Docker Desktop and ensure `docker version` and `docker compose version` work from the same user account that runs Jenkins.
2. Install/start Jenkins and complete the initial setup.
3. Ensure the Jenkins agent has `git`, `python3`, `curl`, `docker`, and `docker compose` on PATH.
4. Give Jenkins permission to access the Docker daemon.
5. Create a new **Pipeline** job.
6. Select **Pipeline script from SCM** -> **Git**, paste your GitHub repository URL, and use `Jenkinsfile` as the script path.
7. Save and choose **Build Now**.
8. After success, capture a screenshot of Jenkins Stage View showing all seven assessed stages green.

If Docker permission errors occur, fix access to the Docker daemon before retrying; do not use `sudo` inside the Jenkinsfile.
