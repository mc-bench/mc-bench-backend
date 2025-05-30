# Docker Guide

This is the easiest way to get the backend application stack up and running.


# Commands

Restart entire backend, will remove state.

```bash
make reset
```

# Quick Start

### Prerequistes
- docker
- git


## 0. Clone repository

```shell
git clone https://github.com/mc-bench/mc-bench-backend
```

## 1. Setup secrets
Copy the .env file

```bash
cp .env.template .env
```

Populate the `.env` with your values.

## 2. Setup login
See [frontend setup docs](https://github.com/mc-bench/mc-bench-frontend/blob/main/docs/setup_oauth_prereqs.md) for setting up a a Github Oauth 2.0 app.

Update the values in your local env file as:
```
export GITHUB_CLIENT_ID="<your_client_id>"
export GITHUB_CLIENT_SECRET="<your_client_secret>"
```

Auth call back URL should be on ```http://localhost:5173/login```


## 3. Start services
The following command will start all the services up

    docker-compose up -d --build

See the docker-compose.yml file for what services are started up and which ports they are listening on


## 4. Migrate Database
Setup the database schema

```shell
docker-compose run --rm api mc-bench-alembic upgrade head
```

## 5. Restart the Database
Update application code now that we have the schema setup

```shell
docker-compose restart
```

## 6. Tail the logs

```shell
docker-compose logs -f
```


## 7. Setup and run front end
See [mc-bench-frontend](https://github.com/mc-bench/mc-bench-frontend)


## 8. Login and give yourself a role
You will want [Grant Roles Doc](docs/role-grant.md)

## Logging Configuration

The application uses structured logging with configurable log levels. The default level is INFO, but you can change it to DEBUG for more detailed logs:

```shell
# In your .env file or as environment variables:
export LOG_LEVEL="DEBUG"  # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL
```

Additionally, several interval settings control how frequently certain operations are logged at INFO level:

```shell
# Log every N blocks placed during rendering
export LOG_INTERVAL_BLOCKS="100"

# Log every N materials baked during rendering
export LOG_INTERVAL_MATERIALS="10"

# Log every N build commands during server operations
export LOG_INTERVAL_COMMANDS="50"

# Log export progress at every N percent complete
export LOG_INTERVAL_EXPORT_PERCENT="10"
```
