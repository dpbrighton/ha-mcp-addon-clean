from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
import uvicorn

async def health(request):
    return JSONResponse({"status": "ok", "service": "ha-mcp-clean"})

app = Starlette(
    routes=[
        Route("/", health),
    ]
)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
