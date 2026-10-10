import os
import vpk
import glob
import concurrent.futures
import time
from helpers import *

DIRECTORIES = get_configured_directories()
class VmfCompilerWrapper:
    def __init__(self):
        # TESTing
        log()

    def get_materials_models_in_directory(self, name):
        game = [dir for dir in DIRECTORIES if dir.get('name') == name][0]
        path = game.get('path')

        vpks = get_vpk_files(path)
        files = get_game_files(path)
        
        return files

    def get_config(self):
        return DIRECTORIES

def get_vpk_files(path):    
    vpks = glob.glob(f"{path}/*/*_dir.vpk", recursive=True)
    
    print(len(vpks))

    #TODO: read all _dir VPKs and return array of file paths for them aswell

def get_game_files(path):
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [
            executor.submit(get_recursive_files,path, "materials"),
            executor.submit(get_recursive_files, path, "models"),
            executor.submit(get_recursive_files, path, "scripts"),
            executor.submit(get_recursive_files, path, "sound")
        ]

        return [future.result() for future in futures]

def get_recursive_files(path, folder) -> set:
    return set(glob.glob(f"{path}/*/{folder}/**", recursive=True))

def log():
    print()
    print("Configured directories")
    print("======================")
    for item in DIRECTORIES:
        name = item.get("name")
        path = item.get("path")
        print("Name: " + name + "\nL Path: " + path)

    print()
