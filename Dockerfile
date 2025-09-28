# Use official Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy Python script into container
COPY image_checker.py .

# Install dependencies
RUN pip install requests

# Run the script by default
CMD ["python", "image_checker.py"]
