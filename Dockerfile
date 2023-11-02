# Use a base image
FROM python:3.11-slim-buster

# Metadata
LABEL maintainer="CIDAR Lab>"
LABEL description="CELLO"
LABEL version="2.1"

RUN apt-get update && apt-get install -y \
    git build-essential clang bison flex \
    libreadline-dev gawk tcl-dev libffi-dev graphviz \
    xdot pkg-config python3 python3-pip libboost-system-dev \
    libboost-python-dev libboost-filesystem-dev zlib1g-dev 

RUN git clone https://github.com/YosysHQ/yosys.git && \
   cd yosys && \
   make && \
   make install

# Set the working directory inside the container
WORKDIR /app

# Copy the entire application into the Docker image
COPY . /app

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Default command to run your application
CMD ["python", "run.py"]
