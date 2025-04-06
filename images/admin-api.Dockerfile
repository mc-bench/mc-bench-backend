FROM python:3.12.7

RUN pip install uv

COPY deps/requirements.txt requirements.txt
COPY deps/api-requirements.txt api-requirements.txt
RUN uv pip install --system -r requirements.txt -r api-requirements.txt

COPY . /usr/lib/mc-bench-backend
RUN uv pip install --system /usr/lib/mc-bench-backend[api]

CMD ["uvicorn", "mc_bench.apps.admin_api.__main__:app", "--proxy-headers", "--port", "8000", "--host", "0.0.0.0"]
