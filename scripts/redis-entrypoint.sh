#!/bin/sh
set -e

# 1. Define paths
SECRET_FILE="/run/secrets/redis_password"

# 1. Validate Secret
if [ ! -f "$SECRET_FILE" ]; then
    echo "Error: Redis password secret not found at $SECRET_FILE"
    exit 1
fi

# 2. Read the password from the secret file
PASSWORD=$(cat "$SECRET_FILE")

# 3. Start Redis with the specified configuration
echo "Starting Redis..."

exec redis-server - <<EOF
requirepass $PASSWORD
port ${REDIS_PORT:-6379}
EOF
