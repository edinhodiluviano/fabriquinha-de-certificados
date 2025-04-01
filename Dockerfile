# Dockerfile

# pull the official docker image
FROM python:3.13.2-bookworm

# set work directory
WORKDIR /app

# set env variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# install dependencies
COPY pyproject.toml /app/
COPY uv.lock /app/
RUN pip install uv
RUN uv sync --frozen --no-dev

# copy project
COPY logging.conf /app/
COPY run-server.py /app/
COPY fabriquinha /app/fabriquinha
