import glob
import json
import os

import vpk

def get_configured_directories():
    with open("./static/config.json", "r") as config_file:
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
