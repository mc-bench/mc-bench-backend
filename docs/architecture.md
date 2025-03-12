# MC-Bench Backend Architecture

## System Overview

MC-Bench is a platform for generating, rendering, and comparing Minecraft builds created by different AI models. The system consists of multiple components working together:

- **Admin API**: REST API for researchers and administrators
- **Public API**: REST API for end users to participate in comparisons
- **Worker System**: Distributed task processing for generation, building, and rendering
- **Database**: Stores models, prompts, templates, runs, and user data
- **Object Storage**: Stores artifacts like images, 3D models, and schematics

## Core Components

### Applications

1. **Admin API** (`apps/admin_api/`)
   - Authentication and authorization
   - Management of models, prompts, templates
   - Run creation and monitoring
   - User management and permissions
   - Research and experimental state tracking

2. **Public API** (`apps/api/`)
   - User authentication
   - Comparison interface for end users
   - Voting and feedback collection

3. **Worker System**
   - **Admin Worker**: Handles AI model interactions and generation tasks
   - **Server Worker**: Manages Minecraft server operations and building
   - **Render Worker**: Renders 3D visualizations of Minecraft builds
   - **General Worker**: Handles utility tasks like ELO calculations

### Database Models

The system uses a PostgreSQL database with a comprehensive schema:

- **Auth**: User accounts, roles, permissions
- **Specification**: Models, prompts, templates, providers, tags
- **Sample**: Artifacts, test sets, sample metadata
- **Scoring**: Comparisons, rankings, metrics, leaderboards
- **Research**: Experimental states, logs, notes

### AI Provider Integration

The system supports multiple AI providers through a clean abstraction layer:

- OpenAI (GPT models)
- Anthropic (Claude models)
- Google (Gemini models)
- Mistral
- DeepSeek
- Grok
- ZhipuAI
- Alibaba Cloud
- OpenRouter
- Reka

## Data Flow

### Run Processing Pipeline

Each run goes through multiple stages:

1. **Prompt Execution**: Send prompt to AI model and collect response
2. **Response Parsing**: Extract code, description, and inspiration
3. **Code Validation**: Validate JavaScript code for security and correctness
4. **Building**: Execute code in Minecraft environment to create structure
5. **Rendering**: Generate 3D model of the completed structure
6. **Sample Preparation**: Prepare artifacts for comparison

### State Management

Each run stage has detailed state tracking:

- PENDING: Waiting to be processed
- IN_PROGRESS: Currently being processed
- COMPLETED: Successfully completed
- FAILED: Failed to complete
- RETRY_PENDING: Waiting to be retried
- IN_RETRY: Currently being retried

## Infrastructure

### Docker-Based Execution

The system uses Docker containers for isolation and reproducibility:

- Each Minecraft build runs in a dedicated container
- Containers are networked to allow communication
- Resources are automatically cleaned up after completion

### Celery Task System

Distributed task processing is handled by Celery:

- Tasks are distributed to appropriate workers
- Retries and error handling are built-in
- Progress tracking throughout the pipeline

## Evaluation System

### Comparison Framework

The system collects human feedback through comparisons:

- Users compare multiple AI-generated builds
- Comparisons can be head-to-head or ranking-based
- Results are collected and analyzed

### ELO Rating System

A competitive rating system tracks performance:

- Models, prompts, and samples are rated
- Ratings update based on comparison outcomes
- Leaderboards show current rankings
- Tag-based filtering for specialized comparisons

## Authentication and Authorization

### OAuth Integration

The system supports OAuth login through:

- GitHub
- Google

### Role-Based Access Control

Granular permission system with roles like:

- Administrator
- Researcher
- Sample Reviewer
- Voting Participant

## Object Storage

The system stores various artifacts:

- Generated code
- Minecraft schematics (.nbt files)
- 3D model files
- Images and renders
- AI model responses

## Deployment Architecture

The system is designed to be deployed as microservices:

- Each component can scale independently
- Services communicate through message queues
- Database is centralized for consistency
- Object storage is shared across components