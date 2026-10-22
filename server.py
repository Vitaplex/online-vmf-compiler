import json

from flask import Flask, jsonify, render_template, abort, redirect, request
from vmf_compiler_wrapper import VmfCompilerWrapper

app = Flask(__name__)

vmf_compiler_wrapper = VmfCompilerWrapper()

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/api/compile", methods=["POST"])
def compile_map():
    content = request.data
    print(content)
    return ""

@app.route("/api/files", methods=["POST"])
def get_directory():
    files = set(json.loads(request.data))
    filesExist = vmf_compiler_wrapper.get_game_files_not_in_directory(files, request.args.get('game'))

    return filesExist  

@app.route("/api/config", methods=["GET"])
def get_config():
    return vmf_compiler_wrapper.get_config()

def main():
    if __name__ == "__main__":app.run(host="127.0.0.1", port=7676, debug=True)

main()