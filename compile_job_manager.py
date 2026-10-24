import glob
import os
import subprocess
import background
from pathlib import Path
from uuid import uuid4

from game_file_manager import GameFileManager


class CompileJobManager:
    def __init__(self, gamefilemanager:GameFileManager):
        self.game_file_manager = gamefilemanager

    def create_compile_job(self, vmf_file, name, file_name):
        job_id = str(uuid4())
        print("Creating compile job. Job-ID: " + job_id)
        game_config = self.game_file_manager.get_directory(name)

        game_path = game_config.get('path')
        game_dir = game_config.get('assetDir')

        # Create a folder for the job - to put the vmf inside (will contain the .log file aswell, neatly providing easy fetching)
        full_path = os.path.join(game_path, game_dir, "mapsrc", job_id)
        Path(full_path).mkdir(parents=True, exist_ok=True)
        map_file_path = os.path.join(full_path, file_name) 
        
        try:
            with open(map_file_path, 'wb') as f:
                f.write(vmf_file)
            return { "success": True, "jobId": job_id, "mapFilePath": map_file_path }
        except Exception as ex:
            print(ex)
            return { "success": False, "error": str(ex) }
        
    def run_map_compile(self, map_file_path, name):
        game_config = self.game_file_manager.get_directory(name)
        compiler_path = os.path.join(game_config.get('path'), game_config.get('compilerPath'))
        vbsp_path = os.path.join(compiler_path, game_config.get('vbsp'))
        vvis_path = os.path.join(compiler_path, game_config.get('vvis'))
        vrad_path = os.path.join(compiler_path, game_config.get('vrad'))
        
        compile_map(vbsp_path, vvis_path, vrad_path, map_file_path, name)
        
        return { "success": True }

    def get_compile_job(self, job_id):
        job_files = self.get_files_for_job(job_id)
        log_file = glob.glob(os.path.join(job_files, "*.log"))[0] if job_files else None
       
        if not log_file:
            return None
        
        with open(log_file, 'r') as f:
            return f.read()

    def get_files_for_job(self, job_id):
        configs = self.game_file_manager.get_config()
        for config in configs:
            path = config.get('path')
            assetDir = config.get('assetDir')
            sourceVmfs = config.get('sourceVmfs')
            mapsrc = os.path.join(path, assetDir, sourceVmfs, job_id)
            if os.path.exists(mapsrc):
                return mapsrc

        
@background.task
def compile_map(vbsp_path, vvis_path, vrad_path, map_file_path, name):
    subprocess.run([vbsp_path, map_file_path])

    bsp = os.path.splitext(map_file_path)[0] + ".bsp"
    subprocess.run([vvis_path, bsp])
    subprocess.run([vrad_path, bsp])
