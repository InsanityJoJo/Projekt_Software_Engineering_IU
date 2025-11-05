# Use official Python runtime as base image
FROM python:3.13-slim

# Set working directory in container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY scripts/ ./scripts/
COPY data/ ./data/

# Create logs directory
RUN mkdir -p logs

# Make script executable
RUN chmod +x scripts/import_data.py

# Add root to PYTHONPATH so imports work
ENV PYTHONPATH=/app

# Expose port (adjust as needed)
EXPOSE 8000

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Run the application
CMD ["python", "src/main.py", "src/scripts/import_data.py", "src/data/demo_data.json"]
