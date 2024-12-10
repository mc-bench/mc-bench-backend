#!/bin/bash
set -e

# Check if required environment variables are set
if [ -z "$REGISTRY" ] || [ -z "$IMAGE_NAME" ] || [ -z "$GITHUB_SHA" ] || [ -z "$CONTAINER_PREFIX" ]; then
    echo "Error: REGISTRY, IMAGE_NAME, GITHUB_SHA, and CONTAINER_PREFIX must be set"
    exit 1
fi

# Login to registry
docker login -u "$DOCKER_LOGIN_USERNAME" -p "$DIGITALOCEAN_ACCESS_TOKEN" registry.digitalocean.com

# Pull the new image
docker pull "$REGISTRY/$IMAGE_NAME:${GITHUB_SHA:0:7}"

# Get timestamp for unique container name
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
NEW_CONTAINER_NAME="${CONTAINER_PREFIX}_${TIMESTAMP}"

# Send stop signal to existing workers
for container in $(docker ps -f name="$CONTAINER_PREFIX" -q); do
    docker kill --signal=SIGTERM "$container"
done

sed -i "s/minecraft-server:[[:alnum:]]\{7\}/minecraft-server:${GITHUB_SHA:0:7}/" /opt/secrets/.env
sed -i "s/minecraft-builder:[[:alnum:]]\{7\}/minecraft-builder:${GITHUB_SHA:0:7}/" /opt/secrets/.env


# Start the new container
docker run -d --name "$NEW_CONTAINER_NAME" \
    --restart unless-stopped \
    --env-file /opt/secrets/.env \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v /root/.docker/config.json:/root/.docker/config.json \
    "$REGISTRY/$IMAGE_NAME:${GITHUB_SHA:0:7}"
