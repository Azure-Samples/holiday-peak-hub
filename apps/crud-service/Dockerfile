FROM python:3.13-slim

WORKDIR /app

# Install uv for fast dependency installation
RUN pip install uv

# Copy dependency files
COPY apps/crud-service/src/pyproject.toml ./
COPY apps/crud-service/README.md ./README.md

# Copy package source for editable install
COPY apps/crud-service/src/crud_service ./crud_service
COPY lib/src ./holiday_peak_lib_src

# Install dependencies
RUN uv pip install --system -e ./holiday_peak_lib_src -e .

# Expose port
EXPOSE 8000

# Run with uvicorn
CMD ["uvicorn", "crud_service.main:app", "--host", "0.0.0.0", "--port", "8000"]
