# 1. Base Image: Use an official, slim Python runtime as a parent image.
FROM python:3.9-slim-buster

# 2. Set Working Directory: Set the working directory inside the container.
WORKDIR /app

# 3. Install Dependencies:
# First, copy only the requirements file to leverage Docker's layer caching.
COPY requirements.txt .
# Install the packages specified in requirements.txt.
# --no-cache-dir keeps the image size smaller.
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copy Application Code:
# Copy the rest of the application's code into the working directory.
COPY . .

# 5. Expose Port:
# Expose the port the app runs on (gunicorn will run on port 5000).
EXPOSE 5000

# 6. Run Command:
# Define the command to run the application using the Gunicorn server.
# This is the production-ready way to run a Flask app.
# It binds the server to all network interfaces on port 5000.
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
