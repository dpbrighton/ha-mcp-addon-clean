ARG BUILD_FROM
FROM ${BUILD_FROM}

# Install Python and pip
RUN apk add --no-cache \
    python3 \
    py3-pip \
    py3-requests

# Install FastAPI and Uvicorn
RUN pip3 install --no-cache-dir --break-system-packages \
    fastapi \
    uvicorn

# Copy server script
COPY ha_mcp_server.py /app/ha_mcp_server.py
WORKDIR /app

# Run server
CMD ["uvicorn", "ha_mcp_server:app", "--host", "0.0.0.0", "--port", "8000"]
