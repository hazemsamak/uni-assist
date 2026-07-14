# Use the official Microsoft Playwright Python base image matching the requirements version
FROM mcr.microsoft.com/playwright/python:v1.61.0-jammy

# Set environment variables to prevent Python from writing pyc files and buffering stdout/stderr
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Set the working directory inside the container
WORKDIR /app

# Copy only requirements first to utilize Docker's cache layer
COPY requirements.txt /app/

# Install the Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the project files
COPY . /app/

# Expose the port the FastAPI server listens on
EXPOSE 8000

# Start Uvicorn to serve the API
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
