ARG BUILD_FROM=ghcr.io/home-assistant/aarch64-base:latest
ARG BUILD_VERSION=1.0.0
ARG BUILD_ARCH=aarch64

FROM $BUILD_FROM

# Install python + requests + FastAPI + uvicorn
RUN apk add --no-cache python3 py3-pip
RUN pip3 install --no-cache-dir fastapi uvicorn requests

# Copy server
COPY ha_mcp_server.py /

# Set working directory
WORKDIR /

# Start script will be run
CMD ["/run"]
