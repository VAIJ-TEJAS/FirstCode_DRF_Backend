FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=FirstCode_DRF_Backend.settings
ENV CELERY_BROKER_URL=redis://redis:6379/0
ENV CELERY_RESULT_BACKEND=redis://redis:6379/0

# Create and set the working directory
WORKDIR /app

# Install system dependencies and upgrade pip
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && pip install --upgrade pip \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy requirements.txt
COPY requirements.txt /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project
COPY . /app/

# Expose port
EXPOSE 8000

# Development mode with auto-reload (for docker-compose)
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
