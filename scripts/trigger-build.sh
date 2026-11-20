#!/usr/bin/env bash
# Trigger a build of the pipeline job with the correct CSRF crumb handling.
#
#   JENKINS_ADMIN_PASSWORD='...' ./scripts/trigger-build.sh false   # normal build
#   JENKINS_ADMIN_PASSWORD='...' ./scripts/trigger-build.sh true    # controlled failure
#
# The crumb is fetched and used with the SAME cookie jar, which is what Jenkins
# requires: a crumb is bound to the web session that requested it.
set -euo pipefail

: "${JENKINS_ADMIN_PASSWORD:?set JENKINS_ADMIN_PASSWORD first}"

JENKINS_URL="${JENKINS_URL:-http://localhost:8080}"
JOB="${JENKINS_JOB:-delivery-metrics-exporter}"
ADMIN_USER="${JENKINS_ADMIN_ID:-admin}"
FORCE_FAILURE="${1:-false}"

case "$FORCE_FAILURE" in
    true|false|1|0|yes|no|on|off) ;;
    *) echo "usage: $0 [true|false]" >&2; exit 2 ;;
esac

COOKIES="$(mktemp)"
trap 'rm -f "$COOKIES"' EXIT

CRUMB="$(curl -fsS -c "$COOKIES" -u "$ADMIN_USER:$JENKINS_ADMIN_PASSWORD" \
        "$JENKINS_URL/crumbIssuer/api/json" \
        | python3 -c 'import sys, json; print(json.load(sys.stdin)["crumb"])')"

HTTP_CODE="$(curl -sS -b "$COOKIES" -u "$ADMIN_USER:$JENKINS_ADMIN_PASSWORD" \
    -H "Jenkins-Crumb: $CRUMB" \
    -X POST -d "DEMO_FORCE_TEST_FAILURE=$FORCE_FAILURE" \
    -o /dev/null -w '%{http_code}' \
    "$JENKINS_URL/job/$JOB/buildWithParameters")"

if [ "$HTTP_CODE" != "201" ]; then
    echo "ERROR: Jenkins rejected the trigger (HTTP $HTTP_CODE)." >&2
    echo "Check the URL, the job name and the admin credentials." >&2
    exit 1
fi

echo "Triggered $JOB with DEMO_FORCE_TEST_FAILURE=$FORCE_FAILURE (HTTP $HTTP_CODE)"
echo "Build page: $JENKINS_URL/job/$JOB/"
