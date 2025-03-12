# MC-Bench Developer Guide

This guide provides detailed information for developers working on the MC-Bench backend.

## Development Environment Setup

### Prerequisites

- Python 3.10+ (3.12.7 recommended, render worker uses 3.11.7)
- Docker and Docker Compose
- PostgreSQL
- Redis

### Installation

1. Clone the repository
2. Install development dependencies:
   ```bash
   pip install -e ".[dev]"
   # or
   make install-dev
   ```

### Common Commands

- Format code: `make fmt` (uses ruff formatter and import sorter)
- Lint code: `make check` (ruff checker)
- Auto-fix linting: `make check-fix`
- Run tests: `pytest tests/test_file.py::test_function`
- Build Docker images: `make build-local-images`
- Reset environment: `make reset`
- Run with changes: `make build-run`

## System Architecture

For an overview of the system architecture, see [Architecture Documentation](architecture.md).

## Database Schema

### Core Tables

The database schema is divided into several schemas:

1. **Auth Schema**
   - `auth_provider`: OAuth providers (GitHub, Google)
   - `user`: User accounts and profile information
   - `role`: Role definitions for permissions
   - `permission`: Available permissions in the system
   - `role_permission`: Many-to-many relationship between roles and permissions
   - `user_role`: Assigns roles to users

2. **Specification Schema**
   - `model`: AI model definitions
   - `provider`: AI providers (OpenAI, Anthropic, etc.)
   - `provider_class`: Provider types and implementations
   - `prompt`: Prompts used for generation
   - `template`: Minecraft templates
   - `run`: Execution runs
   - `run_stage`: Stages within a run
   - `run_state`: State tracking for runs
   - `tag`: Tags for organization and filtering

3. **Sample Schema**
   - `sample`: Generated samples
   - `artifact`: Files and data associated with samples
   - `artifact_kind`: Types of artifacts (code, image, schematic)
   - `test_set`: Sets of samples for evaluation

4. **Scoring Schema**
   - `comparison`: User comparisons between samples
   - `comparison_rank`: Rankings within comparisons
   - `processed_comparison`: Comparisons that have affected ratings
   - `model_leaderboard`: ELO ratings for models
   - `prompt_leaderboard`: ELO ratings for prompts
   - `sample_leaderboard`: ELO ratings for samples

### Migrations

Database migrations are managed with Alembic:

- Add a new migration: `alembic revision -m "description"`
- Apply migrations: `alembic upgrade head`
- Check current version: `alembic current`

## API Endpoints

### Admin API

- **Authentication**
  - `POST /auth/token`: Obtain JWT token
  - `GET /auth/me`: Get current user information

- **Models**
  - `GET /models`: List models
  - `POST /models`: Create model
  - `GET /models/{id}`: Get model details
  - `PUT /models/{id}`: Update model
  - `DELETE /models/{id}`: Delete model

- **Prompts**
  - `GET /prompts`: List prompts
  - `POST /prompts`: Create prompt
  - `GET /prompts/{id}`: Get prompt details
  - `PUT /prompts/{id}`: Update prompt
  - `DELETE /prompts/{id}`: Delete prompt

- **Templates**
  - `GET /templates`: List templates
  - `POST /templates`: Create template
  - `GET /templates/{id}`: Get template details
  - `PUT /templates/{id}`: Update template
  - `DELETE /templates/{id}`: Delete template

- **Runs**
  - `GET /runs`: List runs
  - `POST /runs`: Create run
  - `GET /runs/{id}`: Get run details
  - `PUT /runs/{id}`: Update run
  - `DELETE /runs/{id}`: Delete run
  - `POST /runs/{id}/retry`: Retry failed run

- **Samples**
  - `GET /samples`: List samples
  - `GET /samples/{id}`: Get sample details
  - `PUT /samples/{id}`: Update sample
  - `DELETE /samples/{id}`: Delete sample

### Public API

- **User**
  - `POST /user/login`: Login user
  - `GET /user/me`: Get current user information

- **Comparison**
  - `GET /comparison`: Get comparison for voting
  - `POST /comparison/{id}/vote`: Submit vote for comparison

## Authentication

### JWT Authentication

The system uses JWT tokens for authentication:

```python
from mc_bench.server.auth import create_access_token

# Create token
token = create_access_token(data={"sub": user.id})

# Verify token
from mc_bench.server.auth import verify_token
user_id = verify_token(token)
```

### OAuth Providers

The system supports OAuth2 with GitHub and Google:

1. Redirect user to provider's authorization URL
2. Receive callback with code
3. Exchange code for access token
4. Retrieve user information using access token
5. Create or update local user account
6. Issue JWT token for session

## Worker System

### Celery Tasks

Tasks are defined in worker applications:

```python
from mc_bench.util.celery import create_task

@create_task(queue="admin")
def example_task(param1, param2):
    # Task implementation
    return result
```

