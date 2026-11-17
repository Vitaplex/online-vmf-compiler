import importlib.util
import json
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx
import requests
from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"


def load_server(name, directory):
    spec = importlib.util.spec_from_file_location(name, SRC / directory / "server.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ProxyRoutingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with patch.object(sys, "path", [
            str(SRC), str(SRC / "backend"), str(SRC / "loadbalancer"), *sys.path
        ]):
            import helpers
            import game_file_manager
            import loadbalancer_service

            cls.node_service = loadbalancer_service
            temp = tempfile.TemporaryDirectory()
            cls.addClassCleanup(temp.cleanup)
            config_path = Path(temp.name) / "config.json"
            config_path.write_text("[]", encoding="utf-8")
            with (
                patch.object(game_file_manager, "get_config_path", return_value=str(config_path)),
                patch.object(game_file_manager, "get_configured_directories", return_value=[]),
                patch.object(game_file_manager, "get_vpk_files_for_all_directories", return_value=[]),
                patch.object(helpers, "try_connect_endpoint", return_value=True),
                patch.object(loadbalancer_service, "get_config_path", return_value=str(config_path)),
                patch.object(loadbalancer_service, "parse_nodes_file", return_value=[]),
                patch.object(sys, "argv", ["test"]),
            ):
                cls.backend = load_server("test_backend_server", "backend")
                cls.loadbalancer = load_server("test_loadbalancer_server", "loadbalancer")
                cls.frontend = load_server("test_frontend_server", "frontend")

    def test_config_listeners_follow_application_lifespans(self):
        for server, service in (
            (self.backend, self.backend.game_file_manager),
            (self.loadbalancer, self.loadbalancer.loadbalancer_service),
        ):
            with self.subTest(server=server.__name__):
                with TestClient(server.app):
                    thread = service.config_watcher._thread
                    self.assertTrue(thread.is_alive())
                self.assertFalse(thread.is_alive())

    def test_running_services_reload_configuration_without_restarting(self):
        manager_module = sys.modules[self.backend.GameFileManager.__module__]
        with tempfile.TemporaryDirectory() as temp:
            nodes_path = Path(temp) / "nodes.json"
            config_path = Path(temp) / "config.json"
            nodes_path.write_text("[]", encoding="utf-8")
            config_path.write_text("[]", encoding="utf-8")
            with (
                patch.object(manager_module, "get_config_path", return_value=str(config_path)),
                patch.object(self.node_service, "get_config_path", return_value=str(nodes_path)),
            ):
                manager = self.backend.GameFileManager()
                balancer = self.loadbalancer.LoadBalancerService()

            nodes = [{"name": "reloaded", "address": "http://reloaded", "weight": 1}]
            config = [{"name": "Reloaded Game", "path": temp, "assetDir": "assets"}]
            async_client = httpx.AsyncClient
            transport = httpx.ASGITransport(app=self.backend.app)
            with (
                patch.object(self.backend, "game_file_manager", manager),
                patch.object(self.loadbalancer, "loadbalancer_service", balancer),
                patch.object(
                    self.loadbalancer.httpx, "AsyncClient",
                    side_effect=lambda **kwargs: async_client(transport=transport, **kwargs),
                ),
                TestClient(self.backend.app) as backend_client,
                TestClient(self.loadbalancer.app) as loadbalancer_client,
            ):
                nodes_path.write_text(json.dumps(nodes), encoding="utf-8")
                config_path.write_text(json.dumps(config), encoding="utf-8")
                deadline = time.monotonic() + 3
                while time.monotonic() < deadline:
                    if balancer.nodes == nodes and manager.get_config() == config:
                        break
                    time.sleep(0.02)

                self.assertEqual(balancer.nodes, nodes)
                self.assertEqual(backend_client.get("/api/config").json(), config)
                response = loadbalancer_client.get(
                    "/api/config", headers={"X-Preferred-Node": "reloaded"}
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json(), config)
                self.assertEqual(response.headers["X-Served-By"], "reloaded")

    def test_backend_job_status(self):
        details = {"success": True, "statuses": [], "log": None}
        with TestClient(self.backend.app) as client:
            for result, status_code in [(None, 404), (details, 200)]:
                with self.subTest(status_code=status_code):
                    with patch.object(
                        self.backend.compile_job_service, "get_compile_job",
                        return_value=result,
                    ):
                        response = client.get("/api/compile/job-id")
                    self.assertEqual(response.status_code, status_code)
                    self.assertEqual(
                        response.json(),
                        result or {"success": False, "error": "Job not found"},
                    )

    def test_loadbalancer_finds_only_the_owning_node(self):
        nodes = [
            {"name": "owner", "address": "http://owner", "weight": 1},
            {"name": "other", "address": "http://other", "weight": 1},
        ]
        details = {"success": True, "statuses": [], "log": None}
        async_client = httpx.AsyncClient

        def backend_response(request):
            if request.url.host == "owner":
                return httpx.Response(200, json=details)
            return httpx.Response(404, json={"success": False, "error": "Job not found"})

        transport = httpx.MockTransport(backend_response)
        with (
            patch.object(self.loadbalancer.loadbalancer_service, "nodes", nodes),
            patch.object(
                self.loadbalancer.httpx, "AsyncClient",
                side_effect=lambda **kwargs: async_client(transport=transport, **kwargs),
            ),
            TestClient(self.loadbalancer.app) as client,
        ):
            response = client.get("/api/compile/job-id")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), details)
        self.assertEqual(response.headers["X-Served-By"], "owner")

    def test_loadbalancer_returns_404_for_a_job_missing_on_all_nodes(self):
        nodes = [
            {"name": name, "address": f"http://{name}", "weight": 1}
            for name in ("first", "second")
        ]
        async_client = httpx.AsyncClient
        transport = httpx.MockTransport(
            lambda request: httpx.Response(
                404, json={"success": False, "error": "Job not found"}
            )
        )
        with (
            patch.object(self.loadbalancer.loadbalancer_service, "nodes", nodes),
            patch.object(
                self.loadbalancer.httpx, "AsyncClient",
                side_effect=lambda **kwargs: async_client(transport=transport, **kwargs),
            ),
            TestClient(self.loadbalancer.app) as client,
        ):
            response = client.get("/api/compile/missing-job")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.json()["detail"], "Job missing-job not found on any backend"
        )

    def test_compile_returns_503_when_no_backend_is_available(self):
        offline_node = {"name": "offline", "address": "http://offline", "weight": 1}
        with TestClient(self.loadbalancer.app) as client:
            for nodes in ([], [offline_node]):
                with (
                    self.subTest(nodes=nodes),
                    patch.object(self.loadbalancer.loadbalancer_service, "nodes", nodes),
                    patch.object(
                        self.node_service.requests, "get",
                        side_effect=requests.ConnectionError("Backend offline"),
                    ),
                ):
                    response = client.post(
                        "/api/compile?game=test&fileName=test.vmf", content=b"vmf"
                    )

                self.assertEqual(response.status_code, 503)
                self.assertEqual(response.json()["detail"], "No available backend nodes")

    def test_compile_routes_with_and_without_a_preferred_backend(self):
        node = {"name": "preferred", "address": "http://preferred", "weight": 1}
        async_client = httpx.AsyncClient
        forwarded = []
        job_count = requests.Response()
        job_count.status_code = 200
        job_count._content = b"0"

        def backend_response(request):
            forwarded.append(request)
            return httpx.Response(200, json={"success": True, "jobId": "new-job"})

        transport = httpx.MockTransport(backend_response)
        with (
            patch.object(self.loadbalancer.loadbalancer_service, "nodes", [node]),
            patch.object(
                self.loadbalancer.httpx, "AsyncClient",
                side_effect=lambda **kwargs: async_client(transport=transport, **kwargs),
            ),
            patch.object(self.node_service.requests, "get", return_value=job_count),
            TestClient(self.loadbalancer.app) as client,
        ):
            for headers in ({}, {"X-Preferred-Node": "preferred"}):
                with self.subTest(headers=headers):
                    response = client.post(
                        "/api/compile?game=test&fileName=test.vmf",
                        content=b"vmf",
                        headers=headers,
                    )

                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response.json()["jobId"], "new-job")
                    self.assertEqual(response.headers["X-Served-By"], "preferred")
                    self.assertEqual(
                        str(forwarded[-1].url),
                        "http://preferred/api/compile?game=test&fileName=test.vmf",
                    )
                    self.assertEqual(forwarded[-1].content, b"vmf")

    def test_frontend_preserves_affinity_headers_and_request_content(self):
        body = b"\x00vmf data\xff"
        with TestClient(self.frontend.app) as client:
            for status_code in (200, 400):
                with self.subTest(status_code=status_code):
                    upstream = requests.Response()
                    upstream.status_code = status_code
                    upstream._content = b'{"success": true}'
                    upstream.headers.update({
                        "Content-Type": "application/json",
                        "X-Served-By": "selected-node",
                    })
                    with patch.object(
                        self.frontend.requests, "request", return_value=upstream
                    ) as forward:
                        response = client.post(
                            "/api/compile?game=test&fileName=test.vmf",
                            content=body,
                            headers={
                                "Content-Type": "application/octet-stream",
                                "X-Preferred-Node": "selected-node",
                            },
                        )

                    self.assertEqual(response.status_code, status_code)
                    self.assertEqual(response.content, upstream.content)
                    self.assertEqual(response.headers["X-Served-By"], "selected-node")
                    self.assertEqual(response.headers["Content-Type"], "application/json")
                    kwargs = forward.call_args.kwargs
                    self.assertEqual(kwargs["method"], "POST")
                    self.assertEqual(kwargs["data"], body)
                    self.assertEqual(kwargs["params"]["game"], "test")
                    self.assertEqual(kwargs["params"]["fileName"], "test.vmf")
                    self.assertEqual(kwargs["headers"], {
                        "content-type": "application/octet-stream",
                        "x-preferred-node": "selected-node",
                    })


if __name__ == "__main__":
    unittest.main()
