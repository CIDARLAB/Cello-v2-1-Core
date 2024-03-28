# Use an OpenJDK base image
FROM openjdk:11-jre-slim as java-base

# Use an official Python runtime as a second stage
FROM python:3.11-slim-buster

# Copy Java from the Java base image
COPY --from=java-base /usr/local/openjdk-11 /usr/local/openjdk-11
ENV PATH="/usr/local/openjdk-11/bin:${PATH}"

#RUN apt-get update && apt-get install -y gcc musl-dev linux-headers python3-dev
RUN apt-get update && apt-get install -y build-essential yosys && apt-get clean

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Run app with run.py
CMD ["python", "run.py"]
