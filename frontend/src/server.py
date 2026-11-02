
from pathlib import Path
from fastapi.staticfiles import StaticFiles

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import uvicorn


app = FastAPI()

# Directory containing server.py
BASE_DIR = Path(__file__).resolve().parent.parent
print("BASE DIR: " + str(BASE_DIR))

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

app.mount(
    "/static",
    StaticFiles(directory=BASE_DIR / "static"),
    name="static"
)

if __name__ == "__main__":

    uvicorn.run(
        "server:app",
        host="127.0.0.1",
        port=7677,
        reload=True
    )