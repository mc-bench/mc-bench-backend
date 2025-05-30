# Python Enviornment Quick Start


This approach will setup all of depenendices in your local python environment.


## Prerequistes
- docker (optional)
- git
- python

## 0. Clone repository

```shell
git clone https://github.com/mc-bench/mc-bench-backend
```

## 1. Setup python

Python 3.12.7 installed. We recommend [pyenv]("https://github.com/pyenv/pyenv").

```shell
pyenv install 3.12.7
```

## 2. Setup python environment

A virtual environment created and activated somewhere

via pyenv (recommended)
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



## 3. Setup secrets
Copy the .env file

```bash
cp .env.template .env
```

Populate the `.env` with your values.

Load envs into shell
```bash
source .env
```


## 4. Setup login
See [frontend setup docs](https://github.com/mc-bench/mc-bench-frontend/blob/main/docs/setup_oauth_prereqs.md) for setting up a a Github Oauth 2.0 app.

Update the values in your local env file as:
```
export GITHUB_CLIENT_ID="<your_client_id>"
export GITHUB_CLIENT_SECRET="<your_client_secret>"
```
Auth call back URL should be on ```http://localhost:5173/login```


Load envs into shell
```bash
source .env
```


## 5. Install `mc-bench` into local python
Install the project, as an editable package
```bash
pip install -e ".[dev]"
```


## 6. Database Setup
Once you have completed setting up the python enviornment, it is time to setup the databases.

This application requires 3 databases: postgres, redis,

There are 2 approaches, running the database as a local service or from the docker-compose.

### Option 1: Docker run as background services (easiest)
This will run the doc

```bash
docker-compose run -d -p 5432:5432 postgres
docker-compose run -d -p 6379:6379 redis
```

### Option 2: Install packages manually and run services (without docker)

MacOS [homebrew](https://brew.sh/) setup

    brew install postgresql@16
    brew install redis

    brew services start postgresql@16
    brew services start redis


You will need to create a database

    ./bin/manual-postgres-setup



## 7. Run migrations
Load the environment variables with
```bash
source .env
```

With the python virtual environment activated, run the database migrations

```shell
mc-bench-alembic upgrade head
```


## 8. Setup and run front end
See [mc-bench-frontend](https://github.com/mc-bench/mc-bench-frontend)

<< frontend running >>


## 9. Run services in terminal

python celery  -A  mc_bench.apps.admin_worker flower
python python  -m  mc_bench.apps.scheduler
python server  /data  --console-address  0.0.0.0:9001
uvicorn mc_bench.apps.admin_api.__main__:app --proxy-headers --port 8000 --host 0.0.0.0

## 8. Login and give yourself a role
You will want
[Grant Roles Doc](docs/role_grant.md)






# Working on the rendering code

Unfortunately bpy, the python library for Blender, is not compatible with python 3.12.
If you want to work on the rendering code, you need to use python 3.11.7.
Once you have installed the python 3.11.7 environment, you can install the dependencies with:

```shell
pip install -e .[render-worker]
```

# Other Useful Guides

- [Build local gameservers](docs/build_local_gameservers.md)
