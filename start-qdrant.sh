#!/bin/bash

# Trigger Podman machine startup if not already running
/opt/homebrew/bin/podman machine start 2>/dev/null || true

# Poll for socket readiness (timeout after 30 seconds)
counter=0
until /opt/homebrew/bin/podman system connection list >/dev/null 2>&1 || [ $counter -ge 30 ]; do
    sleep 2
    counter=$((counter + 2))
done

if [ $counter -ge 30 ]; then
    echo "Timed out waiting for Podman machine socket." >&2
    exit 1
fi

# Start Qdrant container
/opt/homebrew/bin/podman start qdrant
