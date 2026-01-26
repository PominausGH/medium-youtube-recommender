#!/bin/bash
# backup.sh - Database backup script for AI Content Curator
# Usage: ./scripts/backup.sh [backup_dir]
#
# Recommended cron entry (daily at 2 AM):
# 0 2 * * * /app/scripts/backup.sh /backups >> /var/log/backup.log 2>&1

set -euo pipefail

# Configuration
BACKUP_DIR="${1:-/app/backups}"
DB_PATH="${DB_PATH:-/app/data/curator.db}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
DATE=$(date +%Y-%m-%d_%H-%M-%S)
BACKUP_NAME="curator_backup_${DATE}.db"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Create backup directory if it doesn't exist
mkdir -p "${BACKUP_DIR}"

# Check if database exists
if [ ! -f "${DB_PATH}" ]; then
    log "ERROR: Database not found at ${DB_PATH}"
    exit 1
fi

log "Starting backup of ${DB_PATH}"

# Create backup using SQLite's backup command (safer than cp for active DBs)
sqlite3 "${DB_PATH}" ".backup '${BACKUP_DIR}/${BACKUP_NAME}'"

# Verify backup was created
if [ -f "${BACKUP_DIR}/${BACKUP_NAME}" ]; then
    BACKUP_SIZE=$(du -h "${BACKUP_DIR}/${BACKUP_NAME}" | cut -f1)
    log "Backup created: ${BACKUP_NAME} (${BACKUP_SIZE})"
    
    # Compress the backup
    gzip "${BACKUP_DIR}/${BACKUP_NAME}"
    log "Backup compressed: ${BACKUP_NAME}.gz"
else
    log "ERROR: Backup failed - file not created"
    exit 1
fi

# Remove old backups (older than RETENTION_DAYS)
log "Cleaning up backups older than ${RETENTION_DAYS} days"
find "${BACKUP_DIR}" -name "curator_backup_*.db.gz" -type f -mtime +${RETENTION_DAYS} -delete

# List current backups
BACKUP_COUNT=$(find "${BACKUP_DIR}" -name "curator_backup_*.db.gz" -type f | wc -l)
log "Current backup count: ${BACKUP_COUNT}"

log "Backup completed successfully"
