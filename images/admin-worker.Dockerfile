FROM mcbenchmark/minecraft-builder-base:2024-12-11

RUN npm install -g eslint

RUN pip install uv

COPY deps/requirements.txt requirements.txt
COPY deps/admin-worker-requirements.txt admin-worker-requirements.txt
RUN uv pip install --system -r requirements.txt -r admin-worker-requirements.txt

COPY . /usr/lib/mc-bench-backend
RUN uv pip install --system /usr/lib/mc-bench-backend[admin-worker]

ENV NUM_WORKERS=4
ENTRYPOINT []
CMD exec celery -A mc_bench.apps.admin_worker worker -Q admin,generation,prompt,parse,validate,post_process,prepare --concurrency $NUM_WORKERS -n $WORKER_NAME
