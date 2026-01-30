FROM python:3.13-slim

WORKDIR /app

# Install uv for fast dependency installation
RUN pip install uv

# Copy dependency files
COPY pyproject.toml ./

# Install dependencies
RUN uv pip install --system -e .

# Copy source code
COPY src/ ./src/

# Expose port
EXPOSE 8000

# Run with uvicorn
CMD ["uvicorn", "crud_service.main:app", "--host", "0.0.0.0", "--port", "8000"]
