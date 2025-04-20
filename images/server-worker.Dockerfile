FROM python:3.12.7

RUN pip install uv

COPY deps/requirements.txt requirements.txt
COPY deps/server-worker-requirements.txt server-worker-requirements.txt
RUN uv pip install --system -r requirements.txt -r server-worker-requirements.txt

COPY . /usr/lib/mc-bench-backend
RUN uv pip install --system /usr/lib/mc-bench-backend[server-worker]

ENV NUM_WORKERS=1

ENTRYPOINT []
CMD exec celery -A mc_bench.apps.server_worker worker -Q server --concurrency $NUM_WORKERS -n $WORKER_NAME
