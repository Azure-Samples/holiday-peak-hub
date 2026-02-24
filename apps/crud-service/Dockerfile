FROM python:3.13-slim

WORKDIR /app

# Install uv for fast dependency installation
RUN pip install uv

# Copy dependency files
COPY src/pyproject.toml ./
COPY README.md ./README.md

# Copy package source for editable install
COPY src/crud_service ./crud_service

# Install dependencies
RUN uv pip install --system -e .

# Expose port
EXPOSE 8000

# Run with uvicorn
CMD ["uvicorn", "crud_service.main:app", "--host", "0.0.0.0", "--port", "8000"]
