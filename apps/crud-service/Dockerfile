FROM python:3.13-slim
ARG APP_UID=10001
ARG APP_GID=10001

RUN groupadd --gid ${APP_GID} appgroup && useradd --uid ${APP_UID} --gid ${APP_GID} --create-home --home-dir /home/appuser --shell /usr/sbin/nologin appuser \
	&& mkdir -p /app && chown -R appuser:appgroup /app

WORKDIR /app

# Required because pyproject uses a Git source override for holiday-peak-lib.
RUN apt-get update && apt-get install -y --no-install-recommends git \
	&& rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency installation
RUN pip install uv

# Copy dependency files
COPY apps/crud-service/src/pyproject.toml ./
COPY apps/crud-service/README.md ./README.md

# Copy package source for editable install
COPY apps/crud-service/src/crud_service ./crud_service

# Install dependencies
RUN uv pip install --system -e .
RUN chown -R appuser:appgroup /app

# Expose port
EXPOSE 8000

USER appuser

# Run with uvicorn
CMD ["uvicorn", "crud_service.main:app", "--host", "0.0.0.0", "--port", "8000"]
