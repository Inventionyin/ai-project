#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/opt/weitesting/backups/jenkins}"
JENKINS_HOME="${JENKINS_HOME:-/var/jenkins_home}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
STAMP="$(date -u +%Y%m%d-%H%M%S)"

mkdir -p "$BACKUP_DIR"
tar --exclude='workspace' --exclude='caches' --exclude='war' -czf "$BACKUP_DIR/jenkins-$STAMP.tgz" -C "$JENKINS_HOME" .
find "$BACKUP_DIR" -name 'jenkins-*.tgz' -mtime +"$RETENTION_DAYS" -delete
echo "Jenkins backup written: $BACKUP_DIR/jenkins-$STAMP.tgz"
