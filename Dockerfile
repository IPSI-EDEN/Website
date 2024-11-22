# Use the official Python image as the base
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements.txt into the container
COPY requirements.txt .

# Install required system dependencies for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends gcc && \
    rm -rf /var/lib/apt/lists/*

# Install the Python dependencies globally (without a virtual environment)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the application code into the container
COPY . .

# Expose the port Django runs on (default: 8000)
EXPOSE 8000

# Default command to run the Django application
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
