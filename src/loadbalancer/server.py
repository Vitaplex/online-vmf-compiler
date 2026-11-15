
from fastapi import Request, HTTPException
from fastapi.responses import Response
from fastapi import FastAPI
import requests
import uvicorn

from loadbalancer_service import LoadBalancerService

app = FastAPI()
loadbalancer_service = LoadBalancerService()

@app.api_route("/api/{path:path}", methods=["GET", "POST", "DELETE"])
async def proxy(path:str, request: Request):
    
    url = loadbalancer_service.resolve_node()

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
                key: value
                for key, value in response.headers.items()
                if key.lower() in {
                    "content-type",
                    "content-disposition",
                    "content-length",
                    "cache-control",
                    "last-modified",
                    "etag"
                }
            }
        )

    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=str(e))

if __name__ == "__main__":

    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=7676,
        reload=True
    )