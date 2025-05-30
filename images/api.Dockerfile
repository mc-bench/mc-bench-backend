FROM python:3.12.7

COPY deps/requirements.txt requirements.txt
COPY deps/api-requirements.txt api-requirements.txt
RUN pip install -r requirements.txt -r api-requirements.txt

COPY . /usr/lib/mc-bench-backend
RUN pip install /usr/lib/mc-bench-backend[api]

CMD ["uvicorn", "mc_bench.apps.api.__main__:app", "--proxy-headers", "--port", "8000", "--host", "0.0.0.0"]
