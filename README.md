# Development

This is known to work with python 3.12.7

# Pre-Requisites

1. python installed. We recommend [pyenv]("https://github.com/pyenv/pyenv").

```shell
pyenv install 3.12.7
```

2. A virtual environment created and activated somewhere

    via pyenv
    ```shell
   pyenv virtualenv 3.12.7 mc-bench-backend
   pyenv activate mc-bench-backend
   ```
   
    via vanilla venv

    ```shell
    pyenv shell 3.12.7
    python -m venv .venv
    source .venv/bin/activate
    ```
   
Any other mechanism should work as well

3. editably install the project
    
    ```pip install -e .[dev,api,worker,server-worker]```

# Run migrations
Load the environment variables with
```bash
source .env
```

With the python virtual environment activated, run the database migrations

```shell
$ mc-bench-alembic upgrade head
```

Or run 
```shell
$ docker-compose run --rm api mc-bench-alembic upgrade head
```

# Setup oauth2

You need to create a Github oauth app and save the client and secret in your local env file as:

GITHUB_CLIENT_ID
GITHUB_CLIENT_SECRET

See [frontend setup docs](https://github.com/mc-bench/mc-bench-frontend/blob/main/docs/setup_oauth_prereqs.md) 
Auth call back URL should be on ```http://localhost:5173/login```

# Login and give yourself a role

Running the frontend and the backend, signup and create a username.

Then use:

```python
./bin/grant-user-role grant --username {your username} --role admin
```
To see the usernames use:

```shell

./bin/grant-user-role list-users
```

To see the roles use:

```shell

./bin/grant-user-role list-roles
```

# Start the ephemeral game server
Build your own ephemeral game server locally. See [build documentation](https://github.com/mc-bench/mc-bench-backend/blob/main/docs/build_local_gameservers.md) for more details.

Run
```bash
cd ../gameservers
git checkout minecraft-1.21.1
docker build -t registry.digitalocean.com/mcbench/gameservers:minecraft-1.21.1-latest .
```


# Services run via docker

The following command will start all the services up

    docker-compose up -d --build

See the docker-compose.yml file for what services are started up and which ports they are listening on

`TODO: figure out hot reloading in the containers`

# Tail the logs

```shell
docker-compose logs -f
```

# Logging Configuration

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

# Formatting/Linting

Run the ruff formatter
```shell
make fmt
````

Run the ruff checker
```shell
make check
```

Run the ruff checker with --fix option
```shell
make check-fix
```

# Working on the rendering code

Unfortunately bpy, the python library for Blender, is not compatible with python 3.12.
If you want to work on the rendering code, you need to use python 3.11.7.
Once you have installed the python 3.11.7 environment, you can install the dependencies with:

```shell
pip install -e .[render-worker]
```

# Other Useful Guides

- [Build local gameservers](docs/build_local_gameservers.md)
