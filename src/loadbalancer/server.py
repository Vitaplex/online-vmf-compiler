import json
from typing import Annotated
from fastapi import Request, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi import FastAPI
import httpx
import uvicorn

from loadbalancer_service import LoadBalancerService

app = FastAPI()
loadbalancer_service = LoadBalancerService()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict this in production
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Served-By"]
)

@app.api_route("/api/{path:path}", methods=["GET", "POST", "DELETE"])
async def proxy(path:str, request: Request, x_preferred_node: Annotated[str | None, Header()] = None):
    parts = path.split("/")

    if len(parts) == 2 and parts[0] in ("compile", "bsp"):
        job_id = parts[1]

        node = await loadbalancer_service.resolve_job_node(job_id)

        if not node:
            raise HTTPException(
                status_code=404,
                detail=f"Job {job_id} not found on any backend"
            )

    elif path == "compile" and request.method == "POST":
        node = loadbalancer_service.resolve_node(x_preferred_node)

    elif path == "jobs-count":
        return await get_total_job_count()

    else:
        node = loadbalancer_service.resolve_node(x_preferred_node)

    if path == "jobs-count":
        return await get_total_job_count()

    print("Resolved:" + json.dumps(node))

    if not node:
        raise HTTPException(
            status_code=503,
            detail="No available backend nodes"
        )

    url = f"{node['address'].rstrip('/')}/api/{path}"
    
    try:
        async with httpx.AsyncClient(timeout=300) as client:
            response = await client.request(
                method=request.method,
                url=url,
                params=request.query_params,
                content=await request.body(),
                headers={
                    key: value
                    for key, value in request.headers.items()
                    if key.lower() not in {
                        "host", "content-length", "connection", "x-served-by"
                    }
                },
                follow_redirects=False
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
            } | {
                    "X-Served-By": node["name"]
            }
        )

    except httpx.TimeoutException as e:
        raise HTTPException(status_code=504, detail=f"Backend timeout: {str(e)}")

    except httpx.ConnectError as e:
        raise HTTPException(status_code=502, detail=f"Could not connect to backend: {str(e)}")

    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Backend request failed: {str(e)}")

if __name__ == "__main__":

    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=7676,
        reload=True
    )

async def get_total_job_count():
    total = 0

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            for node in loadbalancer_service.nodes:
                response = await client.get(
                    f"{node['address'].rstrip('/')}/api/jobs-count"
                )
                response.raise_for_status()
                total += int(response.text)

        return Response(
            content=str(total),
            media_type="text/plain"
        )

    except httpx.HTTPError as ex:
        raise HTTPException(status_code=502, detail=str(ex))