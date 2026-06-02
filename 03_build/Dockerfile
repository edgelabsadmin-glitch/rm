# syntax=docker/dockerfile:1
FROM python:3.12-slim AS base

WORKDIR /app

# Install Python deps first (cached layer)
# psycopg[binary] bundles libpq — no system packages needed
COPY pyproject.toml .
RUN pip install --no-cache-dir -e "." && pip install --no-cache-dir gunicorn

# Copy application code
COPY . .

# Non-root user
RUN useradd -m -u 1001 pulse && chown -R pulse:pulse /app
USER pulse

EXPOSE 8000

# Uvicorn with 2 workers; App Runner sends SIGTERM on scale-down
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2", "--log-level", "info"]
