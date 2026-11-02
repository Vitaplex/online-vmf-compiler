
import json

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from game_file_manager import GameFileManager
from compile_job_manager import CompileJobManager


# Dependencies
game_file_manager = GameFileManager()
compile_job_manager = CompileJobManager(game_file_manager)


# FastAPI application
app = FastAPI()


# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:7677",
        "http://127.0.0.1:7677",
        "http://0.0.0.0:7677",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def home():
    return {"message": "Backend API is running"}


@app.post("/api/compile")
async def compile_map(request: Request):
    game = request.query_params.get("game")
    file_name = request.query_params.get("fileName")

    body = await request.body()

    job_response = compile_job_manager.create_compile_job(
        body, game, file_name
    )

    if not job_response.get("success", True):
        raise HTTPException(status_code=400, detail=job_response)

    map_file_path = job_response.get("mapFilePath")

    compile_job = compile_job_manager.run_map_compile(
        map_file_path, game
    )

    if not compile_job.get("success", False):
        raise HTTPException(status_code=400, detail=job_response)

    return job_response


@app.get("/api/bsp/{job_id}")
async def get_bsp(job_id: str):
    bsp_path, bsp_name = compile_job_manager.get_bsp(job_id)

    return FileResponse(
        path=f"{bsp_path}/{bsp_name}",
        filename=bsp_name,
        media_type="application/octet-stream"
    )


@app.get("/api/compile/{job_id}")
async def get_compile_job(job_id: str):
    job_details = compile_job_manager.get_compile_job(job_id)

    if not job_details:
        raise HTTPException(
            status_code=404,
            detail={"success": False, "error": "Job not found"}
        )

    return job_details


@app.delete("/api/compile/{job_id}")
async def cancel_compile_job(job_id: str):
    cancel_status = compile_job_manager.cancel_compile_job(job_id)

    if cancel_status is not True:
        raise HTTPException(
            status_code=500,
            detail={"success": False}
        )

    return {"success": cancel_status}


@app.post("/api/resolve-files")
async def get_directory(request: Request):
    body = await request.body()
    files = set(json.loads(body))

    game = request.query_params.get("game")

    files_exist = game_file_manager.get_game_files_not_in_directory(
        files, game
    )

    return list(files_exist) if isinstance(files_exist, set) else files_exist


@app.post("/api/upload-file")
async def upload_file(request: Request):
    body = await request.body()

    game = request.query_params.get("game")
    file_path = request.query_params.get("filePath")

    files_exist = game_file_manager.upload_file(
        body, game, file_path
    )

    return files_exist


@app.get("/api/config")
async def get_config():
    return game_file_manager.get_config()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=7676,
        reload=True
    )