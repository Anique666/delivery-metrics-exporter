# Delivery Metrics Exporter — Jenkins CI/CD Pipeline

A small Python application that exports DORA-style delivery metrics as a JSON
report, plus a declarative Jenkins pipeline that validates the code, runs 26
automated tests, and packages a runnable deployment artifact.

| Item | Value |
|---|---|
| GitHub repository | <https://github.com/Anique666/delivery-metrics-exporter> |
| Branch | `main` |
| Jenkins job | `delivery-metrics-exporter` — <http://localhost:8080/job/delivery-metrics-exporter/> |
| Jenkins | 2.580.2 LTS (JDK 21 container), built-in node, 2 executors |
| Pipeline definition | **Pipeline script from SCM** → Git → `Jenkinsfile` |
| Latest verified build | `#5` SUCCESS (recovery run), `#4` FAILURE (controlled failure run) |

> **Actual results vs. illustrative examples.**
> Every build number, timestamp, test count, duration and console excerpt in
> this README was captured from the Jenkins instance described here. Captured
> console logs are committed under [`evidence/`](evidence/) and summarised in
> [`docs/EVIDENCE.md`](docs/EVIDENCE.md). Where an excerpt is illustrative
> (for example a generic expected output), it is explicitly labelled
> **“illustrative”**. Nothing in this document is a screenshot mock-up.

---

## Table of contents

