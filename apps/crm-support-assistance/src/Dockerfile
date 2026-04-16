# Generated for crm-support-assistance
ARG PYTHON_VERSION=3.13-slim
ARG APP_UID=10001
ARG APP_GID=10001

FROM python:${PYTHON_VERSION} AS base
ARG APP_UID=10001
ARG APP_GID=10001
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    APP_NAME=crm-support-assistance
RUN groupadd --gid ${APP_GID} appgroup && useradd --uid ${APP_UID} --gid ${APP_GID} --create-home --home-dir /home/appuser --shell /usr/sbin/nologin appuser \
    && mkdir -p /app && chown -R appuser:appgroup /app
WORKDIR /app/src
RUN apt-get update && apt-get install -y --no-install-recommends build-essential libpq-dev git curl \
    && rm -rf /var/lib/apt/lists/*
RUN python -m pip install --no-cache-dir --upgrade pip uv

FROM base AS dev
ENV APP_ENV=dev
COPY pyproject.toml uv.lock ./
COPY . ./
ENV PYTHONPATH=/app/src
ENV PATH="/app/src/.venv/bin:$PATH"
RUN uv sync --frozen --all-extras
RUN chown -R appuser:appgroup /app
USER appuser
CMD ["uvicorn", "crm_support_assistance.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

FROM base AS prod-builder
ENV APP_ENV=prod
# Copy requirements first for layer caching
COPY requirements.txt ./
RUN uv pip install --system --no-cache -r requirements.txt
# Install app code + lib wheel
COPY . ./
COPY holiday_peak_lib-0.2.1-py3-none-any.whl /tmp/
RUN uv pip install --system --no-deps /tmp/holiday_peak_lib-0.2.1-py3-none-any.whl \
    && rm -rf /tmp/*.whl
# Strip caches and tests from site-packages
RUN find /usr/local/lib -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; \
    find /usr/local/lib -name '*.pyc' -delete 2>/dev/null; \
    find /usr/local/lib -type d -name tests -path '*/site-packages/*' -exec rm -rf {} + 2>/dev/null; \
    true

FROM python:${PYTHON_VERSION} AS prod
ARG APP_UID=10001
ARG APP_GID=10001
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1
RUN groupadd --gid ${APP_GID} appgroup && useradd --uid ${APP_UID} --gid ${APP_GID} --create-home --home-dir /home/appuser --shell /usr/sbin/nologin appuser \
    && mkdir -p /app && chown -R appuser:appgroup /app
WORKDIR /app/src
RUN apt-get update && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/*
COPY --from=prod-builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=prod-builder --chown=appuser:appgroup /app/src /app/src
ENV WEB_CONCURRENCY=2
USER appuser
CMD ["sh", "-c", "python -m uvicorn crm_support_assistance.main:app --host 0.0.0.0 --port 8000 --workers ${WEB_CONCURRENCY:-4}"]
