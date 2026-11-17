import asyncio
import random
import logging
import os,sys,inspect
from random import randint

import httpx

current_dir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from helpers import *
from config_watcher import ConfigFileWatcher


class JobRoutingError(Exception):
    pass


class LoadBalancerService:
    def __init__(self):
        self.config_path = get_config_path("nodes.json", os.path.join("loadbalancer", "nodes.json"))
        self.config_watcher = ConfigFileWatcher(self.config_path, self.reload_config)
        self.reload_config()

    def reload_config(self):
        self.nodes = parse_nodes_file(self.config_path)

    def resolve_node(self, prefered_node_name):
        if (node := self.get_node_by_name(prefered_node_name)) is not None:
            return node
            
        nodes = self.nodes
        weights_resolved = [resolve_weights(node, nodes)for node in nodes]
        nodes_with_jobs = [get_node_job_count(node)for node in weights_resolved]
        fit_node = resolve_best_node(nodes_with_jobs)

        return fit_node

    def get_node_by_name(self, node_name):
        if not node_name:
            return None
        return next((node for node in self.nodes if node.get("name", "").lower() == node_name.lower()), None)      
      
    async def resolve_job_node(self, job_id, require_owner=False):
        async with httpx.AsyncClient(timeout=5) as client:
            async def check_node(node):
                try:
                    url = f"{node['address'].rstrip('/')}/api/compile/{job_id}"

                    response = await client.get(url)

                    if response.status_code == 404:
                        return None

                    response.raise_for_status()
                    details = response.json()
                    if not isinstance(details, dict) or details.get("success") is not True:
                        return None
                    return node, details.get("isOwner") is True

                except (httpx.HTTPError, ValueError) as error:
                    logging.getLogger(__name__).warning(
                        "Could not look up job %s on %s: %s", job_id, node["address"], error
                    )
                    return None

            results = await asyncio.gather(
                *(check_node(node) for node in self.nodes)
            )

        matches = [result for result in results if result is not None]
        owners = [node for node, is_owner in matches if is_owner]

        if len(owners) > 1:
            raise JobRoutingError(f"Multiple backends claim ownership of job {job_id}")
        if owners:
            return owners[0]
        if require_owner and matches:
            raise JobRoutingError(
                f"Cannot safely cancel job {job_id}: its owning backend is unavailable "
                "or ownership is unknown"
            )

        return matches[0][0] if matches else None
def parse_nodes_file(filename):
    nodes_path = filename if os.path.isabs(filename) else get_config_path(
        filename, os.path.join("loadbalancer", filename)
    )
    return read_json_config(nodes_path)

def resolve_weights(node, all_nodes):
    total_weight = sum(nd.get("weight", 0) or 0 for nd in all_nodes)

    if total_weight <= 0:
        raise ValueError("Total node weight must be greater than zero")
    node_weight = node.get("weight", 0) or 0
    node["percentage"] = node_weight / total_weight

    return node

def get_node_job_count(node):
    try:
        address = f"{node.get('address')}/api/jobs-count"
        response = requests.get(address, timeout=5)
        response.raise_for_status()

        node["jobs"] = int(response.text)
        return node

    except Exception as ex:
        print(f"Failed to get job count for {node.get('address')}: {ex}")
        node["jobs"] = None
        return node
    
def resolve_best_node(nodes):
    available_nodes = [
        node for node in nodes
        if node.get("jobs") is not None
        and node.get("weight", 0) > 0
    ]

    if not available_nodes:
        return None

    return random.choices(
        available_nodes,
        weights=[node["weight"] for node in available_nodes],
        k=1
    )[0]
