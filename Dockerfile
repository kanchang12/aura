# Use the official lightweight Python image
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install system dependencies if needed (optional)
RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev && rm -rf /var/lib/apt/lists/*

# Copy only requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project into the container
# This includes app.py, routes/, services/, etc.
COPY . .

# Expose the port Flask usually runs on
EXPOSE 8080

# Use Gunicorn for production (ensure gunicorn is in your requirements.txt)
# Replace 'app:app' with the variable name of your Flask instance in app.py
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "app:app"]
