FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY . .

# Install package
RUN pip3 install -e .

# Expose port
EXPOSE 8888

# Run the application
CMD ["python3", "main.py"]

