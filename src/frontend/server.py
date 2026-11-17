import sys, inspect, os
current_dir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

import requests
import uvicorn

from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi import Request, HTTPException
from fastapi.responses import Response

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from helpers import index, try_connect_endpoint

app = FastAPI()

# Directory containing server.py
BASE_DIR = Path(__file__).resolve().parent
BACKEND_URL = index(1, sys.argv) or "http://127.0.0.1:7676"

print("Application base directory: " + str(BASE_DIR))
print("Backend URL: " + BACKEND_URL)
print("Backend connectivity: " + str(try_connect_endpoint(BACKEND_URL)))

@app.get("/", response_class=HTMLResponse)
async def home():
    index_path = BASE_DIR / "templates" / "index.html"
    print(index_path)
    if not index_path.exists():
        return HTMLResponse(
            content="index.html not found",
            status_code=404
        )

    return HTMLResponse(
        content=index_path.read_text(encoding="utf-8")
    )

@app.get("/stats.html", response_class=HTMLResponse)
async def statistics():
    return HTMLResponse(
        content=(BASE_DIR / "templates" / "stats.html").read_text(encoding="utf-8")
    )

@app.api_route("/api/{path:path}", methods=["GET", "POST", "DELETE"])
async def proxy(path:str, request: Request):
    url = f"{BACKEND_URL}/api/{path}"

    try:
        response = requests.request(
            method=request.method,
            url=url,
            params=request.query_params,
            data=await request.body(),
            headers={
                key: value
                for key, value in request.headers.items()
                if key.lower() in {"content-type", "x-preferred-node"}
            },
            timeout=300
        )

        return Response(
            content=response.content,
            status_code=response.status_code,
            headers={
                key: value
                for key, value in response.headers.items()
                if key.lower() in {
                    "content-type",
                    "content-disposition",
                    "content-length",
                    "cache-control",
                    "last-modified",
                    "etag",
                    "x-served-by"
                }
            }
        )

    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=str(e))


app.mount(
    "/static",
    StaticFiles(directory=BASE_DIR / "static"),
    name="static"
)

if __name__ == "__main__":

    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=7677,
        reload=True
    )