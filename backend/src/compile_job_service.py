import glob
import os
import signal
import subprocess
import background
import psutil
import time
from pathlib import Path
from uuid import uuid4
from datetime import datetime, timezone
from helpers import index, get_globby_file_path, error

from game_file_manager import GameFileManager


class CompileJobService:
    def __init__(self, gamefilemanager:GameFileManager):
        self.game_file_manager = gamefilemanager

    def create_compile_job(self, vmf_file, name, file_name):
        game_config = self.game_file_manager.get_directory(name)

        if game_config is None: return error(f"Game {name} not found")

        game_path = game_config.get('path')
        game_dir = game_config.get('assetDir')

        if game_path is None: return error(f"Game path not specified for selected game {name}")
        if game_dir is None: return error(f"Game directory not specified for selected game {name}")

        job_id = str(uuid4())
        print("Creating compile job. Job-ID: " + job_id)
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

    def cancel_compile_job(self, job_id):
        job = self.get_compile_job(job_id)
        path = job.get("path")
        statuses = job.get("statuses", [])

        pids = [stat.get("pid") for stat in statuses]

        running_jobs = try_get_running_process(pids)

        while(len(running_jobs) > 0):
            try:
                for pid in running_jobs:
                    pid.terminate()
                    time.sleep(0.5)
                    # FIXME! ALERT - POSSIBLE JANK!? Run recursively to kill the following processes
                    self.cancel_compile_job(job_id) 
            except Exception as ex:
                break

        write_status_file(None, path, "terminated")

        return True


    def get_compile_job(self, job_id):
        job_filepath = self.get_files_for_job(job_id)
        if not job_filepath: return None

        log_file = get_globby_file_path(job_filepath, "*.log")
        status_file = get_globby_file_path(job_filepath, "status")

        if not log_file or not status_file:
            return None
        
        statuses = parse_status_file(status_file.get("content"))

        return {"path": job_filepath, "statuses": statuses, "log": log_file.get("content")}

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
    run_process(map_file_path, vbsp_path, "vbsp")

    bsp_path = os.path.splitext(map_file_path)[0] + ".bsp"
    run_process(bsp_path, vvis_path, "vvis")
    run_process(bsp_path, vrad_path, "vrad")
    write_status_file(None, map_file_path, "finished")

def run_process(map_file_path, process_path, tag):
    process = subprocess.Popen([process_path, map_file_path])
    write_status_file(process.pid, map_file_path, tag)
    process.wait()

# The status file is used to keep track of the current status of the compile job
def write_status_file(pid, map_file_path, status):
    pid = str(pid)
    sep = "|"
    date = datetime.now(timezone.utc).strftime('%d/%m/%YT%H:%M:%S%z')

    use_map_file_directory = Path(map_file_path).parent

    is_map_file_directory = os.path.isdir(map_file_path)
    just_use_map_file_path = map_file_path

    # Python is an anglo-saxon-oriented programming language
    map_file_path = use_map_file_directory if is_map_file_directory is not True else just_use_map_file_path 
    
    with open(os.path.join(map_file_path, "status"), "a+") as f:
        f.write(f"{date}{sep}{status}{sep}{pid}\n")

def parse_status_file(status_file):
    status_lines = status_file.split("\n")
    lines = [line for line in status_lines if line is not None and line != ""]
    return [get_status_line(line) for line in lines]

def get_status_line(line:str):
    parts = line.split("|")
    return {
        "time": datetime.strptime(index(0,parts),"%d/%m/%YT%H:%M:%S%z"), 
        "status":index(1, parts).strip("\n"), 
        "pid": index(2, parts)
    }

def try_get_running_process(pids):
    active_pids = []
    for pid in pids:
        try:
            active_pids.append(psutil.Process(int(pid)))
        except Exception as ex:
            pass

    return active_pids