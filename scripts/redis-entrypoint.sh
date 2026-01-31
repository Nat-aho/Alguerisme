#!/bin/sh
set -e

# 1. Define paths
SECRET_FILE="/run/secrets/redis_password"
CONFIG_FILE="/tmp/redis.conf"

# 2. Check if secret exists
if [ ! -f "$SECRET_FILE" ]; then
    echo "Error: Redis password secret not found at $SECRET_FILE"
    exit 1
fi

# 3. Read password
PASSWORD=$(cat "$SECRET_FILE")

# 4. Generate secure config file
# We echo the config directive into a temp file.
# This ensures the password is inside the file, not in the process command line.
echo "requirepass $PASSWORD" > "$CONFIG_FILE"

# 5. Execute Redis
# 'exec' replaces the shell process with redis-server (PID 1).
# This is crucial for Docker to handle signals (like SIGTERM) correctly.
echo "Starting Redis with secure configuration..."
exec redis-server "$CONFIG_FILE"
