#!/bin/bash
set -e

# Check if required environment variables are set
if [ -z "$REGISTRY" ] || [ -z "$IMAGE_NAME" ] || [ -z "$TAG" ] || [ -z "$CONTAINER_PREFIX" ]; then
    echo "Error: REGISTRY, IMAGE_NAME, TAG, and CONTAINER_PREFIX must be set"
    exit 1
fi

# Login to registry
docker login -u "$DOCKER_LOGIN_USERNAME" -p "$DIGITALOCEAN_ACCESS_TOKEN" registry.digitalocean.com

# Get timestamp for unique container name
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
NEW_CONTAINER_NAME="${CONTAINER_PREFIX}_${TIMESTAMP}"

# Send stop signal to existing workers
for container in $(docker ps -f name="$CONTAINER_PREFIX" -q); do
    docker kill --signal=SIGTERM "$container"
done

# Update environment file with new tag
sed -i "s/minecraft-server:[[:alnum:]_-]\+/minecraft-server:$TAG/" /opt/secrets/.env
sed -i "s/minecraft-builder:[[:alnum:]_-]\+/minecraft-builder:$TAG/" /opt/secrets/.env

# Start the new container
docker run -d --name "$NEW_CONTAINER_NAME" \
    --pull always \
    --restart unless-stopped \
    --env-file /opt/secrets/.env \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v /root/.docker/config.json:/root/.docker/config.json \
    "$REGISTRY/$IMAGE_NAME:$TAG"
