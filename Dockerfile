FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files first for better caching
COPY pyproject.toml ./

# Install Python dependencies
RUN pip3 install --no-cache-dir --upgrade pip setuptools wheel && \
    pip3 install --no-cache-dir -e . && \
    pip3 install --no-cache-dir \
    python-dotenv \
    python-dateutil \
    flask-sqlalchemy \
    flask-migrate \
    pymysql \
    cryptography \
    gunicorn

# Patch getargspec compatibility issue for Python 3.12
RUN find /usr/local/lib/python3.12 -type f -name "*.py" \
    -exec sed -i 's/from inspect import getargspec/from inspect import getargs/g' {} + || true

# Copy application code
COPY . .

# Set environment variables for Python
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

# Expose port
EXPOSE 8080

# Run the application with gunicorn for production
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "4", "--threads", "2", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-", "app:app"]

