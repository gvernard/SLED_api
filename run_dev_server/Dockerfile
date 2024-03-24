# Use an official Python runtime as a parent image
FROM python:3.6

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory
WORKDIR /SLED

# Install dependencies
COPY requirements.txt /SLED/
RUN python3 -m pip install -r requirements.txt