# Generated for ecommerce-product-detail-enrichment
ARG PYTHON_VERSION=3.13-slim

FROM python:${PYTHON_VERSION} AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    APP_NAME=ecommerce-product-detail-enrichment
WORKDIR /app/src
RUN apt-get update && apt-get install -y --no-install-recommends build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

FROM base AS dev
ENV APP_ENV=dev
COPY README.md /app/README.md
COPY pyproject.toml ./pyproject.toml
COPY . ./
# COPY tests /app/tests  # tests are outside build context
ENV PYTHONPATH=/app/src
RUN python -m pip install --upgrade pip && \
    python -m pip install --no-cache-dir -e .[dev,test,lint]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

FROM base AS prod
ENV APP_ENV=prod
COPY README.md /app/README.md
COPY pyproject.toml ./pyproject.toml
COPY . ./
ENV PYTHONPATH=/app/src
RUN python -m pip install --upgrade pip && \
    python -m pip install --no-cache-dir .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