### Run Stages

Each run goes through multiple stages:

1. PromptExecution
2. ResponseParsing
3. CodeValidation
4. Building
5. RenderingSample
6. PreparingSample

Each stage has states like PENDING, IN_PROGRESS, COMPLETED, FAILED.

### Task Implementation

```python
from mc_bench.worker.run_stage import StageContext

async def run_stage_task(context: StageContext):
    # Access run and stage information
    run = context.run
    stage = context.stage
    
    # Update stage state
    await context.set_in_progress()
    
    try:
        # Implement stage logic
        result = await process_stage(run, stage)
        
        # Mark as completed
        await context.set_completed(result=result)
    except Exception as e:
        # Handle failure
        await context.set_failed(error=str(e))
```

## AI Provider Integration

### Adding a New Provider

1. Create provider class in `models/provider/`
2. Implement `execute_prompt` method
3. Add provider to database via migrations

Example implementation:

```python
from mc_bench.models.provider._base import Provider

class NewProvider(Provider):
    async def execute_prompt(self, prompt, model_name, **kwargs):
        # Configure API client
        client = setup_client(self.config)
        
        # Execute prompt
        response = await client.generate(
            prompt=prompt,
            model=model_name,
            **kwargs
        )
        
        # Process and return response
        return {
            "text": response.text,
            "raw": response.raw
        }
```

## Minecraft Integration

### Server Worker

The server worker manages Minecraft server instances:

1. Launch Docker container with Minecraft server
2. Execute build script in separate container
3. Export schematic file (.nbt)
4. Clean up containers

### Building Process

JavaScript code is executed in a Node.js environment:

```javascript
// Example build script
const { World } = require('minecraft-scripting-api');

function build(world) {
    // Create structure
    for (let x = 0; x < 10; x++) {
        for (let z = 0; z < 10; z++) {
            world.setBlock(x, 0, z, 'minecraft:stone');
        }
    }
}

module.exports = { build };
```

### Rendering

The render worker converts schematics to 3D models:

1. Load schematic file
2. Convert to 3D model
3. Generate preview images
4. Store in object storage

## ELO Rating System

The ELO rating system tracks performance of models, prompts, and samples:

```python
from mc_bench.util.elo import calculate_elo_update

# Calculate new ratings after a comparison
new_rating_winner, new_rating_loser = calculate_elo_update(
    rating_winner=1500,
    rating_loser=1500,
    k_factor=32
)
```

## Configuration System

Configuration is managed through environment variables:

```python
from pydantic import BaseSettings

class AppSettings(BaseSettings):
    jwt_secret: str
    redis_url: str
    database_url: str
    
    class Config:
        env_file = ".env"
        env_prefix = "MC_BENCH_"
```

## Logging

The system uses structured logging:

```python
from mc_bench.util.logging import get_logger

logger = get_logger(__name__)

logger.info("Operation completed", extra={
    "run_id": run.id,
    "stage": stage.name,
    "result": result
})
```

## Testing

### Unit Tests

Write unit tests with pytest:

```python
import pytest
from mc_bench.util.elo import calculate_elo_update

@pytest.mark.parametrize("rating_a,rating_b,expected_a,expected_b", [
    (1500, 1500, 1516, 1484),
    (1600, 1400, 1608, 1392),
])
def test_elo_calculation(rating_a, rating_b, expected_a, expected_b):
    new_a, new_b = calculate_elo_update(rating_a, rating_b, k_factor=32)
    assert new_a == expected_a
    assert new_b == expected_b
```

### Integration Tests

For integration tests, use Docker Compose to set up dependencies:

```bash
# Start test environment
docker-compose -f docker-compose.test.yml up -d

# Run tests
pytest tests/integration/

# Cleanup
docker-compose -f docker-compose.test.yml down
```

## Common Issues and Solutions

### Database Connection Issues

- Check PostgreSQL connection string
- Ensure database exists and user has permissions
- Verify network connectivity to database server

### Worker Not Processing Tasks

- Check Celery broker (Redis) connection
- Verify worker is running correctly
- Inspect worker logs for errors
- Ensure task is registered with correct queue

### Docker Image Builds Failing

- Clean Docker cache: `docker system prune`
- Check disk space
- Verify build dependencies are available

### Authentication Problems

- Check JWT secret key configuration
- Verify OAuth provider settings
- Ensure proper CORS configuration

## Troubleshooting

### Viewing Logs

```bash
# View API logs
docker-compose logs -f api

# View worker logs
docker-compose logs -f worker

# View all logs
docker-compose logs -f
```

### Debugging Database

```bash
# Connect to database
psql postgres://user:password@localhost:5432/mc_bench

# List tables
\dt

# Describe table
\d table_name
```

### Checking Task Queue

```bash
# Inspect Redis queue
redis-cli

# List queues
KEYS *

# View pending tasks
LRANGE celery:queue:admin 0 -1
```