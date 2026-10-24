import json

from flask import Flask, jsonify, render_template, abort, redirect, request
from game_file_manager import GameFileManager
from compile_job_manager import CompileJobManager

# Dependencies
game_file_manager = GameFileManager()
compile_job_manager = CompileJobManager(game_file_manager)

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html") 

@app.route("/api/compile", methods=["POST"])
def compile_map():
    game = request.args.get('game')
    fileName = request.args.get('fileName')
    job_response = compile_job_manager.create_compile_job(request.data, game, fileName)
    
    if not job_response.get("success", True):
        return job_response, 400
    
    map_file_path = job_response.get("mapFilePath")
    compile_job = compile_job_manager.run_map_compile(map_file_path, game)
    
    return job_response, 200 if compile_job.get("success", False) else 400

@app.route("/api/compile/<job_id>", methods=["GET"])
def get_compile_job(job_id):
    job_details = compile_job_manager.get_compile_job(job_id)
    
    if not job_details:
        return { "success": False, "error": "Job not found" }, 404
    
    return job_details, 200

@app.route("/api/resolve-files", methods=["POST"])
def get_directory():
    files = set(json.loads(request.data))
    filesExist = game_file_manager.get_game_files_not_in_directory(files, request.args.get('game'))

    return filesExist  

@app.route("/api/upload-file", methods=["POST"])
def upload_file():
    filesExist = game_file_manager.upload_file(request.data, request.args.get('game'), request.args.get('filePath'))
    return filesExist

@app.route("/api/config", methods=["GET"])
def get_config():
    return game_file_manager.get_config()

def main():
    if __name__ == "__main__":
        # app.config['MAX_CONTENT_LENGTH'] = 16 * 1000 * 1000
        app.run(host="127.0.0.1", port=7676, debug=False)

main()