FROM python:3.7.9-slim-buster as base

WORKDIR /app

FROM base as builder

ARG LOCAL_USER_ID=1000
ENV PORT=8000

ENV PIP_DEFAULT_TIMEOUT=100 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONFAULTHANDLER=1 \
    PYTHONHASHSEED=random \
    PYTHONUNBUFFERED=1 \
    GCP_PROJECT_ID=postos-anp\
    GCP_CREDENTIALS_BQ=./fuelstations/credentials/credentials.json\
    GCP_CREDENTIALS_PUBSUB=./fuelstations/credentials/pubsub_credentials.json\
    GCP_BQ_TABLE=postos_anp.staging_postos_anp\
    GCP_PUBSUB_TOPIC_ID=fuel-station-data
RUN adduser --system -u ${LOCAL_USER_ID:-1000} crawler && \
    apt-get update && \
    apt-get -qq -y install curl  && \
    apt-get install -y gnupg2

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY . .

RUN chown crawler /app

USER crawler

EXPOSE ${PORT}

CMD exec uvicorn --host 0.0.0.0 --port ${PORT} main:app
