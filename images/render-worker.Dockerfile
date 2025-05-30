FROM python:3.11.7

RUN apt-get update && apt-get install -y blender

COPY deps/requirements.txt requirements.txt
COPY deps/render-worker-requirements.txt render-worker-requirements.txt
RUN pip install -r requirements.txt -r render-worker-requirements.txt

COPY . /usr/lib/mc-bench-backend
RUN pip install /usr/lib/mc-bench-backend[render-worker]

ENV NUM_WORKERS=1

ENTRYPOINT []
CMD exec celery -A mc_bench.apps.render_worker worker -Q render --concurrency $NUM_WORKERS -n $WORKER_NAME
