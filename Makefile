#.PHONY: build-images build-worker build-api build-admin-api build-admin-worker

sync-deps:
	# uv pip compile --python-version <version> -o <output> <input> --contstraints <constraints...>
	docker run --rm -v `pwd`/deps:/deps ghcr.io/astral-sh/uv:python3.12-bookworm bash -c "cd /deps && \
		uv pip compile --python-version 3.12.7 requirements.in -o requirements.txt -c known-constraints.in && \
		uv pip compile --python-version 3.12.7 api-requirements.in -o api-requirements.txt -c requirements.txt -c known-constraints.in && \
		uv pip compile --python-version 3.12.7 worker-requirements.in -o worker-requirements.txt -c requirements.txt -c api-requirements.txt -c known-constraints.in && \
		uv pip compile --python-version 3.12.7 admin-worker-requirements.in -o admin-worker-requirements.txt -c requirements.txt -c api-requirements.txt -c worker-requirements.txt -c known-constraints.in && \
		uv pip compile --python-version 3.12.7 server-worker-requirements.in -o server-worker-requirements.txt -c requirements.txt -c api-requirements.txt -c worker-requirements.txt -c admin-worker-requirements.txt -c known-constraints.in"

	docker run --platform linux/amd64 --rm -v `pwd`/deps:/deps ghcr.io/astral-sh/uv:python3.11-bookworm bash -c "cd /deps && \
		uv pip compile --python-version 3.11.7 render-worker-requirements.in -o render-worker-requirements.txt -c requirements.txt -c api-requirements.txt -c worker-requirements.txt -c admin-worker-requirements.txt -c server-worker-requirements.txt -c known-constraints.in"

	docker run --rm -v `pwd`/deps:/deps ghcr.io/astral-sh/uv:python3.12-bookworm bash -c "cd /deps && \
		uv pip compile  --python-version 3.12.7 --no-emit-package pip --no-emit-package setuptools dev-requirements.in -o dev-requirements.txt -c requirements.txt -c api-requirements.txt -c worker-requirements.txt -c admin-worker-requirements.txt -c server-worker-requirements.txt -c render-worker-requirements.txt -c known-constraints.in"

build-%:
	docker build -t mcbench/$* -f images/$*.Dockerfile .

all-images: build-admin-api build-admin-worker build-api build-worker


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
