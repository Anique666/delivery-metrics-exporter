# Delivery Metrics Exporter

A small Python application that exports DORA-style delivery metrics to a JSON
report, validated and packaged by a Jenkins declarative pipeline.

> This README is updated with the real build evidence after the pipeline runs.
> See [docs/EVIDENCE.md](docs/EVIDENCE.md) for captured console logs and build
> statuses.

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
pytest -v tests
python -m exporter.main
cat output/metrics-report.json
```

## Layout

```
delivery-metrics-exporter/
├── exporter/            # application package (stdlib only)
├── config/metrics.json  # sample delivery-metrics configuration
├── tests/               # automated tests (pytest / unittest)
├── jenkins/             # Jenkins controller Dockerfile + init scripts
├── Jenkinsfile          # declarative pipeline (4 stages)
└── requirements*.txt
```

## Jenkins

```bash
docker build -t jenkins-lab:lts jenkins/
docker run -d --name jenkins-lab -p 8080:8080 \
  -v jenkins-lab-home:/var/jenkins_home \
  -e JENKINS_ADMIN_ID=admin \
  -e JENKINS_ADMIN_PASSWORD='<choose-a-password>' \
  -e GITHUB_REPO_URL=https://github.com/Anique666/delivery-metrics-exporter.git \
  jenkins-lab:lts
```

The job `delivery-metrics-exporter` is created automatically with
**Pipeline script from SCM** (Git, branch `*/main`, script path `Jenkinsfile`).
