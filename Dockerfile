FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy the application code to the container
COPY . .

# Upgrade pip and install the package
RUN pip install --upgrade pip \
    && pip install --no-cache-dir .

# Expose port for API service
EXPOSE 8080

# Command to run the REST API server for mobile apps
CMD ["python", "api_server.py"]