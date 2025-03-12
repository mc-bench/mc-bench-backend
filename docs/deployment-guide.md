# MC-Bench Deployment Guide

This guide provides instructions for deploying the MC-Bench backend in production environments.

## Deployment Architecture

MC-Bench uses a microservices architecture with the following components:

- **APIs**:
  - `api`: Main application API (port 8000)
  - `admin-api`: Administrative API (port 8001)

- **Workers** (Celery-based):
  - `worker`: General purpose worker
  - `admin-worker`: Handles administrative tasks and LLM integrations
  - `render-worker`: Handles rendering tasks (specifically for amd64 platform)
  - `server-worker`: Manages Minecraft server instances

- **Infrastructure Services**:
  - `postgres`: PostgreSQL database (v16)
  - `redis`: Redis for Celery message broker (v7)
  - `object`: MinIO object storage
  - `admin-flower`: Celery monitoring UI

## Prerequisites

- Docker and Docker Compose
- Access to container registry
- PostgreSQL 16+
- Redis 7+
- S3-compatible object storage (MinIO in development, can use AWS S3 in production)
- LLM API keys for supported providers

## Configuration

### Environment Variables

#### Common Variables (All Components)

```
CELERY_BROKER_URL=redis://redis:6379/0
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_USER=user
POSTGRES_PASSWORD=password
POSTGRES_DB=mc_bench
REDIS_HOST=redis
REDIS_PORT=6379
LOG_LEVEL=INFO
WORKER_NAME=containername@hostname
HUMANIZE_LOGS=true
SHOW_VERBOSE_SQL=false
```

#### API-specific Variables

```
SECRET_KEY=your-secret-key
CORS_ALLOWED_ORIGIN=https://frontend.example.com
GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_MINUTES=1440
AUTO_GRANT_ADMIN_ROLE=false
```

#### Object Storage Variables

```
INTERNAL_OBJECT_BUCKET=mc-bench-internal
EXTERNAL_OBJECT_BUCKET=mc-bench-public
OBJECT_STORE_DSN=object:9000
OBJECT_STORE_ACCESS_KEY=minioadmin
OBJECT_STORE_SECRET_KEY=minioadmin
OBJECT_STORE_SECURE=false
```

#### Worker-specific Variables

Admin Worker:
```
ANTHROPIC_API_KEY=your-anthropic-key
OPENAI_API_KEY=your-openai-key
GEMINI_API_KEY=your-gemini-key
MISTRAL_API_KEY=your-mistral-key
```

Render Worker:
```
FAST_RENDER=false
LOG_INTERVAL_BLOCKS=1000
LOG_INTERVAL_MATERIALS=1000
```

Server Worker:
```
MINECRAFT_SERVER_IMAGE=mc-bench-minecraft-server:latest
MINECRAFT_BUILDER_IMAGE=mc-bench-builder-runner:latest
NUM_WORKERS=2
BUILD_DELAY_MS=500
```

### Docker Compose Configuration

For development and testing, use the provided `docker-compose.yml`:

```bash
docker-compose up -d
```

For production, it's recommended to deploy each component separately for better scalability.

## Deployment Steps

### 1. Prepare Environment

Set up environment variables in a `.env` file or configure them in your deployment platform.

### 2. Build and Push Images

```bash
# Build all images
make build-local-images

# Tag images
docker tag mc-bench-api:latest registry.example.com/mc-bench-api:latest
docker tag mc-bench-admin-api:latest registry.example.com/mc-bench-admin-api:latest
docker tag mc-bench-worker:latest registry.example.com/mc-bench-worker:latest
docker tag mc-bench-admin-worker:latest registry.example.com/mc-bench-admin-worker:latest
docker tag mc-bench-render-worker:latest registry.example.com/mc-bench-render-worker:latest
docker tag mc-bench-server-worker:latest registry.example.com/mc-bench-server-worker:latest

# Push images
docker push registry.example.com/mc-bench-api:latest
docker push registry.example.com/mc-bench-admin-api:latest
docker push registry.example.com/mc-bench-worker:latest
docker push registry.example.com/mc-bench-admin-worker:latest
docker push registry.example.com/mc-bench-render-worker:latest
docker push registry.example.com/mc-bench-server-worker:latest
```

### 3. Deploy Infrastructure Services

Deploy PostgreSQL, Redis, and object storage using your preferred method (managed services or self-hosted).

### 4. Deploy Core Components

Use the provided deployment scripts:

```bash
# Deploy API components
./deploy/api-deploy.sh

# Deploy worker components
./deploy/worker-deploy.sh
./deploy/admin-worker-deploy.sh
./deploy/render-worker-deploy.sh
./deploy/server-worker-deploy.sh
```

## Resource Requirements

### Minimum Requirements

