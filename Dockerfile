FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for psycopg2
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Run with verbose output
CMD echo "=== Starting Revna ===" && \
    echo "=== Python env check ===" && \
    python -c "import os; print('DATABASE_URL set:', 'DATABASE_URL' in os.environ); print('Value prefix:', os.environ.get('DATABASE_URL', 'NOT SET')[:40])" && \
    echo "=== Config check ===" && \
    python -c "from backend.config import settings; print('database_url:', settings.database_url[:40]); print('sync_database_url:', settings.sync_database_url[:40])" && \
    echo "=== Running migrations ===" && \
    alembic upgrade head 2>&1 && \
    echo "=== Starting uvicorn ===" && \
    uvicorn backend.main:app --host 0.0.0.0 --port "${PORT:-8000}"
