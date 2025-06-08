#!/bin/bash
# GPU Yield Calculator Backup Script

set -e

BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

echo "🗄️ Creating backup in $BACKUP_DIR"

# Backup Redis data (if local)
if command -v redis-cli >/dev/null 2>&1; then
    echo "Backing up Redis data..."
    redis-cli --rdb "$BACKUP_DIR/redis_backup.rdb"
fi

# Backup configuration files
echo "Backing up configuration..."
cp .env "$BACKUP_DIR/" 2>/dev/null || echo "No .env file found"
cp render.yaml "$BACKUP_DIR/" 2>/dev/null || echo "No render.yaml found"

# Create backup info
cat > "$BACKUP_DIR/backup_info.txt" << EOL
Backup created: $(date)
Environment: ${ENVIRONMENT:-unknown}
Git commit: $(git rev-parse HEAD 2>/dev/null || echo "unknown")
Git branch: $(git branch --show-current 2>/dev/null || echo "unknown")
EOL

echo "✅ Backup completed: $BACKUP_DIR"
