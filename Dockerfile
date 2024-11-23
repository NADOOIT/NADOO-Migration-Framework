FROM python:3.8-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY . .

# Install project dependencies
RUN pip install --no-cache-dir -e .
RUN pip install --no-cache-dir pytest pytest-cov libcst

# Set environment variables
ENV PYTHONPATH=/app/src

# Run tests by default
CMD ["pytest", "-v", "--cov=nadoo_migration_framework", "tests/"]
