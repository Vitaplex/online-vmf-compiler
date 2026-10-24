import os
from pathlib import Path
from uuid import uuid4

from game_file_manager import GameFileManager


class CompileJobManager:
    def __init__(self, gamefilemanager:GameFileManager):
        self.game_file_manager = gamefilemanager

    def compile_map(self, vmf_file, name):
        job_id = str(uuid4())
        print("Compiling vmf-file. Job-ID: " + job_id)
        game_config = self.game_file_manager.get_directory(name)

        game_path = game_config.get('path')
        game_dir = game_config.get('assetDir')

        # Create a folder for the job - to put the vmf inside (will contain the .log file aswell, neatly providing easy fetching)
        path = os.path.join(game_path, game_dir, "mapsrc", job_id)
        Path(path).mkdir(parents=True, exist_ok=True)

