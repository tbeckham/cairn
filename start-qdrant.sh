#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PODMAN="${PODMAN_BIN:-$(command -v podman)}"
CONTAINER=qdrant
IMAGE=docker.io/qdrant/qdrant:latest
STORAGE="${CAIRN_QDRANT_STORAGE:-${SCRIPT_DIR}-qdrant-storage}"

if [ -z "$PODMAN" ]; then
    echo "Podman was not found in PATH. Set PODMAN_BIN to its location." >&2
    exit 1
fi

"$PODMAN" machine start >/dev/null 2>&1 || true

counter=0
until "$PODMAN" info >/dev/null 2>&1 || [ "$counter" -ge 30 ]; do
    sleep 2
    counter=$((counter + 2))
done

if ! "$PODMAN" info >/dev/null 2>&1; then
    echo "Timed out waiting for Podman machine." >&2
    exit 1
fi

mkdir -p "$STORAGE"

if "$PODMAN" container exists "$CONTAINER"; then
    if [ "$("$PODMAN" inspect --format '{{.State.Running}}' "$CONTAINER")" = "true" ]; then
        echo "$CONTAINER is already running"
    else
        "$PODMAN" start "$CONTAINER"
    fi
else
    "$PODMAN" run -d \
        --name "$CONTAINER" \
        --restart=unless-stopped \
        -p 6333:6333 \
        -p 6334:6334 \
        -v "$STORAGE:/qdrant/storage:Z" \
        "$IMAGE"
fi
