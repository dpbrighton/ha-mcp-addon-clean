ARG BUILD_FROM
FROM ${BUILD_FROM}

# Install Python, pip, requests, and system dependencies
RUN apk add --no-cache \
    python3 \
    py3-pip \
    py3-requests \
    bash \
    build-base \
    libffi-dev \
    openssl-dev

# Install Python packages
RUN pip3 install --no-cache-dir --break-system-packages \
    fastapi \
    uvicorn \
    pyyaml \
    requests

# Copy the main application
COPY ha_mcp_server.py /app/ha_mcp_server.py

# Set working directory
WORKDIR /app

# Expose the port (optional, for clarity)
EXPOSE 8000

# Run the application
CMD ["uvicorn", "ha_mcp_server:app", "--host", "0.0.0.0", "--port", "8000"]
