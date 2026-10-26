import glob
import os
import subprocess
import background
from pathlib import Path
from uuid import uuid4
from datetime import datetime, timezone
from helpers import index

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
        
        compile_map(vbsp_path, vvis_path, vrad_path, map_file_path)
        
        return { "success": True }

    def get_compile_job(self, job_id):
        job_files = self.get_files_for_job(job_id)
        if not job_files: return None

        log_file = index(0, glob.glob(os.path.join(job_files, "*.log")))

        status_file = index(0, glob.glob(os.path.join(job_files, "status")))
       
        if not log_file or not status_file:
            return None
        
        statuses = parse_status_file(status_file)

        with open(log_file, "r") as f:
                return {"statuses": statuses, "log": f.read()}

    def get_bsp(self, job_id):
        job_files = self.get_files_for_job(job_id)

        bsp_file = Path(index(0, glob.glob(os.path.join(job_files, "*.bsp"))))
        return (str(bsp_file.parent), str(bsp_file.name))


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
def compile_map(vbsp_path, vvis_path, vrad_path, map_file_path):
    write_status_file(map_file_path, "vbsp")
    subprocess.run([vbsp_path, map_file_path])

    bsp = os.path.splitext(map_file_path)[0] + ".bsp"
    write_status_file(map_file_path, "vvis")
    subprocess.run([vvis_path, bsp])
    write_status_file(map_file_path, "vrad")
    subprocess.run([vrad_path, bsp])
    write_status_file(map_file_path, "finished")

# The status file is used to keep track of the current status of the compile job
def write_status_file(map_file_path, status):
    with open(os.path.join(Path(map_file_path).parent, "status"), "a+") as f:
        f.write(datetime.now(timezone.utc).strftime("%d/%m/%YT%H:%M:%S%z") + "|" + status + "\n")

def parse_status_file(status_file):
    with open(status_file, "r") as s:
        content = s.readlines()
        return [get_status_line(line) for line in content if line is not None]

def get_status_line(line:str):
    parts = line.split("|")
    return {"time": datetime.strptime(parts[0],"%d/%m/%YT%H:%M:%S%z"), "status":parts[1].strip("\n")}