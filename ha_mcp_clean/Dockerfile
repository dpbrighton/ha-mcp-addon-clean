FROM python:3.11-alpine

# Install build deps for websockets C extension
RUN apk add --no-cache gcc musl-dev

# Install Python dependencies
RUN pip3 install --no-cache-dir \
    fastapi \
    uvicorn \
    websockets \
    requests

# Copy app + wrapper
COPY ha_mcp_server.py /app/ha_mcp_server.py
COPY run.sh /app/run.sh

WORKDIR /app
RUN chmod +x /app/run.sh

CMD ["/app/run.sh"]
