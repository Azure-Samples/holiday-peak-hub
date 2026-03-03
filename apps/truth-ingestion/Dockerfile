# Generated for truth-ingestion
ARG PYTHON_VERSION=3.13-slim

FROM python:${PYTHON_VERSION} AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    APP_NAME=truth-ingestion
WORKDIR /app/src
RUN apt-get update && apt-get install -y --no-install-recommends build-essential libpq-dev git curl \
    && rm -rf /var/lib/apt/lists/*

FROM base AS dev
ENV APP_ENV=dev
COPY pyproject.toml ./pyproject.toml
COPY . ./
ENV PYTHONPATH=/app/src
RUN python -m pip install --upgrade pip && \
    python -m pip install --no-cache-dir -e .[dev,test,lint]
CMD ["uvicorn", "truth_ingestion.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

FROM base AS prod
ENV APP_ENV=prod
COPY pyproject.toml ./pyproject.toml
COPY . ./
ENV PYTHONPATH=/app/src
RUN python -m pip install --upgrade pip && \
    python -m pip install --no-cache-dir .
CMD ["uvicorn", "truth_ingestion.main:app", "--host", "0.0.0.0", "--port", "8000"]
