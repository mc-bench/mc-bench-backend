FROM python:3.12.7

COPY deps/requirements.txt requirements.txt
COPY deps/server-worker-requirements.txt server-worker-requirements.txt
RUN pip install -r requirements.txt -r server-worker-requirements.txt

COPY . /usr/lib/mc-bench-backend
RUN pip install /usr/lib/mc-bench-backend[server-worker]

CMD celery -A mc_bench.apps.server_worker worker -Q server --concurrency $NUM_WORKERS
