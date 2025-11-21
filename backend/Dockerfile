# Use official Python runtime as base image
FROM python:3.13-slim

# Set working directory in container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy pyproject.toml
COPY pyproject.toml .

# update pip
Run pip install --upgrade pip

# Install Python dependencies
RUN pip install .  

# Copy application code (prod)
COPY src/ ./src/
COPY scripts/ ./scripts/
COPY data/ ./data/

# Create logs directory
RUN mkdir -p logs

# Make script executable
RUN chmod +x scripts/import_data.py

# Add root to PYTHONPATH so imports work
ENV PYTHONPATH=/app

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Expose port 
EXPOSE 8000

# Run the application
CMD ["python", "src/main.py", "src/scripts/import_data.py", "src/data/demo_data.json"]
