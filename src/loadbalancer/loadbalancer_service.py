import os,sys,inspect

current_dir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from helpers import *

class LoadBalancerService:
    def __init__(self):
        self.nodes = parse_nodes_file("nodes.json")
        pass

    def resolve_node():
        ...

def parse_nodes_file(filename):
    nodes_path = try_get_local_config_override_path(filename) or try_get_path(filename) or try_get_path("./backend/config.json")
    with open(nodes_path, "r") as f:
        content = f.read()
        return json.loads(content)