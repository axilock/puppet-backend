# Example plugin Dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy plugin code
COPY plugin.py .

# Set entrypoint
ENTRYPOINT ["python", "plugin.py"]
