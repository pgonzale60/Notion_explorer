FROM mcr.microsoft.com/devcontainers/python:3.12

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    git \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /workspace

# Copy requirements files
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir pytest pytest-asyncio httpx black pylint

# Set Python path
ENV PYTHONPATH=/workspace
