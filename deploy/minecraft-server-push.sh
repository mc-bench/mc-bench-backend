#!/bin/bash
set -e

# Check if GITHUB_SHA is set
if [ -z "$GITHUB_SHA" ]; then
    echo "Error: GITHUB_SHA environment variable is not set"
    exit 1
fi

# Check if required environment variables are set
if [ -z "$REGISTRY" ] || [ -z "$IMAGE_NAME" ]; then
    echo "Error: REGISTRY and IMAGE_NAME must be set"
    exit 1
fi

# Build the image
cd images/minecraft-server

python build-and-save-image.py --tag "${GITHUB_SHA:0:7}"

# Push to registry
docker push "$REGISTRY/$IMAGE_NAME:${GITHUB_SHA:0:7}"
