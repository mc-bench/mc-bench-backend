FROM python:3.11.7

RUN apt-get update && apt-get install -y blender

COPY deps/render-worker-requirements.txt render-worker-requirements.txt
RUN pip install -r render-worker-requirements.txt

COPY . /usr/lib/mc-bench-backend
RUN pip install /usr/lib/mc-bench-backend[render-worker]

ENTRYPOINT []
CMD ["celery", "-A", "mc_bench.apps.render_worker", "worker", "-Q", "render"]
