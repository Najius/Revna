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
    echo "Shell DATABASE_URL starts with: ${DATABASE_URL:0:50}" && \
    echo "=== Python env check ===" && \
    python -c "import os; url=os.environ.get('DATABASE_URL','NOT SET'); print(f'Python DATABASE_URL: {url[:50] if len(url)>50 else url}...')" && \
    echo "=== Config check ===" && \
    python -c "from backend.config import settings; print(f'settings.database_url: {settings.database_url[:50]}...'); print(f'settings.sync_database_url: {settings.sync_database_url[:50]}...')" && \
    echo "=== Running migrations ===" && \
    alembic upgrade head 2>&1 && \
    echo "=== Starting uvicorn ===" && \
    uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}
