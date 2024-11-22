# Use the official Python image as the base
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements.txt into the container
COPY requirements.txt .

# Create a virtual environment and install dependencies
RUN python -m venv .env && \
    ./.env/bin/pip install --no-cache-dir -r requirements.txt

# Copy the application code into the container
COPY . .

# Expose the port Django runs on (default: 8000)
EXPOSE 8000

# Default command to run the Django application
CMD ["/app/.env/bin/python", "manage.py", "runserver", "0.0.0.0:8000"]
