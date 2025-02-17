#!/bin/bash
set -e

# Check if required environment variables are set
if [ -z "$REGISTRY" ] || [ -z "$IMAGE_NAME" ] || [ -z "$TAG" ] || [ -z "$CONTAINER_PREFIX" ] || [ -z "$SPACES_ACCESS_KEY" ] || [ -z "$SPACES_SECRET_KEY" ] || [ -z "$SPACES_ENDPOINT" ]; then
    echo "Error: Missing required environment variables"
    exit 1
fi

# Create secrets directory if it doesn't exist
mkdir -p /opt/secrets

# Download .env file from DigitalOcean Spaces using official AWS CLI image
docker run --rm \
    -e AWS_ACCESS_KEY_ID="$SPACES_ACCESS_KEY" \
    -e AWS_SECRET_ACCESS_KEY="$SPACES_SECRET_KEY" \
    -v /opt/secrets:/mnt \
    amazon/aws-cli:latest \
    --endpoint-url "$SPACES_ENDPOINT" \
    s3 cp s3://mc-bench-secrets-dev/server-worker/.env /mnt/.env

# Set correct permissions for .env file
chmod 644 /opt/secrets/.env

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
sed -i "s/minecraft-builder:[[:alnum:]_-]\+/minecraft-builder:$TAG/" /opt/secrets/.env

# Start the new container
docker run -d --name "$NEW_CONTAINER_NAME" \
    --pull always \
    --restart unless-stopped \
    --env-file /opt/secrets/.env \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v /root/.docker/config.json:/root/.docker/config.json \
    "$REGISTRY/$IMAGE_NAME:$TAG"
