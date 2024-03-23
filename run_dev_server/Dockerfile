# Use an official Python runtime as a parent image
FROM python:3.8

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory
WORKDIR /SLED

# Install dependencies
COPY requirements.txt /SLED/
RUN pip install -r requirements.txt
