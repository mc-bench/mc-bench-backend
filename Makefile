#.PHONY: build-images build-worker build-api build-admin-api build-admin-worker


sync-deps:
	pip-compile -o deps/requirements.txt deps/requirements.in --constraint deps/dev-requirements.in --constraint deps/api-requirements.in --constraint deps/worker-requirements.in
	pip-compile -o deps/api-requirements.txt deps/api-requirements.in --constraint deps/requirements.txt --constraint deps/worker-requirements.in --constraint deps/dev-requirements.in
	pip-compile -o deps/worker-requirements.txt deps/worker-requirements.in --constraint deps/requirements.txt --constraint deps/api-requirements.txt --constraint deps/dev-requirements.in
	pip-compile -o deps/server-worker-requirements.txt deps/server-worker-requirements.in --constraint deps/requirements.txt --constraint deps/api-requirements.txt --constraint deps/dev-requirements.in --constraint deps/worker-requirements.in
	pip-compile -o deps/dev-requirements.txt deps/dev-requirements.in --constraint deps/requirements.txt --constraint deps/api-requirements.txt --constraint deps/worker-requirements.txt

build-%:
	docker build -t mcbench/$* -f images/$*.Dockerfile .

all-images: build-admin-api build-admin-worker build-api build-worker

install-dev:
	pip install -e ".[dev]"

fmt:
	ruff check --select I --fix
	ruff format .

check:
	ruff check

check-fix:
	ruff check --fix

build-local-server-image:
	cd images/minecraft-server && python build-and-save-image.py --tag built

build-local-builder-image:
	docker build -f images/builder-runner/builder-runner.Dockerfile -t registry.digitalocean.com/mcbench/minecraft-builder:built images/builder-runner

build-local-images: build-local-builder-image build-local-server-image
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