- **APIs**: 1 CPU, 2GB RAM
- **Workers**: 2 CPU, 4GB RAM
- **Render Worker**: 2 CPU, 4GB RAM (must be amd64)
- **Server Worker**: 4 CPU, 8GB RAM (requires Docker socket access)
- **PostgreSQL**: 2 CPU, 4GB RAM, 20GB storage
- **Redis**: 1 CPU, 2GB RAM
- **Object Storage**: 2 CPU, 4GB RAM, 100GB+ storage

### Scaling Considerations

- **API Scaling**: APIs are stateless and can be horizontally scaled
- **Worker Scaling**: Each worker type can be independently scaled
  - Add more worker instances by running deployment scripts
  - Workers identify themselves with unique names (for task routing)
- **Database Scaling**: Consider managed PostgreSQL with replication for high availability
- **Redis Scaling**: Use Redis Cluster for high-volume workloads
- **Storage Scaling**: Use a scalable object storage solution like AWS S3 for production workloads

## Networking

- **Internal Network**: All services communicate over internal Docker network
- **External Access**:
  - API: Expose port 8000
  - Admin API: Expose port 8001 (restrict to admin users)
  - Flower UI: Expose port 5555 (restrict to admin users)

- **Security Considerations**:
  - Use HTTPS for all external traffic
  - Restrict admin interfaces to trusted networks
  - Configure CORS correctly for frontend integration

## Special Deployment Notes

### Server Worker

The server worker requires special attention:

- Requires Docker socket access (`/var/run/docker.sock`)
- Spawns additional containers for Minecraft servers
- Needs to run on a host with sufficient resources for multiple Minecraft servers
- Requires network connectivity between spawned containers

Example configuration:

```yaml
version: '3'
services:
  server-worker:
    image: registry.example.com/mc-bench-server-worker:latest
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    environment:
      - MINECRAFT_SERVER_IMAGE=mc-bench-minecraft-server:latest
      - MINECRAFT_BUILDER_IMAGE=mc-bench-builder-runner:latest
      - NUM_WORKERS=2
    restart: unless-stopped
```

### Render Worker

The render worker is platform-specific:

- Must run on linux/amd64 platform
- CPU-intensive for rendering operations
- Can be scaled horizontally for parallel rendering jobs

## Monitoring and Maintenance

### Celery Flower

Flower provides a web dashboard for monitoring Celery tasks:

- Access on port 5555
- Shows real-time task execution status
- Provides task history and error information

### Logging

Configure logging appropriately:

- Set `LOG_LEVEL` to adjust verbosity (INFO for production, DEBUG for troubleshooting)
- Use `HUMANIZE_LOGS=true` for human-readable logs or `false` for structured JSON logs
- Configure log aggregation service (e.g., ELK stack) for centralized logging

### Cleanup

Regular cleanup is required to manage Docker resources:

- Run the cleanup script periodically:
  ```bash
  ./deploy/docker-cleanup.sh
  ```
- Consider scheduling this as a cron job:
  ```
  0 */6 * * * /path/to/deploy/docker-cleanup.sh
  ```

## Database Migrations

Apply database migrations during deployment:

```bash
# Run migrations inside the API container
docker exec -it mc-bench-api alembic upgrade head

# Or run directly if you have access to the database
PYTHONPATH=/app python -m mc_bench.migrations upgrade head
```

## Backup Strategy

Implement a backup strategy for:

- PostgreSQL database
- Object storage data
- Configuration files and environment variables

Example PostgreSQL backup:

```bash
pg_dump -h postgres -U user -d mc_bench > backup_$(date +%Y%m%d).sql
```

## Troubleshooting

### Common Issues

1. **Database Connection Issues**
   - Check PostgreSQL connection parameters
   - Verify network connectivity
   - Check database user permissions

2. **Worker Not Processing Tasks**
   - Verify Celery broker URL (Redis connection)
   - Check worker logs for errors
   - Ensure task queue exists and contains tasks

3. **Minecraft Server Issues**
   - Check Docker socket permissions
   - Verify server worker can create containers
   - Check network connectivity between containers

4. **Rendering Failures**
   - Verify render worker is running on amd64 platform
   - Check object storage connectivity
   - Verify schematic files are accessible

### Viewing Logs

```bash
# View API logs
docker logs mc-bench-api

# View worker logs
docker logs mc-bench-worker
docker logs mc-bench-admin-worker
docker logs mc-bench-render-worker
docker logs mc-bench-server-worker

# Follow logs in real-time
docker logs -f mc-bench-api
```

## Upgrading

To upgrade the deployment:

1. Build and push new images
2. Run database migrations if schema changes are present
3. Deploy updated components using deployment scripts
4. Verify functionality

For zero-downtime upgrades, deploy new instances before removing old ones.

## Security Considerations

- Store API keys and secrets securely
- Restrict access to admin interfaces
- Use HTTPS for all external traffic
- Implement proper authentication and authorization
- Regularly update dependencies and base images
- Monitor for suspicious activity
- Configure resource limits to prevent DoS attacks