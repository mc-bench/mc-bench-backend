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
	pip install -e .[dev]

fmt:
	ruff check --select I --fix
	ruff format .

check:
	ruff check

check-fix:
	ruff check --fix

build-local-server-image:
	cd images/minecraft-server && python build-and-save-image.py --tag built
