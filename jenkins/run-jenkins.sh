#!/usr/bin/env bash
# Start the Jenkins controller used by this lab.
#
#   export JENKINS_ADMIN_PASSWORD='choose-a-strong-password'
#   ./jenkins/run-jenkins.sh
#
# The container keeps its state in the named volume "jenkins-lab-home".
# Delete the volume (docker volume rm jenkins-lab-home) for a clean rebuild.
set -euo pipefail

: "${JENKINS_ADMIN_PASSWORD:?Set JENKINS_ADMIN_PASSWORD before starting Jenkins}"

IMAGE="${JENKINS_IMAGE:-jenkins-lab:lts}"
CONTAINER="${JENKINS_CONTAINER:-jenkins-lab}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

docker build -t "$IMAGE" "$SCRIPT_DIR"

if docker container inspect "$CONTAINER" >/dev/null 2>&1; then
    echo "Removing existing container $CONTAINER"
    docker rm -f "$CONTAINER" >/dev/null
fi

docker run -d --name "$CONTAINER" \
    -p 8080:8080 \
    -p 50000:50000 \
    -v jenkins-lab-home:/var/jenkins_home \
    -e JENKINS_ADMIN_ID="${JENKINS_ADMIN_ID:-admin}" \
    -e JENKINS_ADMIN_PASSWORD="$JENKINS_ADMIN_PASSWORD" \
    -e JENKINS_ROOT_URL="${JENKINS_ROOT_URL:-http://localhost:8080/}" \
    -e GITHUB_REPO_URL="${GITHUB_REPO_URL:-https://github.com/Anique666/delivery-metrics-exporter.git}" \
    -e GITHUB_BRANCH="${GITHUB_BRANCH:-*/main}" \
    -e JENKINS_JOB_NAME="${JENKINS_JOB_NAME:-delivery-metrics-exporter}" \
    "$IMAGE"

echo "Jenkins is starting: http://localhost:8080  (user: ${JENKINS_ADMIN_ID:-admin})"
echo "Wait for 'Jenkins is fully up and running' in: docker logs -f $CONTAINER"
