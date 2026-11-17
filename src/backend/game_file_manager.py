import os
import glob
import sys
import os,sys,inspect
from pathlib import Path

current_dir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from helpers import *
from config_watcher import ConfigFileWatcher

class GameFileManager:
    def __init__(self):
        self.config_path = get_config_path("config.json", os.path.join("backend", "config.json"))
        self.config_watcher = ConfigFileWatcher(self.config_path, self.reload_config)
        self.reload_config()

    def reload_config(self):
        directories = get_configured_directories(self.config_path)
        vpk_files = get_vpk_files_for_all_directories(directories)
        log(directories)
        self._configuration = directories, vpk_files

    def get_game_files_not_in_directory(self, files, name):
        directories, vpk_files = self._configuration
        game = index(0, [game for game in directories if game.get("name") == name])
        name = game.get('name')
        path = game.get('path')
        gameDir = game.get('assetDir')

        vpk_for_game = [vpk for vpk in vpk_files if vpk.get(name) != None][0].get(name)

        path_game_dir = os.path.join(path,gameDir)
        files_not_in_local_dirs = get_game_files(path_game_dir, vpk_for_game, files)
        
        return files_not_in_local_dirs
    
    def upload_file(self, data, name, file_path):
        game = self.get_directory(name)
        game_path = game.get('path')
        asset_dir = game.get('assetDir')
        asset_path_relative = os.path.join(asset_dir, str(Path(file_path))) # Cast to Path and then str to make the slashes go the right way, since the file_path is different if on Windows
        full_path = os.path.join(game_path, asset_path_relative)

        print("Creating file:" + full_path)
        # Create folders if not exist
        Path(full_path).parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(full_path, 'wb') as f:
                f.write(data)
            return { "success": True, "path": asset_path_relative }
        except Exception as ex:
            print(ex)
            return { "success": False, "error": ex }

    def get_config(self):
        return self._configuration[0]

    def get_directory(self, name):
        return index(0, [dir for dir in self.get_config() if dir.get('name') == name])

    

def get_game_files(path, vpks, files):
    used_existing_files = []
    for file in files:
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

def log(directories):
    print()
    print("Configured directories")
    print("======================")
    for item in directories:
        name = item.get("name")
        path = item.get("path")
        print("Name: " + name + "\nL Path: " + path)

    print()

