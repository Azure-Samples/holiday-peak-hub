# Generated for search-enrichment-agent
ARG PYTHON_VERSION=3.13-slim
ARG APP_UID=10001
ARG APP_GID=10001

FROM python:${PYTHON_VERSION} AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    APP_NAME=search-enrichment-agent
RUN groupadd --gid ${APP_GID} appgroup && useradd --uid ${APP_UID} --gid ${APP_GID} --create-home --home-dir /home/appuser --shell /usr/sbin/nologin appuser \
    && mkdir -p /app && chown -R appuser:appgroup /app
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
RUN chown -R appuser:appgroup /app
USER appuser
CMD ["uvicorn", "search_enrichment_agent.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

FROM base AS prod-builder
ENV APP_ENV=prod
COPY pyproject.toml ./pyproject.toml
COPY . ./
ENV PYTHONPATH=/app/src
RUN python -m pip install --upgrade pip && \
    python -m pip install --no-cache-dir .

FROM python:${PYTHON_VERSION} AS prod
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1
RUN groupadd --gid ${APP_GID} appgroup && useradd --uid ${APP_UID} --gid ${APP_GID} --create-home --home-dir /home/appuser --shell /usr/sbin/nologin appuser \
    && mkdir -p /app && chown -R appuser:appgroup /app
WORKDIR /app/src
RUN apt-get update && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/*
COPY --from=prod-builder /usr/local /usr/local
COPY --from=prod-builder /app /app
RUN chown -R appuser:appgroup /app
USER appuser
CMD ["uvicorn", "search_enrichment_agent.main:app", "--host", "0.0.0.0", "--port", "8000"]
