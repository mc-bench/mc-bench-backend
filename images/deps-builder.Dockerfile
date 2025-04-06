ARG PYTHON_VERSION
FROM python:${PYTHON_VERSION}-slim

RUN pip install uv
