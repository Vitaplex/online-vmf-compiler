import os
import vpk
import glob
import concurrent.futures
import time
from helpers import *

DIRECTORIES = get_configured_directories()
VPK_FILES = get_vpk_files_for_all_directories(DIRECTORIES)

class VmfCompilerWrapper:
    def __init__(self):
        log()

    def get_game_files_not_in_directory(self, files, name):
        game = [dir for dir in DIRECTORIES if dir.get('name') == name][0]
        name = game.get('name')
        path = game.get('path')
        gameDir = game.get('assetDir')

        vpk_for_game = [vpk for vpk  in VPK_FILES if vpk.get(name) != None][0].get(name)

        path_game_dir = os.path.join(path,gameDir)
        files_not_in_local_dirs = get_game_files(path_game_dir, vpk_for_game, files)
        
        return files_not_in_local_dirs

    def get_config(self):
        return DIRECTORIES

def get_game_files(path, vpks, files):
    used_existing_files = []
    for file in files:
        if "whitegaragedoor" in file:
            pass

        normalized_filename = normalize_filename(file)
        full_path = resolve_files(os.path.join(path, normalized_filename))
        exists_in_folders = len(full_path) > 0
        exists_in_vpk = file in vpks or normalized_filename in vpks
        exists = exists_in_folders or exists_in_vpk

        # We only care about the files that don't exist
        if not exists:
            used_existing_files.append(file)

    return used_existing_files

def resolve_files(path):
    glob_path = os.path.join(path)
    res1 = glob.glob(glob_path ,recursive=True) 

    return res1

def normalize_filename(file:str):
    if file.startswith("materials"):
        file += ".vmt" if not file.endswith(".vmt") else ""
        file = file.lower()
    elif file.startswith("models"):
        file = file.lower()
    return file

def log():
    print()
    print("Configured directories")
    print("======================")
    for item in DIRECTORIES:
        name = item.get("name")
        path = item.get("path")
        print("Name: " + name + "\nL Path: " + path)

    print()
