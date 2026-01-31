#!/bin/sh
set -e

# 1. Send PING to Redis with authentication
response=$(REDISCLI_AUTH="$(cat /run/secrets/redis_password)" redis-cli ping)

# 2. Check Result
if [ "$response" = "PONG" ]; then
    exit 0
fi

echo "Healthcheck failed: Expected 'PONG' but got '$response'"
exit 1
