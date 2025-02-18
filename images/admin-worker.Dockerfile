FROM mcbenchmark/minecraft-builder-base:2024-12-11

RUN npm install -g eslint

COPY deps/requirements.txt requirements.txt
COPY deps/admin-worker-requirements.txt admin-worker-requirements.txt
RUN pip install -r requirements.txt -r admin-worker-requirements.txt

COPY . /usr/lib/mc-bench-backend
RUN pip install /usr/lib/mc-bench-backend[admin-worker]

ENV NUM_WORKERS=4
ENTRYPOINT []
CMD exec celery -A mc_bench.apps.admin_worker worker -Q admin --concurrency $NUM_WORKERS
