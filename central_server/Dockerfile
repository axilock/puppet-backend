FROM python:3.9-slim

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .


# Set environment variables
ENV PYTHONPATH=/

# Expose the API port
EXPOSE 8000

# Command to run the application - use explicit path

CMD ["python", "-m","app.main"]
