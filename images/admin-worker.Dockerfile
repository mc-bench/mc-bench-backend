FROM mcbenchmark/minecraft-builder-base:2024-12-11

RUN npm install -g eslint

COPY deps/requirements.txt requirements.txt
COPY deps/worker-requirements.txt worker-requirements.txt
RUN pip install -r requirements.txt -r worker-requirements.txt

COPY . /usr/lib/mc-bench-backend
RUN pip install /usr/lib/mc-bench-backend[worker]

ENTRYPOINT []
CMD ["celery", "-A", "mc_bench.apps.admin_worker", "worker", "-Q", "admin"]
