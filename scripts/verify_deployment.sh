#!/usr/bin/env bash
# Verify that deployment-artifact.zip is independently runnable.
#
#   ./scripts/verify_deployment.sh [path/to/deployment-artifact.zip]
#
# The ZIP is unpacked into a temporary directory, a fresh virtual environment
# is created inside the unpacked package, dependencies from requirements.txt
# are installed, and the exporter is executed. This proves the artifact does
# not depend on the Jenkins workspace or its CI virtual environment.
set -euo pipefail

ARTIFACT="${1:-deployment-artifact.zip}"

if [ ! -f "$ARTIFACT" ]; then
    echo "ERROR: artifact not found: $ARTIFACT" >&2
    exit 1
fi

WORKDIR="$(mktemp -d)"
trap 'rm -rf "$WORKDIR"' EXIT

echo "Unpacking $ARTIFACT into $WORKDIR"
unzip -q "$ARTIFACT" -d "$WORKDIR"

if [ ! -d "$WORKDIR/deployment" ]; then
    echo "ERROR: archive does not contain a deployment/ directory" >&2
    exit 1
fi

cd "$WORKDIR/deployment"

echo "Creating a fresh virtual environment inside the unpacked package"
python3 -m venv .venv
# shellcheck disable=SC1091
. .venv/bin/activate

echo "Installing runtime requirements"
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt

echo "Running the packaged exporter"
python -m exporter.main --output-dir output

echo "Generated report:"
cat output/metrics-report.json

echo
echo "SUCCESS: the deployment artifact runs independently."
