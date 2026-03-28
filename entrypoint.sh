#!/bin/sh
set -e

chown -R app_user:app_user /app/json /app/logs
exec su-exec app_user "$@"
