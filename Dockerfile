FROM python:3.12-slim as builder

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./

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

RUN find /usr/local/lib/python3.12 -type f -name "*.py" \
    -exec sed -i 's/from inspect import getargspec/from inspect import getargs/g' {} + || true

COPY . .

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

EXPOSE 8080

CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "4", "--threads", "2", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-", "app:app"]