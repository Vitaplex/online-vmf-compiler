
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi import Request, HTTPException
from fastapi.responses import Response

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import requests
import uvicorn

app = FastAPI()

# Directory containing server.py
BASE_DIR = Path(__file__).resolve().parent.parent
print("BASE DIR: " + str(BASE_DIR))

BACKEND_URL = "http://127.0.0.1:7676" # Backend running on the same computer

@app.get("/", response_class=HTMLResponse)
async def home():
    index_path = BASE_DIR / "templates" / "index.html"

    if not index_path.exists():
        return HTMLResponse(
            content="index.html not found",
            status_code=404
        )

    return HTMLResponse(
        content=index_path.read_text(encoding="utf-8")
    )


@app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
async def proxy(path:str, request: Request):
    url = f"{BACKEND_URL}/api/{path}"

    try:
        response = requests.request(
            method=request.method,
            url=url,
            params=request.query_params,
            data=await request.body(),
            timeout=300
        )

        return Response(
            content=response.content,
            status_code=response.status_code,
            headers={
                "Content-Type": response.headers.get(
                    "Content-Type", "application/json"
                )
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