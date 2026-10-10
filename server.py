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

@app.route("/api/files", methods=["GET"])
def get_directory():
    entry = vmf_compiler_wrapper.get_materials_models_in_directory(request.args.get('game'))

    if entry is not None:
        return entry, 200  
    else:
        return None, 404

@app.route("/api/config", methods=["GET"])
def get_config():
    return vmf_compiler_wrapper.get_config()

if __name__ == "__main__":
     app.run(host="127.0.0.1", port=7676, debug=True)