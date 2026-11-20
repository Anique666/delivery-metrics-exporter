/*
 * Jenkinsfile - Delivery Metrics Exporter
 * ---------------------------------------
 * Declarative pipeline with the four mandatory stages:
 *   1. Source Checkout
 *   2. Dependency Installation / Build
 *   3. Automated Test / Validation
 *   4. Deployment Packaging
 *
 * The controlled-failure switch is the build parameter DEMO_FORCE_TEST_FAILURE.
 * It is exported to the test stage as an environment variable; when true the
 * test suite fails on purpose so Jenkins marks the build FAILURE.
 */
pipeline {
    agent any

    options {
        timestamps()
        timeout(time: 20, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '30', artifactNumToKeepStr: '10'))
        disableConcurrentBuilds()
    }

    parameters {
        booleanParam(
            name: 'DEMO_FORCE_TEST_FAILURE',
            defaultValue: false,
            description: 'Examination demo only: when checked, the automated test stage fails on purpose so Jenkins reports a FAILURE build. Leave unchecked for normal builds.'
        )
    }

    environment {
        VENV_DIR      = '.venv'
        DEPLOY_DIR    = 'deployment'
        ARTIFACT_NAME = 'deployment-artifact.zip'
        REPORT_DIR    = 'reports'
        PYTHONDONTWRITEBYTECODE = '1'
        PYTHONUNBUFFERED = '1'
    }

    stages {

        /* ------------------------------------------------------------------
         * Stage 1 - Source Checkout
         * The Declarative pipeline checks out the SCM configured in the job
         * (Pipeline script from SCM -> Git -> repository URL + branch).
         * This stage proves which revision Jenkins is building and that the
         * expected project files really came from the repository.
         * ------------------------------------------------------------------ */
        stage('Source Checkout') {
            steps {
                sh '''
                    set -eu
                    echo "=========================================================="
                    echo "Stage 1: Source Checkout"
                    echo "=========================================================="
                    echo "Repository URL : $(git config --get remote.origin.url || echo 'not set')"
                    echo "Branch         : ${GIT_BRANCH:-unknown} (working tree state: $(git rev-parse --abbrev-ref HEAD))"
                    echo "Remote refs    : $(git for-each-ref --format='%(refname:short)' --points-at HEAD refs/remotes/origin | tr '\n' ' ')"
                    echo "Commit         : $(git rev-parse HEAD)"
                    echo "Short commit   : $(git rev-parse --short HEAD)"
                    echo "Commit message : $(git log -1 --pretty=%s)"
                    echo "Commit author  : $(git log -1 --pretty='%an <%ae>')"
                    echo "Commit date    : $(git log -1 --pretty=%ci)"
                    echo "Workspace      : $(pwd)"
                    echo "----------------------------------------------------------"
                    echo "Removing build outputs from previous runs (stale-artifact protection)"
                    rm -rf "$DEPLOY_DIR" "$ARTIFACT_NAME" "$REPORT_DIR"
                    echo "----------------------------------------------------------"
                    echo "Verifying expected project files:"
                    for file in Jenkinsfile requirements.txt requirements-dev.txt exporter/__init__.py exporter/metrics.py exporter/main.py config/metrics.json tests/test_metrics.py README.md; do
                        if [ ! -f "$file" ]; then
                            echo "MISSING required file: $file"
                            exit 1
                        fi
                        echo "  OK  $file"
                    done
                    echo "All expected project files are present."
                '''
            }
        }

        /* ------------------------------------------------------------------
         * Stage 2 - Dependency Installation / Build
         * Creates an isolated virtual environment, installs the declared
         * dependencies and byte-compiles the sources. Any pip/compile error
         * returns a non-zero exit code, which fails the stage and the build.
         * ------------------------------------------------------------------ */
        stage('Dependency Installation / Build') {
            steps {
                sh '''
                    set -eu
                    echo "=========================================================="
                    echo "Stage 2: Dependency Installation / Build"
                    echo "=========================================================="
                    echo "Recreating the virtual environment from scratch"
                    rm -rf "$VENV_DIR"
                    python3 -m venv "$VENV_DIR"
                    # shellcheck disable=SC1091
                    . "$VENV_DIR/bin/activate"
                    echo "Python executable : $(command -v python)"
                    python --version
                    python -m pip install --upgrade pip
                    echo "----------------------------------------------------------"
                    echo "Installing runtime dependencies (requirements.txt):"
                    python -m pip install -r requirements.txt
                    echo "----------------------------------------------------------"
                    echo "Installing test/CI dependencies (requirements-dev.txt):"
                    python -m pip install -r requirements-dev.txt
                    echo "----------------------------------------------------------"
                    echo "Installed packages:"
                    python -m pip list
                    echo "----------------------------------------------------------"
                    echo "Build check: byte-compiling the package"
                    python -m compileall -q exporter tests
                    echo "Byte-compilation succeeded."
                '''
            }
        }

        /* ------------------------------------------------------------------
         * Stage 3 - Automated Test / Validation
         * Runs the pytest suite. pytest exits non-zero when any test fails,
         * so `sh` throws, the stage is marked FAILURE and Jenkins aborts the
         * remaining stages. JUnit XML is published in the stage post block.
         * ------------------------------------------------------------------ */
        stage('Automated Test / Validation') {
            steps {
                sh '''
                    set -eu
                    echo "=========================================================="
                    echo "Stage 3: Automated Test / Validation"
                    echo "=========================================================="
                    # shellcheck disable=SC1091
                    . "$VENV_DIR/bin/activate"
                    echo "DEMO_FORCE_TEST_FAILURE=${DEMO_FORCE_TEST_FAILURE:-false}"
                    mkdir -p "$REPORT_DIR"
                    python -m pytest -v tests --junitxml="$REPORT_DIR/junit-results.xml"
                    echo "----------------------------------------------------------"
                    echo "Test suite finished with exit code 0 (all tests passed)."
                '''
            }
            post {
                always {
                    junit testResults: "${REPORT_DIR}/*.xml", allowEmptyResults: true
                }
            }
        }

        /* ------------------------------------------------------------------
         * Stage 4 - Deployment Packaging
         * Builds a self-contained deployment/ directory (runtime files only)
         * and zips it into deployment-artifact.zip. The packaged app is
         * smoke-tested with the system interpreter to prove it runs without
         * the CI virtual environment or any test files.
         * ------------------------------------------------------------------ */
        stage('Deployment Packaging') {
            steps {
                sh '''
                    set -eu
                    echo "=========================================================="
                    echo "Stage 4: Deployment Packaging"
                    echo "=========================================================="
                    rm -rf "$DEPLOY_DIR" "$ARTIFACT_NAME"
                    mkdir -p "$DEPLOY_DIR"

                    echo "Copying runtime files into $DEPLOY_DIR/"
                    cp -R exporter "$DEPLOY_DIR/"
                    cp -R config "$DEPLOY_DIR/"
                    cp requirements.txt README.md "$DEPLOY_DIR/"

                    echo "Removing caches, byte-code and test-only files from the package"
                    find "$DEPLOY_DIR" -name '__pycache__' -type d -prune -exec rm -rf {} +
                    find "$DEPLOY_DIR" -name '*.pyc' -delete
                    rm -rf "$DEPLOY_DIR/tests" "$DEPLOY_DIR/.venv" "$DEPLOY_DIR/reports"

                    if [ -e "$DEPLOY_DIR/tests" ] || [ -e "$DEPLOY_DIR/.venv" ]; then
                        echo "ERROR: test files or virtual environments leaked into the package"
                        exit 1
                    fi
                    if find "$DEPLOY_DIR" -name '__pycache__' | grep -q .; then
                        echo "ERROR: __pycache__ leaked into the package"
                        exit 1
                    fi

                    {
                        echo "delivery-metrics-exporter deployment package"
                        echo "Build number : ${BUILD_NUMBER}"
                        echo "Git commit   : ${GIT_COMMIT}"
                        echo "Git branch   : ${GIT_BRANCH}"
                        echo "Built at     : $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
                    } > "$DEPLOY_DIR/BUILD-INFO.txt"

                    echo "Verifying required deployment files:"
                    for file in exporter/__init__.py exporter/metrics.py exporter/main.py config/metrics.json requirements.txt README.md BUILD-INFO.txt; do
                        if [ ! -f "$DEPLOY_DIR/$file" ]; then
                            echo "MISSING in deployment package: $file"
                            exit 1
                        fi
                        echo "  OK  $DEPLOY_DIR/$file"
                    done

                    echo "----------------------------------------------------------"
                    echo "Smoke test: running the packaged exporter with the system python3"
                    ( cd "$DEPLOY_DIR" && PYTHONDONTWRITEBYTECODE=1 python3 -m exporter.main --output-dir output )
                    test -f "$DEPLOY_DIR/output/metrics-report.json"
                    python3 -c 'import json, pathlib; r = json.loads(pathlib.Path("deployment/output/metrics-report.json").read_text()); assert r["metric_count"] == 4, r; assert r["service"] == "checkout-api", r; print("Packaged report validated: service=%s metrics=%s" % (r["service"], r["metric_count"]))'

                    echo "----------------------------------------------------------"
                    echo "Removing any byte-code generated by the smoke test"
                    find "$DEPLOY_DIR" -name '__pycache__' -type d -prune -exec rm -rf {} +
                    find "$DEPLOY_DIR" -name '*.pyc' -delete

                    echo "Creating ZIP archive: $ARTIFACT_NAME"
                    zip -qr "$ARTIFACT_NAME" "$DEPLOY_DIR"
                    unzip -l "$ARTIFACT_NAME"
                    if unzip -Z1 "$ARTIFACT_NAME" | grep -Eq '(__pycache__|[.]venv/|/tests/|[.]pytest_cache)'; then
                        echo "ERROR: the ZIP archive contains build/test artefacts that must not be shipped"
                        exit 1
                    fi
                    ls -lh "$ARTIFACT_NAME"
                    echo "Deployment packaging complete."
                '''
            }
        }
    }

    post {
        success {
            echo 'BUILD SUCCESS: all four stages passed. The exporter was validated and deployment-artifact.zip was produced.'
        }
        failure {
            echo 'BUILD FAILURE: the pipeline stopped at the failing stage. Check the stage console output above and the archived JUnit report.'
        }
        always {
            echo "Final build status: ${currentBuild.currentResult} (build #${BUILD_NUMBER})"
            archiveArtifacts artifacts: "${ARTIFACT_NAME}, ${REPORT_DIR}/*.xml", allowEmptyArchive: true, fingerprint: true
        }
    }
}
