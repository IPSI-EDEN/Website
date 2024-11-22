# Use the official Python image as the base
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements.txt into the container
COPY requirements.txt .

# Install required system dependencies for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends gcc && \
    rm -rf /var/lib/apt/lists/*

# Create the .env directory (Ensure it's created)
RUN mkdir -p /app/.env

# Create a virtual environment and install dependencies
RUN python -m venv /app/.env && \
    /app/.env/bin/pip install --no-cache-dir --upgrade pip && \
    /app/.env/bin/pip install --no-cache-dir -r requirements.txt

# Check if the virtual environment was created correctly
RUN if [ ! -f /app/.env/bin/activate ]; then echo "Environment not created correctly"; exit 1; fi

# Copy the application code into the container
COPY . .

# Expose the port Django runs on (default: 8000)
EXPOSE 8000

# Default command to run the Django application
CMD ["/bin/bash", "-c", "source /app/.env/bin/activate && python manage.py runserver 0.0.0.0:8000"]
