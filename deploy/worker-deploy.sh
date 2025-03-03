#!/bin/bash
set -e

# Check if required environment variables are set
if [ -z "$REGISTRY" ] || [ -z "$IMAGE_NAME" ] || [ -z "$TAG" ] || [ -z "$CONTAINER_PREFIX" ] || [ -z "$SPACES_ACCESS_KEY" ] || [ -z "$SPACES_SECRET_KEY" ] || [ -z "$SPACES_ENDPOINT" ]; then
    echo "Error: Missing required environment variables"
    exit 1
fi

# Create secrets directory if it doesn't exist
mkdir -p /opt/secrets

# Download .env file from DigitalOcean Spaces
docker run --rm \
    -e AWS_ACCESS_KEY_ID="$SPACES_ACCESS_KEY" \
    -e AWS_SECRET_ACCESS_KEY="$SPACES_SECRET_KEY" \
    -v /opt/secrets:/mnt \
    amazon/aws-cli:latest \
    --endpoint-url "$SPACES_ENDPOINT" \
    s3 cp s3://mc-bench-worker/.env /mnt/.env

chmod 644 /opt/secrets/.env

# Login to registry
docker login -u "$DOCKER_LOGIN_USERNAME" -p "$DIGITALOCEAN_ACCESS_TOKEN" registry.digitalocean.com

# Get timestamp for unique container name
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
NEW_CONTAINER_NAME="${CONTAINER_PREFIX}_${TIMESTAMP}"
HOSTNAME=$(hostname)

# Stop existing containers
for container in $(docker ps -f name="$CONTAINER_PREFIX" -q); do
    docker kill --signal=SIGTERM "$container"
done

# Start new container with named worker
docker run -d --name "$NEW_CONTAINER_NAME" \
    --pull always \
    --rm \
    --env-file /opt/secrets/.env \
    -e CONTAINER_NAME="$NEW_CONTAINER_NAME" \
    "$REGISTRY/$IMAGE_NAME:$TAG" \
    celery -A mc_bench.apps.worker worker -Q default --concurrency $NUM_WORKERS -n "${NEW_CONTAINER_NAME}@${HOSTNAME}"

# Create run script for manual execution
cat > /opt/run-${CONTAINER_PREFIX}.sh << EOF
#!/bin/bash
# Manual worker runner script - generated at $(date)
# Run this script to manually start a worker container

# Pull latest image
docker pull "$REGISTRY/$IMAGE_NAME:$TAG"

# Generate a container name
MANUAL_CONTAINER_NAME="${CONTAINER_PREFIX}_manual_\$(date +%Y%m%d_%H%M%S)"
HOSTNAME=\$(hostname)

# Run the container
docker run -d --name "\$MANUAL_CONTAINER_NAME" \\
    --rm \\
    --env-file /opt/secrets/.env \\
    -e CONTAINER_NAME="\$MANUAL_CONTAINER_NAME" \\
    "$REGISTRY/$IMAGE_NAME:$TAG" \\
    celery -A mc_bench.apps.worker worker -Q default --concurrency \$NUM_WORKERS -n "\${MANUAL_CONTAINER_NAME}@\${HOSTNAME}"

echo "Started worker container: \$MANUAL_CONTAINER_NAME"
echo "To view logs: docker logs -f \$MANUAL_CONTAINER_NAME"
echo "To stop: docker kill \$MANUAL_CONTAINER_NAME"
EOF

chmod +x /opt/run-${CONTAINER_PREFIX}.sh
echo "Created manual runner script at /opt/run-${CONTAINER_PREFIX}.sh"

# Setup cleanup
chmod +x /opt/docker-cleanup.sh
if ! crontab -l | grep -q "docker-cleanup"; then
    (crontab -l 2>/dev/null; echo "0 */6 * * * /opt/docker-cleanup.sh >> /var/log/docker-cleanup.log 2>&1") | crontab -
fi 