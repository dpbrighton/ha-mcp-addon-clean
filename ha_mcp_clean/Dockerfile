ARG BUILD_FROM
FROM ${BUILD_FROM}

# Install Python and deps
RUN apk add --no-cache \
    python3 \
    py3-pip \
    py3-requests

# Install FastAPI stack
RUN pip3 install --no-cache-dir --break-system-packages \
    fastapi \
    uvicorn

# Copy app + wrapper
COPY ha_mcp_server.py /app/ha_mcp_server.py
COPY run.sh /app/run.sh

WORKDIR /app
RUN chmod +x /app/run.sh

CMD ["/app/run.sh"]
