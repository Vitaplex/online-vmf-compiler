import glob
import json
import os
import base64
import vpk

def get_configured_directories():
    with open("./config.json", "r") as config_file:
        content = config_file.read()
        config = json.loads(content)
        return config

def get_vpk_files_for_all_directories(configuration):
    vpk_dirs = []
    for entry in configuration:
        path = entry.get('path')
        name = entry.get('name')
        print(f"Caching .vpk directories for {name}")
        vpk_dirs.append({name: get_vpk_files(path)})
    return vpk_dirs

def get_vpk_files(path):    
    return_files = set()    
    vpks = glob.glob(os.path.join(path, "**", "*_dir.vpk"), recursive=True)
    for vpk_file in vpks:
        vpk_files = vpk.open(vpk_file)
        for vpk_file in vpk_files:
            return_files.add(vpk_file)
    return return_files

def index(index, array):
    if array is not None and len(array) > 0 and len(array) >= index:
        return array[index]

def get_globby_file_path(path, name):
    globbed_path = index(0, glob.glob(os.path.join(path, name)))
    if globbed_path is None: return
    with open(globbed_path, "r") as f:
        return {"path": globbed_path, "content": f.read()}

def error(message):
    return {"success": False, "message": message }

def b64_encode_str(input):
    if input != str(input): return None
    return base64.b64encode(input.encode("ascii")).decode("ascii")

def b64_decode_str(input):
    if input != str(input): return None
    return base64.b64decode(input.encode("ascii")).decode("ascii")