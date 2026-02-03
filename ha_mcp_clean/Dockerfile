ARG BUILD_FROM
FROM ${BUILD_FROM}

RUN apk add --no-cache \
    python3 \
    py3-pip \
    py3-requests

RUN pip3 install --no-cache-dir --break-system-packages \
    fastapi \
    uvicorn

COPY ha_mcp_server.py /app/ha_mcp_server.py
WORKDIR /app

CMD ["python3", "/app/ha_mcp_server.py"]
