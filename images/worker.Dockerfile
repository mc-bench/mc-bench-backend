FROM python:3.12.7

COPY deps/requirements.txt requirements.txt
COPY deps/worker-requirements.txt worker-requirements.txt
RUN pip install -r requirements.txt -r worker-requirements.txt

COPY . /usr/lib/mc-bench-backend
RUN pip install /usr/lib/mc-bench-backend[worker]

ENV NUM_WORKERS=1

ENTRYPOINT []
CMD exec celery -A mc_bench.apps.worker worker -Q default --concurrency $NUM_WORKERS -n $WORKER_NAME
