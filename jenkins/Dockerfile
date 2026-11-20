# Jenkins controller image for the delivery-metrics-exporter lab.
#
# The official Jenkins image ships without Python, so this image adds the
# Python toolchain required by the pipeline (python3, venv, pip) plus zip
# for artifact creation. Plugins are baked in so the job works on first boot.
FROM jenkins/jenkins:lts-jdk21

USER root

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        python3 \
        python3-venv \
        python3-pip \
        zip \
        unzip \
        curl \
    && rm -rf /var/lib/apt/lists/*

USER jenkins

COPY plugins.txt /usr/share/jenkins/ref/plugins.txt
RUN jenkins-plugin-cli --plugin-file /usr/share/jenkins/ref/plugins.txt

# Configuration-as-code: security realm, executor count and the pipeline job
# are created on first boot by these init scripts.
COPY init.groovy.d/ /usr/share/jenkins/ref/init.groovy.d/
