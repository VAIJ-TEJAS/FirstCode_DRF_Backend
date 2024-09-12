FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

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

# Copy the Django project files to the container
COPY . /app/

# Run the migration commands
#
RUN python manage.py makemigrations
RUN python manage.py migrate
RUN python manage.py migrate --run-syncdb

# Create superuser using environment variables
RUN python manage.py createsuperuser

# Expose the port the app runs on
EXPOSE 8000

# Run Django development server
#CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

CMD ["gunicorn", "--bind", "0.0.0.0:8000","--workers", "3", "FirstCode_DRF_Backend.wsgi:application"]