# Generated for ecommerce-checkout-support
ARG PYTHON_VERSION=3.13-slim

FROM python:${PYTHON_VERSION} AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    APP_NAME=ecommerce-checkout-support
WORKDIR /app/src
RUN apt-get update && apt-get install -y --no-install-recommends build-essential libpq-dev git curl \
    && rm -rf /var/lib/apt/lists/*
RUN python -m pip install --no-cache-dir --upgrade pip uv

FROM base AS dev
ENV APP_ENV=dev
COPY pyproject.toml uv.lock ./
COPY . ./
# COPY tests /app/tests  # tests are outside build context
ENV PYTHONPATH=/app/src
ENV PATH="/app/src/.venv/bin:$PATH"
RUN uv sync --frozen --all-extras --no-sources
CMD ["uvicorn", "ecommerce_checkout_support.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

FROM base AS prod
ENV APP_ENV=prod
COPY pyproject.toml uv.lock ./
COPY . ./
ENV PYTHONPATH=/app/src
ENV PATH="/app/src/.venv/bin:$PATH"
RUN uv sync --frozen --no-dev --no-sources
CMD ["uvicorn", "ecommerce_checkout_support.main:app", "--host", "0.0.0.0", "--port", "8000"]
