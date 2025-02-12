#.PHONY: build-images build-worker build-api build-admin-api build-admin-worker


sync-deps: build-deps-images
	docker run --rm -v `pwd`/deps:/deps mcbench/deps-builder:3.12.7 bash -c "cd /deps && pip-compile -o requirements.txt requirements.in -c known-constraints.in"
	docker run --rm -v `pwd`/deps:/deps mcbench/deps-builder:3.12.7 bash -c "cd /deps && pip-compile -o api-requirements.txt api-requirements.in --constraint requirements.txt -c known-constraints.in"
	docker run --rm -v `pwd`/deps:/deps mcbench/deps-builder:3.12.7 bash -c "cd /deps && pip-compile -o worker-requirements.txt worker-requirements.in --constraint requirements.txt --constraint api-requirements.txt -c known-constraints.in"
	docker run --rm -v `pwd`/deps:/deps mcbench/deps-builder:3.12.7 bash -c "cd /deps && pip-compile -o server-worker-requirements.txt server-worker-requirements.in --constraint requirements.txt --constraint api-requirements.txt --constraint worker-requirements.txt -c known-constraints.in"
	docker run --platform linux/amd64 --rm -v `pwd`/deps:/deps mcbench/deps-builder:3.11.7 bash -c "cd /deps && pip-compile -o render-worker-requirements.txt render-worker-requirements.in --constraint requirements.txt --constraint api-requirements.txt --constraint worker-requirements.txt --constraint server-worker-requirements.txt -c known-constraints.in"
	docker run --rm -v `pwd`/deps:/deps mcbench/deps-builder:3.12.7 bash -c "cd /deps && pip-compile -o dev-requirements.txt dev-requirements.in --constraint requirements.txt --constraint api-requirements.txt --constraint worker-requirements.txt --constraint server-worker-requirements.txt --constraint render-worker-requirements.txt -c known-constraints.in"

build-%:
	docker build -t mcbench/$* -f images/$*.Dockerfile .

all-images: build-admin-api build-admin-worker build-api build-worker

build-deps-images:
	docker build --build-arg PYTHON_VERSION=3.12.7 -t mcbench/deps-builder:3.12.7 -f images/deps-builder.Dockerfile .
	docker build --platform linux/amd64 --build-arg PYTHON_VERSION=3.11.7 -t mcbench/deps-builder:3.11.7 -f images/deps-builder.Dockerfile .

install-dev:
	pip install -e ".[dev]"

fmt:
	ruff check --select I,T20 --fix
	ruff format .

check:
	ruff check

check-fix:
	ruff check --fix

build-local-builder-image:
	docker build -f images/builder-runner/builder-runner.Dockerfile -t registry.digitalocean.com/mcbench/minecraft-builder:built images/builder-runner

build-local-images: build-local-builder-image
	docker-compose build

reset:
	docker-compose down -v
	source .env || echo "Be sure to create .env in the root per the template"
	# TODO: Check for local minecraft server and minecraft builder images
	docker-compose up -d postgres redis object
	echo "Sleeping for 10 seconds to let the database come up"
	sleep 10
	make install-dev
	mc-bench-alembic upgrade head
	docker-compose exec object sh -c "mc alias set object http://localhost:9000 fake_key fake_secret && \
		mc mb object/mcbench-backend-object-local && mc anonymous set download object/mcbench-backend-object-local && \
		mc mb object/mcbench-object-cdn-local && mc anonymous set download object/mcbench-object-cdn-local"

	docker-compose up -d --build

	make seed-data

	echo "Via the frontend log in, and then run:"
	echo ""
	echo " ./bin/grant-user-role grant --username YOURUSERNAME --role admin"
	echo ""
	echo "and then log out and log back in"
	echo ""

rebuild: install-dev build-local-images
	make reset

seed-data:
	docker cp `pwd`/dev/seed-data.sql `docker-compose ps --quiet postgres`:/tmp/file.sql
	docker-compose exec -e PGPASSWORD=mc-bench postgres psql -U mc-bench-admin -d mc-bench -f /tmp/file.sql

build-run:
	docker-compose up -d --build worker admin-worker server-worker api admin-api && docker-compose logs -f api admin-api server-worker admin-worker
