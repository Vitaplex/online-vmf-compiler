import glob
import json
import os
import base64
import requests
import vpk

def try_connect_endpoint(endpoint):
    try:
        requests.get(endpoint, timeout=1)
        return True
    except:
        return False

def get_configured_directories():
    config_path = try_get_local_config_override_path("config.json") or try_get_path("config.json") or try_get_path("./backend/config.json")
    if config_path is None:
        raise FileNotFoundError("Config file not found")
    
    print("Config path: " + config_path)
    with open(config_path, "r") as config_file:
        content = config_file.read()
        config = json.loads(content)
        return config

# CLUSTER-specific - get the local config.json override
# If a cluster node uses mounted filesystem for the game files
# whilst ALSO having the application itself mounted (therfore sharing the config.json) 
# the node can reference the mounted path exclusively using the config.json override  
# The folder is assumed to be at /<os-root>/OVMFC/config.json
def try_get_local_config_override_path(path):
    config_path = os.path.join(get_os_root(), "OVMFC", path)
    override_path = try_get_path(config_path)
    if override_path:
        print(f"CLUSTER! Found config override at {config_path}")
        return override_path
    print("No config override found")

def get_os_root() -> str:
    if  os.name == "nt":
        # Returns 'C:' by default, append separator to get 'C:\\'
        system_drive = os.environ.get("SystemDrive", "C:")
        return system_drive + os.sep
    else:
        return "/"


def try_get_path(path):
    if os.path.exists(path):
        return os.path.abspath(path)
    return None

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

    print(f"Cached: {len(return_files)} filepaths")
    
    return return_files

def index(index, array):
    if array is not None and len(array) > 0 and len(array) - 1 >= index:
        return array[index]

def get_globby_file_path(path, name):
    globbed_path = index(0, glob.glob(os.path.join(path, name)))
    if globbed_path is None: return
    with open(globbed_path, "r") as f:
        return {"path": globbed_path, "content": f.read()}

def error(message):
    return {"success": False, "message": message }

def b64_encode_str(input):
    if input == None or input == "None" or input != str(input) : return None
    return base64.b64encode(input.encode("ascii")).decode("ascii")

def b64_decode_str(input):
    if input == None or input == "None" or input != str(input): return None
    return base64.b64decode(input.encode("ascii")).decode("ascii")