1. [Project Title](#1-project-title)
2. [Problem Statement](#2-problem-statement)
3. [Objectives](#3-objectives)
4. [Technologies Used](#4-technologies-used)
5. [Project Architecture](#5-project-architecture)
6. [Project Directory Structure](#6-project-directory-structure)
7. [Application Functionality](#7-application-functionality)
8. [Delivery Metrics Explained](#8-delivery-metrics-explained)
9. [Python Implementation Overview](#9-python-implementation-overview)
10. [Requirements and Dependencies](#10-requirements-and-dependencies)
11. [GitHub Repository Setup](#11-github-repository-setup)
12. [Jenkins Installation / Prerequisites](#12-jenkins-installation--prerequisites)
13. [Jenkins Pipeline Architecture](#13-jenkins-pipeline-architecture)
14. [Explanation of Every Jenkinsfile Stage](#14-explanation-of-every-jenkinsfile-stage)
15. [Jenkins Pipeline Job Configuration](#15-jenkins-pipeline-job-configuration-pipeline-script-from-scm)
16. [How to Execute the Pipeline](#16-how-to-execute-the-pipeline)
17. [Expected Successful Build Output](#17-expected-successful-build-output)
18. [Deployment Packaging](#18-deployment-packaging)
19. [Deployment Artifact Structure](#19-deployment-artifact-structure)
20. [How to Run the Deployment Artifact Independently](#20-how-to-run-the-deployment-artifact-independently)
21. [Automated Testing Strategy](#21-automated-testing-strategy)
22. [Controlled Failure Demonstration](#22-controlled-failure-demonstration)
23. [How to Recover from a Failed Build](#23-how-to-recover-from-a-failed-build)
24. [Expected Console Output and Build Statuses](#24-expected-console-output-and-build-statuses)
25. [Troubleshooting Common Errors](#25-troubleshooting-common-errors)
26. [Verification Checklist for All Five Examination Requirements](#26-verification-checklist-for-all-five-examination-requirements)
27. [Viva / Demonstration Explanation](#27-viva--demonstration-explanation)
28. [Conclusion](#28-conclusion)
29. [Laboratory Demonstration – Step-by-Step](#laboratory-demonstration--step-by-step)
30. [Likely Viva Questions and Answers](#likely-viva-questions-and-answers)

---

## 1. Project Title

**Jenkins Pipeline for a Python Delivery Metrics Exporter**

## 2. Problem Statement

Automate the delivery-metrics application using Jenkins. The pipeline must
validate the Python project and produce a runnable deployment artifact.

The solution has to demonstrate:

1. A Python metrics exporter with source code, a requirements file and
   automated tests, committed and pushed to GitHub.
2. A `Jenkinsfile` with four stages: **Source Checkout**, **Dependency
   Installation / Build**, **Automated Test / Validation**, and
   **Deployment Packaging**.
3. A Jenkins **Pipeline script from SCM** job that retrieves the GitHub
   repository and the `Jenkinsfile` from source control.
4. A successful execution in which dependencies install, tests pass, and the
   exporter source and configuration are copied into a dedicated `deployment/`
   directory.
5. Inspection of stage logs and final status, followed by a **controlled test
   failure** that makes Jenkins mark the build `FAILURE`, then a **recovery**
   build that returns to `SUCCESS`.

## 3. Objectives

- Build a minimal, deterministic Python application with **no unnecessary
  infrastructure** (no Kubernetes, Terraform, Ansible, databases or services).
- Express the whole delivery process as code in a single declarative
  `Jenkinsfile` stored in Git.
- Make failures loud: a non-zero exit code in any stage must stop the pipeline
  and mark the build `FAILURE`, never `UNSTABLE` or `SUCCESS`.
- Produce a self-contained, independently runnable deployment package
  (`deployment/` + `deployment-artifact.zip`).
- Provide a reproducible, documented, examinable setup, including how the
  Jenkins controller itself is provisioned.
- Demonstrate failure detection and recovery with a deterministic, switchable
  mechanism (no random failures).

## 4. Technologies Used

| Technology | Verified version | Role |
|---|---|---|
| Python | 3.12.15 (host) / 3.13.5 (Jenkins agent) | Application runtime; stdlib only |
| pytest | 8.3.4 | Automated test runner + JUnit XML output |
| Jenkins | 2.580.2 LTS, JDK 21 (`jenkins/jenkins:lts-jdk21`) | CI/CD orchestrator |
| Jenkins plugins | `workflow-aggregator` 608.x, `git` 5.11.0, `junit` 1458.1460.x, `pipeline-stage-view` 2.41, `timestamper` 1.30, `ws-cleanup` 0.49, `github` 1.47.0, `credentials-binding` 728.x | Pipeline, SCM, test reporting |
| Git | 2.55.0 (host) / 2.47.3 (agent) | Version control |
| GitHub | public repository, branch `main` | Source of truth for SCM checkout |
| Docker | 29.7.2 | Hosts the Jenkins controller only |
| Bash / coreutils / zip | zip 3.0 | Pipeline shell steps and artifact creation |
| Groovy (init scripts) | Bundled with Jenkins | Automated job/security provisioning |

Docker is used **only** to run Jenkins, because the host already has Docker and
its system Java is 25 (Jenkins LTS supports Java 17/21). The pipeline itself
contains no Docker steps.

## 5. Project Architecture

```
 Developer workstation
 ┌──────────────────────────────┐
 │ git push origin main         │
 └──────────────┬───────────────┘
                │ HTTPS
                ▼
 ┌──────────────────────────────┐        ┌────────────────────────────────────┐
 │ GitHub                       │        │ Jenkins controller (Docker)        │
 │ Anique666/                   │◄───────┤ job: delivery-metrics-exporter     │
 │   delivery-metrics-exporter  │  SCM   │ Pipeline script from SCM           │
 │  ├── Jenkinsfile             │  poll  │ branch */main, script Jenkinsfile  │
 │  ├── exporter/               │        │                                    │
 │  ├── config/                 │        │  workspace/                        │
 │  └── tests/                  │        │   ├── .venv/      (CI only)        │
 └──────────────────────────────┘        │   ├── deployment/  (runtime files) │
                                         │   ├── deployment-artifact.zip      │
                                         │   └── reports/junit-results.xml    │
                                         │                                    │
                                         │  Stage 1  Source Checkout          │
                                         │  Stage 2  Dependencies / Build     │
                                         │  Stage 3  Tests / Validation       │
                                         │  Stage 4  Deployment Packaging     │
                                         └────────────────────────────────────┘
```

Data flow of a build:

```
GitHub (main) ──checkout──► workspace ──venv+pip──► pytest ──► deployment/ ──zip──► artifact
                                                        │
                                                        └─ JUnit XML ─► Jenkins test report
```

## 6. Project Directory Structure

```
delivery-metrics-exporter/
├── exporter/
│   ├── __init__.py            # package exports, __version__
│   ├── metrics.py             # validation, report building, JSON serialisation
│   └── main.py                # CLI entry point (python -m exporter.main)
├── config/
│   └── metrics.json           # deterministic sample delivery-metrics data
├── tests/
│   ├── __init__.py
│   └── test_metrics.py        # 26 tests incl. controlled-failure switch
├── scripts/
│   └── verify_deployment.sh   # proves the ZIP runs independently
├── jenkins/
│   ├── Dockerfile             # Jenkins controller with Python + plugins
│   ├── plugins.txt            # plugins baked into the image
│   ├── run-jenkins.sh         # start the controller (password via env var)
│   └── init.groovy.d/
│       ├── 01-security.groovy # admin user, root URL, executors
│       └── 02-job.groovy      # creates the Pipeline-script-from-SCM job
├── evidence/                  # captured console logs, job config, artifacts
├── docs/
│   └── EVIDENCE.md            # index of the captured evidence
├── Jenkinsfile                # declarative pipeline (4 mandatory stages)
├── requirements.txt           # runtime dependencies (stdlib only → empty)
├── requirements-dev.txt       # test/CI tooling (pytest)
├── .gitignore
└── README.md
```

The generated `deployment/`, `deployment-artifact.zip`, `.venv/`, `reports/`
and `output/` directories are build products and are git-ignored.

## 7. Application Functionality

The exporter is intentionally small enough to explain in a viva:

1. Reads a JSON configuration file (`config/metrics.json` by default).
2. Validates every metric: numeric, finite, within the metric's allowed range,
   and all four required metrics present.
3. Builds a predictable report dictionary with service name, window, ISO-8601
   UTC timestamp, metric count and a self-describing metric map.
4. Writes the report as pretty-printed JSON to `output/metrics-report.json`.
5. Returns exit code `0` on success and `1` on any configuration or I/O error,
   which is what allows Jenkins to detect failures.

Command-line interface:

```bash
python -m exporter.main --help
python -m exporter.main
python -m exporter.main --config config/metrics.json --output-dir output --filename report.json
```

Actual run (host, Python 3.12.15):

```text
$ python -m exporter.main
Service      : checkout-api
Window (days): 30
Metrics      : 4
Report       : /home/anique/DevOps_SEE/delivery-metrics-exporter/output/metrics-report.json
```

Actual generated report:

```json
{
  "service": "checkout-api",
  "window_days": 30,
  "generated_at": "2026-11-20T07:17:13+00:00",
  "metric_count": 4,
  "metrics": {
    "deployment_frequency_per_day": {
      "label": "Deployment Frequency",
      "value": 3.4,
      "unit": "deployments/day",
      "description": "How often the service is deployed to production per day."
    },
    "lead_time_hours": {
      "label": "Lead Time for Changes",
      "value": 18.5,
      "unit": "hours",
      "description": "Time from commit to running in production."
    },
    "change_failure_rate_percent": {
      "label": "Change Failure Rate",
      "value": 8.0,
      "unit": "%",
      "description": "Percentage of deployments that cause a degradation."
    },
    "mttr_hours": {
      "label": "Mean Time to Recovery (MTTR)",
      "value": 2.25,
      "unit": "hours",
      "description": "Average time to restore service after an incident."
    }
  }
}
```

Error handling example (invalid configuration → exit code 1):

```text
$ python -m exporter.main --config config/missing.json
ERROR: Cannot read configuration file config/missing.json: [Errno 2] No such file or directory: 'config/missing.json'
$ echo $?
1
```

## 8. Delivery Metrics Explained

The four metrics are the DORA (“four keys”) software-delivery indicators.

| Metric | Question it answers | Formula / meaning | Sample value | Unit |
|---|---|---|---|---|
| Deployment Frequency | How often do we ship? | successful production deployments ÷ days in window | 3.4 | deployments/day |
| Lead Time for Changes | How long from commit to production? | median(production timestamp − commit timestamp) | 18.5 | hours |
| Change Failure Rate | How often do deployments cause harm? | failed deployments ÷ total deployments × 100 | 8.0 | % |
| Mean Time to Recovery (MTTR) | How fast do we recover? | total incident downtime ÷ number of incidents | 2.25 | hours |

The exporter does **not** scrape a real production system: the values come from
`config/metrics.json`. This keeps the demonstration deterministic, which is
exactly what a CI lab needs — the pipeline output is predictable and testable.
In a real deployment the same module would be fed by data from GitHub, a CI
system, or an incident tool; only the configuration/collection layer would
change, not the report format.

## 9. Python Implementation Overview

### `exporter/metrics.py`

| Function | Purpose | Failure behaviour |
|---|---|---|
| `validate_metric(name, value)` | Validate one metric, return `float` | raises `MetricError` |
| `validate_metrics(mapping)` | Require all four metrics, reject unknown/missing | raises `MetricError` |
| `load_config(path)` | Read + parse JSON configuration | raises `MetricError` on I/O or JSON errors |
| `build_report(config, generated_at=None)` | Produce the report dict | raises `MetricError` |
| `to_json(report)` | Pretty-print JSON | raises `MetricError` if not serialisable |
| `write_report(report, dir, filename)` | Create output dir + write file | raises `MetricError` on I/O errors |

Validation rules implemented:

- metric name must exist in `METRIC_SPECS`;
- value must be `int`/`float`, **not** `bool` (guards against `true` typos);
- value must be finite (`NaN`/`inf` rejected);
- value must be `>= minimum`; percentage metrics also `<= 100`;
- `window_days` must be a positive integer;
- `service` must be a non-empty string;
- report filename must end in `.json`.

`MetricError` subclasses `ValueError`, so callers can catch one exception type.

### `exporter/main.py`

`main()` parses arguments, loads the configuration, builds and writes the
report, prints a short summary, and returns `0` or `1`. `__main__` raises
`SystemExit(main())`, so the process exit code is correct for Jenkins.

### `config/metrics.json`

```json
{
  "service": "checkout-api",
  "window_days": 30,
  "metrics": {
    "deployment_frequency_per_day": 3.4,
    "lead_time_hours": 18.5,
    "change_failure_rate_percent": 8.0,
    "mttr_hours": 2.25
  }
}
```

## 10. Requirements and Dependencies

**Runtime (`requirements.txt`)** — none. The exporter uses only `json`,
`argparse`, `pathlib`, `datetime` and `math` from the standard library. The
file contains an explanatory comment so the dependency policy is explicit and
the packaged artifact stays dependency-free.

**Test/CI (`requirements-dev.txt`)**:

```text
-r requirements.txt
pytest==8.3.4
```

pytest is the only third-party package; it is pinned for reproducibility and is
**not** shipped in the deployment package.

**Jenkins agent requirements** (the container already provides them):

- `git` — checkout
- `python3`, `python3-venv`, `python3-pip` — virtual environment and tests
- `zip`, `unzip` — artifact creation and verification

**Local requirements**: Python 3.8+ (tested on 3.12.15 and 3.13.5), Git, and
optionally Docker for the Jenkins controller.

## 11. GitHub Repository Setup

Repository: <https://github.com/Anique666/delivery-metrics-exporter> (public,
default branch `main`).

Exact commands used:

```bash
cd delivery-metrics-exporter
git init -b main
git add -A
git commit -m "Add delivery metrics exporter with tests and Jenkins pipeline"
gh repo create delivery-metrics-exporter --public \
  --description "Python delivery-metrics exporter validated and packaged by a Jenkins declarative pipeline" \
  --source . --remote origin --push
```

Verification (actual output):

```text
$ git remote -v
origin  https://github.com/Anique666/delivery-metrics-exporter.git (fetch)
origin  https://github.com/Anique666/delivery-metrics-exporter.git (push)

$ git ls-remote origin main
82a9a97eaeee47015a54b601f9cb5d429d72ee76        refs/heads/main

$ gh repo view --json url,defaultBranchRef,visibility
https://github.com/Anique666/delivery-metrics-exporter | branch=main | PUBLIC
```

Authentication is handled by the GitHub CLI credential helper
(`git config --global credential.https://github.com.helper` →
`gh auth git-credential`). **No token, password or credential is stored in the
repository or printed by the pipeline.** The repository is public, so Jenkins
needs no GitHub credentials — its checkout log says `No credentials specified`.

Manual push (if you re-create the repository yourself):

```bash
git remote add origin https://github.com/<your-user>/delivery-metrics-exporter.git
git push -u origin main
```

## 12. Jenkins Installation / Prerequisites

### Option A — Docker (what this implementation used)

The host has Docker 29.7.2 and Java 25. Jenkins LTS targets Java 17/21, so
Jenkins runs in a container with JDK 21 and a Python toolchain:

```bash
cd delivery-metrics-exporter
docker build -t jenkins-lab:lts jenkins/

export JENKINS_ADMIN_PASSWORD='choose-a-strong-password'
./jenkins/run-jenkins.sh
```

`run-jenkins.sh` starts the container with:

```text
-p 8080:8080 -p 50000:50000
-v jenkins-lab-home:/var/jenkins_home
-e JENKINS_ADMIN_ID=admin
-e JENKINS_ADMIN_PASSWORD=...
-e GITHUB_REPO_URL=https://github.com/Anique666/delivery-metrics-exporter.git
-e GITHUB_BRANCH=*/main
-e JENKINS_JOB_NAME=delivery-metrics-exporter
```

On first boot the init scripts (`jenkins/init.groovy.d/`) create the admin
account, set the root URL and executors, and create the pipeline job. Actual
container log from first boot:

```text
[init] created admin user 'admin'
[init] Jenkins URL = http://localhost:8080/, executors = 2, admin ready = true
[init] created job 'delivery-metrics-exporter'
[init] job 'delivery-metrics-exporter' -> https://github.com/Anique666/delivery-metrics-exporter.git [*/main] scriptPath=Jenkinsfile
2026-11-20 07:25:45.294+0000 [INFO] hudson.lifecycle.Lifecycle#onReady: Jenkins is fully up and running
```

Wait until `curl -fsS http://localhost:8080/login` succeeds (about 15–20 s in
this environment), then log in as `admin`.

> The password is supplied at container start via `JENKINS_ADMIN_PASSWORD`; it
> is never written to the repository. Choose your own value.

### Option B — Native installation (if Docker is unavailable)

```bash
# Debian/Ubuntu example, Java 21 required
sudo apt-get update && sudo apt-get install -y openjdk-21-jre python3 python3-venv python3-pip zip
wget -q https://get.jenkins.io/war-stable/latest/jenkins.war
java -jar jenkins.war --httpPort=8080
```

Then install the plugins listed in `jenkins/plugins.txt` (Manage Jenkins →
Plugins), create the admin user, and create the job manually as described in
[section 15](#15-jenkins-pipeline-job-configuration-pipeline-script-from-scm).

### Prerequisites checklist

- Jenkins reachable on port 8080.
- Plugins: Pipeline (`workflow-aggregator`), Git, JUnit, Pipeline Stage View,
  Timestamper.
- Agent with `git`, `python3`, `python3-venv`, `zip`.
- Outbound HTTPS to GitHub and PyPI.

## 13. Jenkins Pipeline Architecture

| Concept | In this project |
|---|---|
| Controller | `jenkins-lab` container, Jenkins 2.580.2, 2 executors |
| Agent | Built-in node (`Running on Jenkins in /var/jenkins_home/workspace/delivery-metrics-exporter`) |
| Job type | Pipeline |
| Definition | Pipeline script from SCM |
| SCM | Git, `https://github.com/Anique666/delivery-metrics-exporter.git` |
| Branch specifier | `*/main` |
| Script path | `Jenkinsfile` |
| Checkout mode | Lightweight (Jenkinsfile fetched first, then full checkout in the implicit `Checkout SCM` stage) |
| Build parameters | `DEMO_FORCE_TEST_FAILURE` (boolean, default `false`) |
| Artifacts | `deployment-artifact.zip`, `reports/junit-results.xml` |
| Test report | `reports/junit-results.xml` published by the `junit` step |

Because the job uses **Pipeline script from SCM**, the pipeline definition is
versioned with the application: changing the `Jenkinsfile` on `main` and
rebuilding changes the pipeline itself. That is the core CI/CD idea being
demonstrated.

## 14. Explanation of Every Jenkinsfile Stage

The pipeline is declarative (`pipeline { agent any ... }`) with a 20-minute
timeout, timestamped console output, build rotation (30 builds / 10 artifacts)
and `disableConcurrentBuilds()`.

### Global environment

```groovy
environment {
    VENV_DIR      = '.venv'
    DEPLOY_DIR    = 'deployment'
    ARTIFACT_NAME = 'deployment-artifact.zip'
    REPORT_DIR    = 'reports'
    PYTHONDONTWRITEBYTECODE = '1'
    PYTHONUNBUFFERED = '1'
}
```

`PYTHONDONTWRITEBYTECODE=1` keeps `__pycache__` out of the workspace and the
package. Environment variables are available to every `sh` step.

### Stage 1 — Source Checkout

```groovy
stage('Source Checkout') {
    steps {
        sh '''
            set -eu
            echo "Repository URL : $(git config --get remote.origin.url ...)"
            echo "Branch         : ${GIT_BRANCH:-unknown} ..."
            echo "Commit         : $(git rev-parse HEAD)"
            ...
            for file in Jenkinsfile requirements.txt ... README.md; do
                if [ ! -f "$file" ]; then echo "MISSING required file: $file"; exit 1; fi
            done
        '''
    }
}
```

What it does:

- Declarative pipelines automatically check out the SCM configured in the job;
  Jenkins first fetches the `Jenkinsfile` itself (`Obtained Jenkinsfile from git
  https://github.com/...`), then performs the real checkout.
- Prints repository URL, branch (`origin/main`), full and short commit, commit
  message, author, date and workspace path.
- **Removes build outputs from previous runs** (`deployment/`, the ZIP and
  `reports/`). This prevents a failed build from archiving a stale artifact —
  a real defect found in build `#3` and fixed in commit `0a8b849`.
- Verifies that every expected file exists, so a broken checkout fails
  immediately instead of failing mysteriously later.

Why it matters: it proves Jenkins is building the intended repository,
branch and revision, which is requirement 3 of the examination.

### Stage 2 — Dependency Installation / Build

```groovy
stage('Dependency Installation / Build') {
    steps {
        sh '''
            set -eu
            python3 -m venv "$VENV_DIR"
            . "$VENV_DIR/bin/activate"
            python -m pip install --upgrade pip
            python -m pip install -r requirements.txt
            python -m pip install -r requirements-dev.txt
            python -m pip list
            python -m compileall -q exporter tests
        '''
    }
}
```

- Creates an isolated virtual environment in the workspace, so the build never
  pollutes the system Python and is repeatable.
- Installs runtime and test requirements. `pip install` returns non-zero on
  network/version problems; combined with `set -eu` this fails the stage.
- Prints the interpreter version, pip version and the installed package list
  (audit trail for the examiner).
- Byte-compiles `exporter/` and `tests/` as a cheap build/syntax gate.

### Stage 3 — Automated Test / Validation

```groovy
stage('Automated Test / Validation') {
    steps {
        sh '''
            set -eu
            . "$VENV_DIR/bin/activate"
            echo "DEMO_FORCE_TEST_FAILURE=${DEMO_FORCE_TEST_FAILURE:-false}"
            mkdir -p "$REPORT_DIR"
            python -m pytest -v tests --junitxml="$REPORT_DIR/junit-results.xml"
        '''
    }
    post {
        always {
            junit testResults: "${REPORT_DIR}/*.xml", allowEmptyResults: true
        }
    }
}
```

- Runs all 26 tests verbosely, so the console contains the test names.
- Writes a JUnit XML report, which the `junit` step publishes to the Jenkins
  test report and the build page.
- **Failure propagation:** pytest exits with code `1` if any test fails. `sh`
  throws on a non-zero exit code, so the stage fails and Jenkins sets the build
  result to `FAILURE`; subsequent stages are skipped. The `junit` publisher
  runs in the stage's `post { always }` block, so the test report is still
  published for a failed run. It cannot downgrade the build: Jenkins'
  `setResult(UNSTABLE)` only applies when the current result is better than
  `UNSTABLE`, and the build is already `FAILURE`.

### Stage 4 — Deployment Packaging

```groovy
stage('Deployment Packaging') {
    steps {
        sh '''
            set -eu
            rm -rf "$DEPLOY_DIR" "$ARTIFACT_NAME"
            mkdir -p "$DEPLOY_DIR"
            cp -R exporter "$DEPLOY_DIR/"
            cp -R config "$DEPLOY_DIR/"
            cp requirements.txt README.md "$DEPLOY_DIR/"
            # strip __pycache__, *.pyc, tests, .venv, reports
            # write BUILD-INFO.txt with build number, commit, branch, timestamp
            # verify every required file exists
            # smoke-test the packaged app with the system python3
            # re-strip byte-code produced by the smoke test
            zip -qr "$ARTIFACT_NAME" "$DEPLOY_DIR"
            # fail if the ZIP contains caches / venv / tests
        '''
    }
}
```

- Produces the dedicated `deployment/` directory required by the examination.
- Copies **only runtime files**: `exporter/`, `config/`, `requirements.txt`,
  `README.md`, plus a generated `BUILD-INFO.txt` (build number, commit,
  branch, UTC timestamp).
- Explicitly excludes `.git/`, `.venv/`, `tests/`, `reports/`, `__pycache__/`
  and `*.pyc`, then asserts the exclusions worked.
- Runs the packaged application with the **system** `python3` (not the CI
  virtual environment) and validates the generated JSON — proof that the
  package is independently runnable.
- Creates `deployment-artifact.zip`, lists its contents and fails if the
  archive contains caches, a virtual environment or test files.

### Post-build actions

```groovy
post {
    success { echo 'BUILD SUCCESS: all four stages passed...' }
    failure { echo 'BUILD FAILURE: the pipeline stopped at the failing stage...' }
    always {
        echo "Final build status: ${currentBuild.currentResult} (build #${BUILD_NUMBER})"
        archiveArtifacts artifacts: "${ARTIFACT_NAME}, ${REPORT_DIR}/*.xml",
                         allowEmptyArchive: true, fingerprint: true
    }
}
```

- `success` / `failure` print unambiguous messages to the console.
- `always` prints the final status and archives whatever this build produced.
  `allowEmptyArchive: true` keeps a failed build from failing *again* because
  the ZIP was never created, while still publishing the JUnit report.
- Failures are never swallowed: no `catchError`, no `returnStatus`, no
  `|| true` anywhere in the pipeline.

## 15. Jenkins Pipeline Job Configuration (Pipeline script from SCM)

### Actual configuration (verified)

```text
Job name          : delivery-metrics-exporter
Job type          : Pipeline
Definition        : Pipeline script from SCM
SCM               : Git
Repository URL    : https://github.com/Anique666/delivery-metrics-exporter.git
Branch Specifier  : */main
Script Path       : Jenkinsfile
Lightweight checkout: enabled
Parameter         : DEMO_FORCE_TEST_FAILURE (boolean, default false)
```

The persisted job configuration (`evidence/jenkins-job-config.xml`) contains:

```xml
<definition class="org.jenkinsci.plugins.workflow.cps.CpsScmFlowDefinition">
  <scm class="hudson.plugins.git.GitSCM">
    <userRemoteConfigs>
      <hudson.plugins.git.UserRemoteConfig>
        <url>https://github.com/Anique666/delivery-metrics-exporter.git</url>
      </hudson.plugins.git.UserRemoteConfig>
    </userRemoteConfigs>
    <branches>
      <hudson.plugins.git.BranchSpec>
        <name>*/main</name>
      </hudson.plugins.git.BranchSpec>
    </branches>
  </scm>
  <scriptPath>Jenkinsfile</scriptPath>
  <lightweight>true</lightweight>
</definition>
```

### How it was created automatically

`jenkins/init.groovy.d/02-job.groovy` runs at controller start and creates the
job with `CpsScmFlowDefinition` + `GitSCM` + `BooleanParameterDefinition`. This
makes the whole environment reproducible with one `docker run` and avoids
manual UI clicking during the exam.

### Manual UI steps (equivalent)

1. **New Item** → name `delivery-metrics-exporter` → **Pipeline** → OK.
2. **General** → check **This project is parameterized** →
   **Boolean Parameter**:
   - Name: `DEMO_FORCE_TEST_FAILURE`
   - Default: unchecked
   - Description: “Examination demo only: when checked, the automated test
     stage fails on purpose so Jenkins reports a FAILURE build.”
3. **Pipeline** section:
   - Definition: **Pipeline script from SCM**
   - SCM: **Git**
   - Repository URL:
     `https://github.com/Anique666/delivery-metrics-exporter.git`
   - Credentials: **none** (public repository)
   - Branch Specifier: `*/main`
   - Script Path: `Jenkinsfile`
4. **Save** → **Build with Parameters**.

### How to verify SCM integration

- Build console starts with
  `Obtained Jenkinsfile from git https://github.com/Anique666/delivery-metrics-exporter.git`.
- The implicit `Checkout SCM` stage logs
  `Checking out Revision 0a8b8496e479931d09bc9db8c59d79f48060e506 (refs/remotes/origin/main)`.
- Stage 1 prints the same URL and commit from inside the workspace.
- The job page links to the `Jenkinsfile` under “Pipeline” → “Definition”.

Jenkins checks out a specific commit, so `git rev-parse --abbrev-ref HEAD`
reports `HEAD` (detached). The pipeline therefore prints the plugin-provided
`GIT_BRANCH` (`origin/main`) and the remote refs pointing at the commit.

## 16. How to Execute the Pipeline

### From the UI

1. Open <http://localhost:8080/job/delivery-metrics-exporter/>.
2. **Build with Parameters**.
3. Leave `DEMO_FORCE_TEST_FAILURE` unchecked for a normal build (or check it
   for the failure demo).
4. **Build**.
5. Open the build → **Console Output** / **Pipeline Steps** / **Stage View**.

### From the command line (used for the captured evidence)

Jenkins CSRF protection requires a crumb. This exact sequence works:

```bash
JENKINS=http://localhost:8080
JOB=delivery-metrics-exporter
CRUMB=$(curl -s -c /tmp/jenkins-cookies -u admin:"$JENKINS_ADMIN_PASSWORD" \
        "$JENKINS/crumbIssuer/api/json" | python3 -c 'import sys,json; print(json.load(sys.stdin)["crumb"])')

# normal build
curl -s -b /tmp/jenkins-cookies -u admin:"$JENKINS_ADMIN_PASSWORD" \
     -H "Jenkins-Crumb: $CRUMB" \
     -X POST -d "DEMO_FORCE_TEST_FAILURE=false" \
     "$JENKINS/job/$JOB/buildWithParameters"

# controlled-failure build
curl -s -b /tmp/jenkins-cookies -u admin:"$JENKINS_ADMIN_PASSWORD" \
     -H "Jenkins-Crumb: $CRUMB" \
     -X POST -d "DEMO_FORCE_TEST_FAILURE=true" \
     "$JENKINS/job/$JOB/buildWithParameters"
```

Check the result:

```bash
curl -s -u admin:"$JENKINS_ADMIN_PASSWORD" \
     "$JENKINS/job/$JOB/lastBuild/api/json" | python3 -m json.tool | grep -E '"result"|"number"'
```

> `curl -X POST -d "" .../build` returns **400 “Nothing is submitted”** on this
> Jenkins version. Use `buildWithParameters` with an explicit parameter (as
> above) or POST with no body at all.

### From the demo scripts

```bash
python3 /tmp/opencode/jenkins_run.py delivery-metrics-exporter evidence/build-6-console.txt DEMO_FORCE_TEST_FAILURE=false
```

(that helper is a local evidence-capture script, not part of the repository).

## 17. Expected Successful Build Output

### Actual captured console (build `#5`, abridged)

```text
Started by user admin
Obtained Jenkinsfile from git https://github.com/Anique666/delivery-metrics-exporter.git
[Pipeline] node
Running on Jenkins in /var/jenkins_home/workspace/delivery-metrics-exporter
...
[Pipeline] { (Declarative: Checkout SCM)
Checking out Revision 0a8b8496e479931d09bc9db8c59d79f48060e506 (refs/remotes/origin/main)
Commit message: "Remove stale build outputs before each run"
...
Stage 1: Source Checkout
Repository URL : https://github.com/Anique666/delivery-metrics-exporter.git
Commit         : 0a8b8496e479931d09bc9db8c59d79f48060e506
Commit message : Remove stale build outputs before each run
...
Stage 2: Dependency Installation / Build
Python 3.13.5
Successfully installed iniconfig-2.3.1 packaging-26.3 pluggy-1.7.0 pytest-8.3.4
...
Stage 3: Automated Test / Validation
DEMO_FORCE_TEST_FAILURE=false
tests/test_metrics.py::TestControlledFailureDemo::test_controlled_failure_flag_is_respected PASSED [100%]
============================== 26 passed in 0.03s ==============================
...
Stage 4: Deployment Packaging
  OK  deployment/exporter/__init__.py
  OK  deployment/exporter/metrics.py
  OK  deployment/exporter/main.py
  OK  deployment/config/metrics.json
  OK  deployment/requirements.txt
  OK  deployment/README.md
  OK  deployment/BUILD-INFO.txt
Packaged report validated: service=checkout-api metrics=4
Creating ZIP archive: deployment-artifact.zip
-rw-r--r--. 1 jenkins jenkins 7.5K Nov 20 07:42 deployment-artifact.zip
Deployment packaging complete.
Final build status: SUCCESS (build #5)
BUILD SUCCESS: all four stages passed. The exporter was validated and deployment-artifact.zip was produced.
Finished: SUCCESS
```

### Stage table (actual, build `#5`)

| Stage | Status | Duration |
|---|---|---|
| Declarative: Checkout SCM | SUCCESS | 1.6 s |
| Source Checkout | SUCCESS | 0.3 s |
| Dependency Installation / Build | SUCCESS | 1.6 s |
| Automated Test / Validation | SUCCESS | 0.3 s |
| Deployment Packaging | SUCCESS | 0.3 s |
| Declarative: Post Actions | SUCCESS | 0.1 s |

Total build time: **6.0 s** (build `#2`, the first successful run, took 17.6 s
because pip downloaded pytest for the first time).

### Illustrative “expected” summary

For a fresh machine with a warm package cache, expect roughly:

```text
Source Checkout                  SUCCESS
Dependency Installation / Build  SUCCESS   ~10-20 s (first run), ~2 s (cached)
Automated Test / Validation      SUCCESS   26 passed
Deployment Packaging             SUCCESS   deployment/ + deployment-artifact.zip
Finished: SUCCESS
```

## 18. Deployment Packaging

The `deployment/` directory is created from scratch on every successful build:

| Copied | Excluded |
|---|---|
| `exporter/` (all `.py` sources) | `.git/` |
| `config/metrics.json` | `.venv/` |
| `requirements.txt` | `tests/` |
| `README.md` | `reports/`, `output/` of the CI run |
| `BUILD-INFO.txt` (generated) | `__pycache__/`, `*.pyc`, `.pytest_cache/` |

Generated `BUILD-INFO.txt` (actual, build `#5`):

```text
delivery-metrics-exporter deployment package
Build number : 5
Git commit   : 0a8b8496e479931d09bc9db8c59d79f48060e506
Git branch   : origin/main
Built at     : 2026-11-20T07:42:35Z
```

Packaging guarantees enforced by the pipeline:

1. Every required file is present (`test -f` loop).
2. `tests/` and `.venv/` are absent (`test -e` check).
3. No `__pycache__` remains (`find | grep` check).
4. The packaged exporter runs with the **system** Python and produces a valid
   4-metric JSON report.
5. The ZIP contains no caches, virtual environment or test files
   (`unzip -Z1 | grep -Eq ...` check).

The ZIP is created with `zip -qr deployment-artifact.zip deployment` and
archived by `archiveArtifacts`, which also fingerprints it so Jenkins can track
where the artifact was produced and consumed.

## 19. Deployment Artifact Structure

Actual `unzip -l deployment-artifact.zip` from build `#5`:

```text
Archive:  deployment-artifact.zip
  Length      Date    Time    Name
---------  ---------- -----   ----
        0  2026-11-20 07:42   deployment/
        0  2026-11-20 07:42   deployment/exporter/
      574  2026-11-20 07:42   deployment/exporter/__init__.py
     2247  2026-11-20 07:42   deployment/exporter/main.py
     7866  2026-11-20 07:42   deployment/exporter/metrics.py
        0  2026-11-20 07:42   deployment/config/
      206  2026-11-20 07:42   deployment/config/metrics.json
      343  2026-11-20 07:42   deployment/requirements.txt
     1458  2026-11-20 07:42   deployment/README.md
      181  2026-11-20 07:42   deployment/BUILD-INFO.txt
        0  2026-11-20 07:42   deployment/output/
      927  2026-11-20 07:42   deployment/output/metrics-report.json
---------                     -------
    13802                     12 files
```

- Archive size: **7,578 bytes** (`7.5K`).
- 12 entries: 3 source files, 1 config file, 2 documentation/metadata files,
  1 requirements file, 1 report generated by the packaging smoke test,
  and 4 directory entries.
- A copy is committed at [`evidence/deployment-artifact.zip`](evidence/deployment-artifact.zip).

Inside Jenkins the same files live in:

```text
/var/jenkins_home/workspace/delivery-metrics-exporter/deployment/
/var/jenkins_home/workspace/delivery-metrics-exporter/deployment-artifact.zip
```

and the archived copy is downloadable from the build page at
`http://localhost:8080/job/delivery-metrics-exporter/5/artifact/deployment-artifact.zip`.

## 20. How to Run the Deployment Artifact Independently

### Automated check

```bash
./scripts/verify_deployment.sh evidence/deployment-artifact.zip
```

Actual output (run on the host, outside Jenkins):

```text
Unpacking evidence/deployment-artifact.zip into /tmp/tmp.Cm3QY4oofx
Creating a fresh virtual environment inside the unpacked package
Installing runtime requirements
Running the packaged exporter
Service      : checkout-api
Window (days): 30
Metrics      : 4
Report       : /tmp/tmp.Cm3QY4oofx/deployment/output/metrics-report.json
...
SUCCESS: the deployment artifact runs independently.
```

### Manual check (exactly as in the examination brief)

```bash
unzip deployment-artifact.zip -d /tmp/dme
cd /tmp/dme/deployment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m exporter.main
cat output/metrics-report.json
```

Because `requirements.txt` has no third-party runtime packages, `pip install`
succeeds offline once pip itself is available; the application needs nothing
beyond the standard library.

### Inside the Jenkins workspace (actual)

```text
$ docker exec jenkins-lab sh -c 'cd /var/jenkins_home/workspace/delivery-metrics-exporter/deployment && python3 -m exporter.main --output-dir /tmp/standalone-run'
Service      : checkout-api
Window (days): 30
Metrics      : 4
Report       : /tmp/standalone-run/metrics-report.json
```

This run used the agent's system Python 3.13.5, **not** the CI virtual
environment, which proves the package is self-contained.

## 21. Automated Testing Strategy

Framework: **pytest 8.3.4** (the suite is also runnable with
`python -m unittest discover -s tests -v`, because tests are written with
`unittest.TestCase`).

Actual result: **26 passed in 0.03 s** (build `#5`, host Python 3.12.15, agent
Python 3.13.5).

| Test class | Tests | What is covered |
|---|---|---|
| `TestConfiguration` | 4 | shipped config loads; missing file, invalid JSON, missing `metrics` section |
| `TestMetricValidation` | 10 | valid values; unknown metric; negative; >100 %; strings/bools/lists/`None`; NaN; missing key; unknown key; non-mapping |
| `TestReportGeneration` | 5 | exact report structure; values match input; determinism with a fixed timestamp; invalid value blocks the report; invalid `window_days` |
| `TestJsonSerialisation` | 4 | JSON round-trip; pretty-printing; directory creation; non-`.json` filename rejected |
| `TestCommandLine` | 2 | CLI writes a valid report and exits `0`; bad config exits `1` |
| `TestControlledFailureDemo` | 1 | passes normally, fails when `DEMO_FORCE_TEST_FAILURE=true` |
| **Total** | **26** | |

Determinism: `build_report(..., generated_at=FIXED_TIME)` lets tests compare
exact output, and the sample data is fixed, so a green build is meaningful.

Jenkins integration:

- `--junitxml=reports/junit-results.xml` produces the JUnit report.
- `junit testResults: 'reports/*.xml', allowEmptyResults: true` publishes it;
  Jenkins build `#5` records **26 passed, 0 failed, 0 skipped**
  (`evidence/build-5-testreport.json`).
- A failing test yields a non-zero exit code → failing stage → `FAILURE` build.

## 22. Controlled Failure Demonstration

### Mechanism

`tests/test_metrics.py`:

```python
class TestControlledFailureDemo(unittest.TestCase):
    def test_controlled_failure_flag_is_respected(self):
        flag = os.environ.get("DEMO_FORCE_TEST_FAILURE", "").strip().lower()
        if flag in {"1", "true", "yes", "on"}:
            self.fail(
                "CONTROLLED FAILURE: DEMO_FORCE_TEST_FAILURE="
                f"{flag!r} is enabled. This failure is intentional and exists "
                "only to demonstrate Jenkins test-failure detection."
            )
        self.assertIn(flag, {"", "0", "false", "no", "off"})
```

The flag is a Jenkins **build parameter**
(`booleanParam`, default `false`) and is exported to the test stage by
`environment`/`parameters` handling in declarative pipelines. It is
deterministic: no randomness, no sleeps, no network. When the flag is off the
test passes; when it is on, exactly one test fails.

### Run 1 — normal execution (build `#2`)

Triggered with `DEMO_FORCE_TEST_FAILURE=false`:

| Stage | Status | Duration |
|---|---|---|
| Source Checkout | SUCCESS | 0.3 s |
| Dependency Installation / Build | SUCCESS | 10.8 s |
| Automated Test / Validation | SUCCESS | 0.4 s |
| Deployment Packaging | SUCCESS | 0.3 s |

`26 passed in 0.03s`, `Finished: SUCCESS`, artifacts:
`deployment-artifact.zip`, `junit-results.xml`.
Full log: [`evidence/build-2-console.txt`](evidence/build-2-console.txt).

### Run 2 — controlled failure (build `#4`)

Triggered with `DEMO_FORCE_TEST_FAILURE=true`:

```text
DEMO_FORCE_TEST_FAILURE=true
tests/test_metrics.py::TestControlledFailureDemo::test_controlled_failure_flag_is_respected FAILED [100%]
E           AssertionError: CONTROLLED FAILURE: DEMO_FORCE_TEST_FAILURE='true' is enabled. This failure is intentional and exists only to demonstrate Jenkins test-failure detection.
========================= 1 failed, 25 passed in 0.04s =========================
Stage "Deployment Packaging" skipped due to earlier failure(s)
Final build status: FAILURE (build #4)
BUILD FAILURE: the pipeline stopped at the failing stage. Check the stage console output above and the archived JUnit report.
Finished: FAILURE
```

| Stage | Status | Duration |
|---|---|---|
| Source Checkout | SUCCESS | 0.3 s |
| Dependency Installation / Build | SUCCESS | 1.7 s |
| Automated Test / Validation | **FAILED** | 0.3 s |
| Deployment Packaging | not executed (`skipped due to earlier failure(s)`) | — |

Verification of the requirement:

- The failure happened **in the automated test stage**.
- pytest returned **exit code 1** (visible in the `sh` step log), which made the
  stage fail.
- The build result is **`FAILURE`**, not `UNSTABLE` and not `SUCCESS`.
- Deployment packaging did **not** execute, so no new ZIP was produced. Build
  `#4` archives only `junit-results.xml` (see
  `evidence/build-4-stages.json`).
- Jenkins still publishes the failed test in the test report because the
  `junit` step is in the stage's `post { always }` block.

Full log: [`evidence/build-4-console.txt`](evidence/build-4-console.txt).

> Note: Jenkins' stage-view API reports the skipped packaging stage with status
> `FAILED` and a 0.0 s duration. The console line
> `Stage "Deployment Packaging" skipped due to earlier failure(s)` is the
> authoritative statement that it never ran.

### Run 3 — recovery (build `#5`)

Triggered again with `DEMO_FORCE_TEST_FAILURE=false`, same commit
(`0a8b849`): all four stages `SUCCESS`, `26 passed`, new
`deployment-artifact.zip` produced, `Finished: SUCCESS` in 6.0 s.
Full log: [`evidence/build-5-console.txt`](evidence/build-5-console.txt).

### Development history (honest record)

| Build | Result | Reason |
|---|---|---|
| `#1` | FAILURE | `Jenkinsfile` contained `\.` inside a Groovy single-quoted string → `unexpected char: '\'` at compile time. Fixed in commit `82a9a97` (use `[.]` in the regex). Log: `evidence/build-1-console.txt`. |
| `#2` | SUCCESS | First fully green run (normal execution). |
| `#3` | FAILURE | Controlled failure run that exposed a real defect: the previous build's ZIP was still in the workspace and got archived by the `always` post block. Fixed in commit `0a8b849` (clean outputs in Stage 1). |
| `#4` | FAILURE | Clean controlled-failure run (only `junit-results.xml` archived). |
| `#5` | SUCCESS | Recovery run. |

These two defects are documented rather than hidden because they show how the
pipeline itself was validated.

## 23. How to Recover from a Failed Build

1. Open the failed build → **Console Output**, find the failing stage and the
   first error line.
2. For a controlled-failure demo, simply rebuild with
   `DEMO_FORCE_TEST_FAILURE` **unchecked**:

   ```bash
   curl -s -b /tmp/jenkins-cookies -u admin:"$JENKINS_ADMIN_PASSWORD" \
        -H "Jenkins-Crumb: $CRUMB" -X POST \
        -d "DEMO_FORCE_TEST_FAILURE=false" \
        "$JENKINS/job/delivery-metrics-exporter/buildWithParameters"
   ```

3. For a real test regression: fix the code locally, run
   `pytest -v tests`, commit and push to `main`, then rebuild. Because the job
   is *Pipeline script from SCM*, Jenkins picks up the new commit and, if the
   `Jenkinsfile` changed, the new pipeline definition automatically.
4. For environment problems (missing `python3-venv`, no network to PyPI),
   fix the agent and use **Replay** only for experimentation — production
   changes belong in the `Jenkinsfile` in Git.
5. Confirm recovery: the build page shows all four stages green and
   `Finished: SUCCESS`; the artifact list contains `deployment-artifact.zip`
   again.

Recovery was demonstrated: build `#4` FAILURE → build `#5` SUCCESS on the same
commit, with no code change other than the build parameter.

## 24. Expected Console Output and Build Statuses

### Recorded builds (actual)

| Build | Trigger | Result | Duration | Artifacts | Evidence |
|---|---|---|---|---|---|
| `#1` | normal (dev) | FAILURE | 5.4 s | — | `evidence/build-1-console.txt` |
| `#2` | `DEMO_FORCE_TEST_FAILURE=false` | **SUCCESS** | 17.6 s | ZIP + JUnit | `evidence/build-2-console.txt` |
| `#3` | `DEMO_FORCE_TEST_FAILURE=true` | FAILURE | 6.1 s | stale ZIP + JUnit | `evidence/build-3-console.txt` |
| `#4` | `DEMO_FORCE_TEST_FAILURE=true` | **FAILURE** | 7.2 s | JUnit only | `evidence/build-4-console.txt` |
| `#5` | `DEMO_FORCE_TEST_FAILURE=false` | **SUCCESS** | 6.0 s | ZIP + JUnit | `evidence/build-5-console.txt` |

### Status semantics used in this project

| Jenkins result | Meaning here |
|---|---|
| `SUCCESS` | All four stages completed; tests passed; ZIP produced |
| `FAILURE` | A stage returned a non-zero exit code (failing test, pip error, missing file, packaging check) |
| `UNSTABLE` | Never used. The pipeline deliberately does not use `warnings`/`unstable` steps, so a test failure cannot be downgraded |

### What the examiner should look for in the console

- `Obtained Jenkinsfile from git https://github.com/Anique666/delivery-metrics-exporter.git`
- `Checking out Revision <sha> (refs/remotes/origin/main)`
- `Stage 2: Dependency Installation / Build` → `Successfully installed ... pytest-8.3.4`
- `Stage 3: Automated Test / Validation` → `26 passed` or `1 failed, 25 passed`
- `Stage 4: Deployment Packaging` → `OK deployment/...` lines, `Packaged report validated`
- `Final build status: SUCCESS|FAILURE (build #N)` and `Finished: ...`

## 25. Troubleshooting Common Errors

| Symptom | Cause | Fix |
|---|---|---|
| `unexpected char: '\'` at pipeline compile time | Backslash escape inside a Groovy single-quoted string (`\.`) | Use a character class (`[.]`) or `\\.`; see build `#1` |
| `python3: command not found` | Agent image lacks Python | Install `python3 python3-venv python3-pip` on the agent (already in `jenkins/Dockerfile`) |
| `ensurepip is not available` / `venv` fails | `python3-venv` not installed | `apt-get install python3-venv` |
| `junit` step: `No such DSL method 'junit'` | JUnit plugin missing | Install the `junit` plugin (`jenkins/plugins.txt`) |
| `ERROR: No artifacts found` on a failed build | No ZIP produced; archiving strict | `allowEmptyArchive: true` is already set in `post { always }` |
| Failed build archives an old ZIP | Previous workspace not cleaned | Stage 1 removes `deployment/`, the ZIP and `reports/` (fix in `0a8b849`) |
| `400 Nothing is submitted` from `curl` | POST with an empty form body | Use `buildWithParameters` with a parameter, or POST with no body |
| `403 No valid crumb was included` | CSRF protection | Fetch `/crumbIssuer/api/json` and send `Jenkins-Crumb` |
| `401 Unauthorized` on API | Wrong password / anonymous read disabled | Use the admin credentials supplied via `JENKINS_ADMIN_PASSWORD` |
| Checkout fails with 404/403 | Wrong URL, private repo without credentials | Use the public URL; for private repos add a GitHub credential in Jenkins |
| `Branch : HEAD` in Stage 1 | Jenkins checks out a detached commit | Expected; the pipeline also prints `GIT_BRANCH` (`origin/main`) |
| `Selected Git installation does not exist. Using Default` | Cosmetic Git-plugin warning | Harmless |
| Tests pass locally, fail in Jenkins | Different Python version or missing files | Check `python --version` and the file-existence loop in Stage 1 |
| ZIP contains `__pycache__` | Byte-code created by the smoke test | Pipeline re-strips caches before zipping and asserts the archive is clean |
| `Permission denied` writing the workspace | Container user mismatch on a bind mount | Use the named volume `jenkins-lab-home` or fix ownership |
| Jenkins container won't start | Port 8080 in use | `docker ps`, then map another port and set `JENKINS_ROOT_URL` |

## 26. Verification Checklist for All Five Examination Requirements

### Requirement 1 — Python exporter project with source, requirements and tests on GitHub

- [x] `exporter/metrics.py`, `exporter/main.py`, `exporter/__init__.py`
- [x] `config/metrics.json`
- [x] `requirements.txt` (documented stdlib-only policy) + `requirements-dev.txt` (pytest)
- [x] `tests/test_metrics.py` — 26 tests
- [x] Committed and pushed to <https://github.com/Anique666/delivery-metrics-exporter> (`main`)
- [x] Verified with `git ls-remote origin main` and `gh repo view`

### Requirement 2 — Jenkinsfile with the four stages

- [x] `Source Checkout`
- [x] `Dependency Installation / Build`
- [x] `Automated Test / Validation`
- [x] `Deployment Packaging`
- [x] `post { success / failure / always }`

### Requirement 3 — Pipeline job using Pipeline script from SCM

- [x] Job `delivery-metrics-exporter` created with `CpsScmFlowDefinition`
- [x] Git URL and `*/main` verified in `evidence/jenkins-job-config.xml`
- [x] Script path `Jenkinsfile`
- [x] Console proves retrieval: `Obtained Jenkinsfile from git ...` and the
      expected commit is checked out

### Requirement 4 — Execution: dependencies, tests, deployment copy

- [x] Dependencies installed (`Successfully installed ... pytest-8.3.4`, build `#2`)
- [x] Tests pass (`26 passed`, builds `#2` and `#5`)
- [x] `deployment/` created with `exporter/`, `config/`, `requirements.txt`,
      `README.md`, `BUILD-INFO.txt`
- [x] `deployment-artifact.zip` created (7,578 bytes) and archived
- [x] Packaged app executed independently and produced the expected JSON

### Requirement 5 — Stage logs, controlled failure, FAILURE status

- [x] Stage logs captured for builds `#1`–`#5` in `evidence/`
- [x] Controlled failure via `DEMO_FORCE_TEST_FAILURE=true` (build `#4`)
- [x] Test stage FAILED, packaging skipped, final status **FAILURE**
- [x] Recovery via `DEMO_FORCE_TEST_FAILURE=false` (build `#5`, SUCCESS)

## 27. Viva / Demonstration Explanation

Short spoken explanation you can use:

> “This project is a small Python exporter for DORA delivery metrics. It reads
> a JSON configuration, validates four metrics — deployment frequency, lead
> time, change failure rate and MTTR — and writes a JSON report. The whole
> delivery process is a declarative Jenkinsfile stored in GitHub, so the
> pipeline itself is versioned with the code. Jenkins is configured with
> ‘Pipeline script from SCM’, which means it fetches the Jenkinsfile from the
> repository, then checks out branch main. The pipeline has four stages:
> checkout and file verification, virtual-environment creation and dependency
> installation, pytest with a JUnit report, and finally a deployment stage that
> copies only runtime files into deployment/ and zips them. Test failures
> propagate as non-zero exit codes, so Jenkins marks the build FAILURE and skips
> packaging. I demonstrate that with a build parameter that deliberately fails
> one test, and then show the recovery build returning to SUCCESS.”

Key points to emphasise:

- **Pipeline as code** — the Jenkinsfile is in Git, not clicked into the UI.
- **Idempotence** — virtual environment per build, outputs cleaned at the start.
- **Fail fast** — `set -eu`, no swallowed errors, no `|| true`.
- **Evidence** — console logs, JUnit report, stage view, archived ZIP.
- **Simplicity** — stdlib-only application, no extra infrastructure.

## 28. Conclusion

The implementation satisfies all five mandatory examination requirements with
real, reproducible evidence:

- a tested Python metrics exporter in GitHub;
- a declarative `Jenkinsfile` with the four required stages and explicit
  post-build handling;
- a Jenkins job defined by **Pipeline script from SCM** against branch `main`;
- successful builds that install dependencies, pass 26 tests, generate a
  dedicated `deployment/` directory and a runnable `deployment-artifact.zip`;
- a deterministic controlled test failure that Jenkins reports as `FAILURE`,
  followed by a documented recovery to `SUCCESS`.

The pipeline is intentionally minimal so every behaviour can be explained and
demonstrated live, and every claim in this README is backed by a captured log
in [`evidence/`](evidence/).

---

## Laboratory Demonstration – Step-by-Step

Target duration: **5–8 minutes**. Commands assume the Jenkins container is
running and `$JENKINS_ADMIN_PASSWORD` is set.

### Step 1 — Introduce the problem (30 s)

- **Show:** this README’s title and problem statement.
- **Say:** “I built a Python exporter for delivery metrics and automated its
  validation and packaging with a Jenkins declarative pipeline driven from
  GitHub.”

### Step 2 — Show the GitHub repository (30 s)

- **Do:** open <https://github.com/Anique666/delivery-metrics-exporter>.
- **Observe:** branch `main`, the `Jenkinsfile`, `exporter/`, `config/`,
  `tests/`.
- **Say:** “The pipeline definition is versioned with the application, which is
  the core of pipeline-as-code.”

### Step 3 — Explain the project structure (30 s)

- **Show:** the tree in [section 6](#6-project-directory-structure).
- **Say:** “Source, configuration, tests and CI infrastructure are separated.
  `jenkins/` only provisions the controller; the pipeline itself is the
  `Jenkinsfile`.”

### Step 4 — Explain the exporter (60 s)

- **Do:** open `exporter/metrics.py` and `exporter/main.py`.
- **Show:** the metric catalogue, validation, report builder, CLI.
- **Say:** “Validation rejects negative values, percentages above 100, NaN and
  missing metrics; errors return exit code 1, which is what Jenkins uses to
  detect failure.”

### Step 5 — Explain the Jenkinsfile stages (60 s)

- **Do:** open `Jenkinsfile` in GitHub.
- **Show:** the four `stage(...)` blocks and the `post` block.
- **Say:** one sentence per stage: checkout + file checks; venv + pip +
  compile; pytest + JUnit; deployment copy + zip + smoke test.

### Step 6 — Show the Jenkins job configuration (45 s)

- **Do:** open <http://localhost:8080/job/delivery-metrics-exporter/configure>.
- **Observe:** Definition = *Pipeline script from SCM*, SCM = Git, URL, branch
  `*/main`, Script Path `Jenkinsfile`, parameter `DEMO_FORCE_TEST_FAILURE`.
- **Say:** “Jenkins fetches the Jenkinsfile from this repository and branch; no
  pipeline code lives only in the UI.”

### Step 7 — Run a successful pipeline (60 s)

- **Do:** **Build with Parameters** → leave the flag unchecked → **Build** →
  open **Console Output**.
- **Observe:** `Obtained Jenkinsfile from git ...`, `26 passed`,
  `Packaged report validated`, `Finished: SUCCESS`.
- **Say:** “All four stages are green: dependencies installed, tests passed,
  package produced.”

### Step 8 — Show the deployment directory and ZIP (45 s)

- **Do:** on the build page open **Workspace** →
  `deployment/` and `deployment-artifact.zip`; or run:

  ```bash
  docker exec jenkins-lab sh -c 'cd /var/jenkins_home/workspace/delivery-metrics-exporter && find deployment -type f | sort && unzip -l deployment-artifact.zip'
  ```

- **Observe:** only runtime files; no `tests/`, `.venv/` or `__pycache__`.
- **Say:** “The artifact contains exactly what is needed to run the exporter.”

### Step 9 — Run the artifact independently (45 s)

- **Do:**

  ```bash
  ./scripts/verify_deployment.sh evidence/deployment-artifact.zip
  ```

- **Observe:** a fresh venv, `pip install -r requirements.txt`, and the JSON
  report printed from the unpacked package.
- **Say:** “The package runs outside Jenkins with no access to the CI
  workspace.”

### Step 10 — Trigger the controlled failure (60 s)

- **Do:** **Build with Parameters** → check `DEMO_FORCE_TEST_FAILURE` →
  **Build** → open the console.
- **Observe:** `1 failed, 25 passed`,
  `Stage "Deployment Packaging" skipped due to earlier failure(s)`,
  `Final build status: FAILURE`, `Finished: FAILURE`.
- **Say:** “The flag makes one deterministic test fail; pytest exits non-zero;
  Jenkins stops the pipeline and marks the build FAILURE — not unstable.”

### Step 11 — Show the failed stage and status (30 s)

- **Do:** open **Stage View** and the build summary.
- **Observe:** test stage red, packaging not executed, build marked with the red
  ball; the JUnit report still lists the failing test.
- **Say:** “Failure detection comes from the process exit code, and the test
  report is still published for diagnosis.”

### Step 12 — Demonstrate recovery (45 s)

- **Do:** **Build with Parameters** → uncheck the flag → **Build**.
- **Observe:** all stages green again, `26 passed`, new ZIP archived,
  `Finished: SUCCESS`.
- **Say:** “No code change was needed — the failure was an intentional switch,
  and the next normal build recovers.”

### Backup material

- Captured logs: `evidence/build-2-console.txt` (success),
  `evidence/build-4-console.txt` (failure), `evidence/build-5-console.txt`
  (recovery).
- Job configuration: `evidence/jenkins-job-config.xml`.
- JUnit report: `evidence/junit-results.xml`.
- Artifact: `evidence/deployment-artifact.zip`.

---

## Likely Viva Questions and Answers

**1. What is Jenkins?**
An open-source automation server written in Java. It orchestrates build, test
and deployment jobs, either as freestyle projects or as pipelines defined in
code, and reports results, logs and artifacts.

**2. What is CI/CD?**
Continuous Integration: every change is automatically built and tested.
Continuous Delivery/Deployment: validated changes are automatically packaged
and released. This project implements CI (checkout, dependencies, tests) and the
delivery-packaging step (artifact creation), leaving the actual release to a
deployment tool.

**3. What is a Jenkinsfile?**
A text file in the repository that defines the pipeline — stages, steps,
environment, parameters and post-build actions — so the pipeline is versioned
and reviewed like application code.

**4. Declarative vs. scripted pipeline?**
Declarative uses a fixed structure (`pipeline`, `agent`, `stages`, `steps`,
`post`) and is easier to read and validate. Scripted is general Groovy with
fewer guardrails. This project uses declarative.

**5. What are stages and steps?**
A stage is a logical phase shown in the stage view (e.g. “Automated Test /
Validation”). Steps are the individual commands inside a stage (`sh`, `junit`,
`archiveArtifacts`).

**6. What does “Pipeline script from SCM” mean?**
Jenkins does not store the pipeline in its own configuration. It fetches the
`Jenkinsfile` from a source-control repository at build time, so the pipeline
definition is always the version in Git.

**7. How does Jenkins know which repository and branch to use?**
From the job configuration: SCM = Git, repository URL, branch specifier
`*/main`, script path `Jenkinsfile`. The console logs
`Obtained Jenkinsfile from git <url>` and the checked-out revision.

**8. What is a build agent/node?**
The machine or process that executes the pipeline. Here the built-in node runs
on the controller (`Running on Jenkins in /var/jenkins_home/workspace/...`).
Agents can be added for scale or different environments.

**9. How is dependency management handled?**
`requirements.txt` declares runtime dependencies (none, stdlib only);
`requirements-dev.txt` adds pinned pytest. Stage 2 creates an isolated
`.venv`, installs both files, and byte-compiles the code. A pip failure is a
non-zero exit code and fails the build.

**10. Why use a virtual environment in CI?**
Isolation and reproducibility: the build does not modify system packages, and
the same dependency set can be recreated on any agent. It also prevents
“works on my machine” drift.

**11. How does Jenkins detect a failing test?**
The test process returns a non-zero exit code. `sh` throws on a non-zero exit
code, the stage is marked FAILED, and the build result becomes `FAILURE`.
Additionally, pytest writes JUnit XML that Jenkins parses for the test report.

**12. Why is the build FAILURE and not UNSTABLE?**
`UNSTABLE` is typically set by publishers such as JUnit when tests fail in a
build that otherwise succeeded. Here the failing shell step already sets
`FAILURE`, which is worse than `UNSTABLE`, so the result cannot be downgraded.
The pipeline also never uses `catchError` or `warnError`.

**13. What are post-build actions?**
The `post` block runs after stages: `success`, `failure`, `always`,
`unstable`, `changed`, `aborted`. This project prints status messages and
archives the ZIP and JUnit XML in `always`, so evidence is kept even for failed
builds.

**14. What is an artifact in Jenkins?**
A file produced by a build that Jenkins stores and exposes for download, with
optional fingerprinting. Here: `deployment-artifact.zip` and
`reports/junit-results.xml`.

**15. What is deployment packaging?**
Producing a self-contained, runnable bundle from validated sources: copying
only runtime files into `deployment/`, generating build metadata, smoke-testing
it, and archiving a ZIP that can be moved to another machine.

**16. Why exclude tests and virtual environments from the package?**
They are development/CI concerns; shipping them bloats the artifact, leaks test
code, and can break on the target because virtual environments are not portable
across paths and platforms.

**17. How is the artifact verified as runnable?**
Stage 4 runs `python3 -m exporter.main` inside `deployment/` with the system
interpreter and asserts the JSON contains 4 metrics for `checkout-api`.
`scripts/verify_deployment.sh` repeats this from the ZIP in a temporary
directory with a brand-new virtual environment.

**18. What happens if the Jenkinsfile itself is broken?**
The build fails before any stage runs, with a Groovy compilation error — this
happened in build `#1` (`unexpected char: '\'`). Because the Jenkinsfile is in
Git, the fix is a normal commit and push.

**19. How do you make the pipeline reproducible?**
Pinned pytest version, virtual environment per build, deterministic sample data,
fixed timestamps in tests, cleaning of previous outputs, and a Docker image that
pins Jenkins plus the required plugins and Python toolchain.

**20. Why not use Docker inside the pipeline?**
It adds nothing for this task. The requirement is Jenkins + Python + GitHub +
tests + packaging; a Docker agent would add complexity, permissions and startup
time without improving the demonstration.

**21. How would you extend this to real deployment?**
Add a `Deploy` stage after packaging that uploads the ZIP to an artifact
repository or copies it to a target host, gate it with a manual `input` step
and/or a `when { branch 'main' }` condition, and keep the same failure
semantics.

**22. What is the difference between `archiveArtifacts` and `stash`?**
`archiveArtifacts` stores files permanently with the build for humans and
downstream jobs; `stash` is temporary storage for passing files between stages
or nodes within the same build. This pipeline needs the former.

**23. Why is `allowEmptyArchive: true` used?**
So a failed build that never produced a ZIP does not fail again during
archiving, while still publishing the JUnit report. It does not hide the test
failure — the build result is already `FAILURE`.

**24. How do you know Jenkins built the right commit?**
The console shows `Obtained Jenkinsfile from git <url>` and
`Checking out Revision <sha> (refs/remotes/origin/main)`; Stage 1 prints the
same URL, commit and commit message from inside the workspace, and
`BUILD-INFO.txt` in the artifact records the commit and build number.

---

## Appendix — Reproducing the evidence

```bash
# 1. start Jenkins (Docker)
export JENKINS_ADMIN_PASSWORD='choose-a-strong-password'
./jenkins/run-jenkins.sh

# 2. normal build
CRUMB=$(curl -s -c /tmp/cj -u admin:"$JENKINS_ADMIN_PASSWORD" \
        http://localhost:8080/crumbIssuer/api/json \
        | python3 -c 'import sys,json;print(json.load(sys.stdin)["crumb"])')
curl -s -b /tmp/cj -u admin:"$JENKINS_ADMIN_PASSWORD" -H "Jenkins-Crumb: $CRUMB" \
     -X POST -d "DEMO_FORCE_TEST_FAILURE=false" \
     http://localhost:8080/job/delivery-metrics-exporter/buildWithParameters

# 3. controlled failure build
curl -s -b /tmp/cj -u admin:"$JENKINS_ADMIN_PASSWORD" -H "Jenkins-Crumb: $CRUMB" \
     -X POST -d "DEMO_FORCE_TEST_FAILURE=true" \
     http://localhost:8080/job/delivery-metrics-exporter/buildWithParameters

# 4. recovery build
curl -s -b /tmp/cj -u admin:"$JENKINS_ADMIN_PASSWORD" -H "Jenkins-Crumb: $CRUMB" \
     -X POST -d "DEMO_FORCE_TEST_FAILURE=false" \
     http://localhost:8080/job/delivery-metrics-exporter/buildWithParameters

# 5. inspect the latest result
curl -s -u admin:"$JENKINS_ADMIN_PASSWORD" \
     http://localhost:8080/job/delivery-metrics-exporter/lastBuild/api/json \
     | python3 -c 'import sys,json;d=json.load(sys.stdin);print(d["number"], d["result"])'
```
