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

    def test_running_jobs_report_only_active_job_directories(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            job_dir = root / "assets" / "mapsrc" / "active-job"
            job_dir.mkdir(parents=True)
            (job_dir / "runfile").touch()
            (job_dir / "owner").write_text(
                self.backend.compile_job_service.node_id, encoding="utf-8"
            )
            (job_dir / "test.vmf").write_text("world {}", encoding="utf-8")
            finished_dir = job_dir.parent / "finished-job"
            finished_dir.mkdir()
            (finished_dir / "finished.vmf").touch()
            config = [{
                "name": "Test Game", "path": temp,
                "assetDir": "assets", "sourceVmfs": "mapsrc",
            }]
            with (
                patch.object(self.backend.game_file_manager, "get_config", return_value=config),
                TestClient(self.backend.app) as client,
            ):
                response = client.get("/api/running-jobs")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json(), [{
                    "jobId": "active-job", "game": "Test Game", "fileName": "test.vmf",
                }])
                self.assertEqual(client.get("/api/jobs-count").json(), 1)

    def test_shared_storage_records_owner_and_blocks_foreign_or_unknown_cancellation(self):
        service_module = sys.modules[self.backend.CompileJobService.__module__]
        with tempfile.TemporaryDirectory() as temp:
            config = {
                "name": "Shared Game", "path": temp,
                "assetDir": "assets", "sourceVmfs": "mapsrc",
            }
            owner = self.backend.CompileJobService(self.backend.game_file_manager)
            reader = self.backend.CompileJobService(self.backend.game_file_manager)
            owner.node_id = "owner-node"
            reader.node_id = "reader-node"
            with (
                patch.object(self.backend.game_file_manager, "get_config", return_value=[config]),
                patch.object(self.backend.game_file_manager, "get_directory", return_value=config),
            ):
                created = owner.create_compile_job(b"world {}", "Shared Game", "shared.vmf")
                self.assertTrue(created["success"])
                job_id = created["jobId"]
                job_dir = Path(created["mapFilePath"]).parent
                (job_dir / "runfile").touch()
                self.assertEqual((job_dir / "owner").read_text(encoding="utf-8"), "owner-node")
                self.assertTrue(owner.get_compile_job(job_id)["isOwner"])
                self.assertFalse(reader.get_compile_job(job_id)["isOwner"])
                self.assertEqual(reader.get_compile_job(job_id)["ownerNode"], "owner-node")
                self.assertEqual(len(owner.get_running_job_details()), 1)
                self.assertEqual(reader.get_running_job_details(), [])
                with patch.object(service_module, "try_get_running_process", return_value=[]) as processes:
                    self.assertTrue(owner.cancel_compile_job(job_id))
                    processes.assert_called_once_with([])

                services = {"owner": owner, "reader": reader}
                nodes = [
                    {"name": name, "address": f"http://{name}", "weight": 1}
                    for name in services
                ]
                async_client = httpx.AsyncClient

                def backend_response(request):
                    service = services[request.url.host]
                    if request.url.path == "/api/running-jobs":
                        return httpx.Response(200, json=service.get_running_job_details())
                    self.assertEqual(request.url.path, "/api/jobs-count")
                    count = sum(len(game["runningJobs"]) for game in service.get_running_jobs())
                    return httpx.Response(200, json=count)

                transport = httpx.MockTransport(backend_response)
                with (
                    patch.object(self.loadbalancer.loadbalancer_service, "nodes", nodes),
                    patch.object(
                        self.loadbalancer.httpx, "AsyncClient",
                        side_effect=lambda **kwargs: async_client(transport=transport, **kwargs),
                    ),
                    TestClient(self.loadbalancer.app) as client,
                ):
                    stats = client.get("/api/stats").json()
                    self.assertEqual(stats["totalRunningJobs"], 1)
                    self.assertEqual([node["jobCount"] for node in stats["nodes"]], [1, 0])
                    self.assertEqual(client.get("/api/jobs-count").text, "1")

                with (
                    patch.object(self.backend, "compile_job_service", reader),
                    patch.object(service_module, "try_get_running_process") as processes,
                    TestClient(self.backend.app) as client,
                ):
                    response = client.delete(f"/api/compile/{job_id}")
                    self.assertEqual(response.status_code, 409)
                    processes.assert_not_called()
                    self.assertEqual(client.get("/api/jobs-count").json(), 0)

                restarted = self.backend.CompileJobService(self.backend.game_file_manager)
                restarted.node_id = owner.node_id
                self.assertTrue(restarted.get_compile_job(job_id)["isOwner"])
                self.assertEqual(len(restarted.get_running_job_details()), 1)

                (job_dir / "owner").unlink()
                self.assertTrue(reader.get_compile_job(job_id)["success"])
                self.assertIsNone(reader.get_compile_job(job_id)["ownerNode"])
                with (
                    patch.object(self.backend, "compile_job_service", reader),
                    patch.object(service_module, "try_get_running_process") as processes,
                    TestClient(self.backend.app) as client,
                ):
                    self.assertEqual(client.delete(f"/api/compile/{job_id}").status_code, 409)
                    self.assertEqual(client.delete("/api/compile/not-found").status_code, 404)
                    processes.assert_not_called()

    def test_shared_job_routes_to_owner_and_reads_survive_owner_outage(self):
        nodes = [
            {"name": name, "address": f"http://{name}", "weight": 1}
            for name in ("reader", "owner")
        ]
        async_client = httpx.AsyncClient
        forwarded = []
        offline = False

        def backend_response(request):
            if offline and request.url.host == "owner":
                raise httpx.ConnectError("Owner offline", request=request)
            forwarded.append((request.method, request.url.host, request.url.path))
            if request.method == "DELETE":
                self.assertEqual(request.url.host, "owner")
                return httpx.Response(200, json={"success": True})
            if request.url.path.startswith("/api/bsp/"):
                return httpx.Response(200, content=b"compiled bsp")
            return httpx.Response(200, json={
                "success": True, "statuses": [], "log": None,
                "ownerNode": "owner-host", "isOwner": request.url.host == "owner",
            })

        transport = httpx.MockTransport(backend_response)
        with (
            patch.object(self.loadbalancer.loadbalancer_service, "nodes", nodes),
            patch.object(
                self.loadbalancer.httpx, "AsyncClient",
                side_effect=lambda **kwargs: async_client(transport=transport, **kwargs),
            ),
            TestClient(self.loadbalancer.app) as client,
        ):
            for method, path in (
                ("GET", "/api/compile/shared-job"),
                ("GET", "/api/bsp/shared-job"),
                ("DELETE", "/api/compile/shared-job"),
            ):
                with self.subTest(method=method, path=path):
                    response = client.request(method, path)
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response.headers["X-Served-By"], "owner")
            offline = True
            with self.assertLogs(self.node_service.__name__, level="WARNING"):
                response = client.get("/api/compile/shared-job")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.headers["X-Served-By"], "reader")
                self.assertEqual(client.get("/api/bsp/shared-job").content, b"compiled bsp")
                response = client.delete("/api/compile/shared-job")
            self.assertEqual(response.status_code, 409)
            self.assertIn("owning backend is unavailable", response.json()["detail"])
            self.assertNotIn(("DELETE", "reader", "/api/compile/shared-job"), forwarded)

    def test_legacy_shared_job_reads_succeed_but_unverified_cancellation_is_rejected(self):
        nodes = [
            {"name": name, "address": f"http://{name}", "weight": 1}
            for name in ("first", "second")
        ]
        async_client = httpx.AsyncClient
        details = {"success": True, "statuses": [], "log": None}
        transport = httpx.MockTransport(lambda request: httpx.Response(200, json=details))
        with (
            patch.object(self.loadbalancer.loadbalancer_service, "nodes", nodes),
            patch.object(
                self.loadbalancer.httpx, "AsyncClient",
                side_effect=lambda **kwargs: async_client(transport=transport, **kwargs),
            ),
            TestClient(self.loadbalancer.app) as client,
        ):
            response = client.get("/api/compile/legacy-job")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers["X-Served-By"], "first")
            self.assertEqual(client.delete("/api/compile/legacy-job").status_code, 409)

    def test_conflicting_owner_claims_return_explicit_conflict(self):
        nodes = [
            {"name": name, "address": f"http://{name}", "weight": 1}
            for name in ("first", "second")
        ]
        async_client = httpx.AsyncClient
        transport = httpx.MockTransport(
            lambda request: httpx.Response(200, json={"success": True, "isOwner": True})
        )
        with (
            patch.object(self.loadbalancer.loadbalancer_service, "nodes", nodes),
            patch.object(
                self.loadbalancer.httpx, "AsyncClient",
                side_effect=lambda **kwargs: async_client(transport=transport, **kwargs),
            ),
            TestClient(self.loadbalancer.app) as client,
        ):
            response = client.delete("/api/compile/job")
            self.assertEqual(response.status_code, 409)
            self.assertIn("claim ownership", response.json()["detail"])

    def test_statistics_include_running_idle_and_unavailable_nodes(self):
        nodes = [
            {"name": name, "address": f"http://{name}", "weight": 2}
            for name in ("active", "idle", "offline", "invalid", "timeout", "error")
        ]
        jobs = [{"jobId": "test-job", "game": "Test Game", "fileName": "test.vmf"}]
        async_client = httpx.AsyncClient

        def backend_response(request):
            self.assertEqual(request.url.path, "/api/running-jobs")
            host = request.url.host
            if host == "offline":
                raise httpx.ConnectError("Node offline", request=request)
            if host == "timeout":
                raise httpx.ReadTimeout("Node timed out", request=request)
            if host == "error":
                return httpx.Response(500)
            if host == "invalid":
                return httpx.Response(200, json=[{"wrong": "shape"}])
            return httpx.Response(200, json=jobs if host == "active" else [])

        transport = httpx.MockTransport(backend_response)
        with (
            patch.object(self.loadbalancer.loadbalancer_service, "nodes", nodes),
            patch.object(
                self.loadbalancer.httpx, "AsyncClient",
                side_effect=lambda **kwargs: async_client(transport=transport, **kwargs),
            ),
            TestClient(self.loadbalancer.app) as client,
        ):
            with self.assertLogs(self.loadbalancer.__name__, level="WARNING"):
                response = client.get("/api/stats", headers={"X-Preferred-Node": "idle"})

        self.assertEqual(response.status_code, 200)
        stats = response.json()
        self.assertEqual(stats["totalRunningJobs"], 1)
        self.assertEqual(len(stats["nodes"]), len(nodes))
        self.assertEqual(stats["nodes"][0]["runningJobs"], jobs)
        self.assertEqual(stats["nodes"][0]["jobCount"], 1)
        self.assertEqual(stats["nodes"][1]["runningJobs"], [])
        self.assertEqual(stats["nodes"][1]["jobCount"], 0)
        for node in stats["nodes"][2:]:
            self.assertFalse(node["online"])
            self.assertIsNone(node["runningJobs"])
            self.assertIsNone(node["jobCount"])
            self.assertTrue(node["error"])

    def test_statistics_without_nodes(self):
        with (
            patch.object(self.loadbalancer.loadbalancer_service, "nodes", []),
            TestClient(self.loadbalancer.app) as client,
        ):
            self.assertEqual(
                client.get("/api/stats").json(), {"nodes": [], "totalRunningJobs": 0}
            )

    def test_frontend_serves_statistics_page_and_proxies_statistics(self):
        upstream = requests.Response()
        upstream.status_code = 200
        upstream._content = b'{"nodes": [], "totalRunningJobs": 0}'
        upstream.headers["Content-Type"] = "application/json"
        with TestClient(self.frontend.app) as client:
            page = client.get("/stats.html")
            self.assertEqual(page.status_code, 200)
            self.assertIn('/static/js/stats.js', page.text)
            self.assertIn('/static/css/style.css', page.text)
            with patch.object(self.frontend.requests, "request", return_value=upstream) as forward:
                response = client.get("/api/stats")
            self.assertEqual(response.json(), {"nodes": [], "totalRunningJobs": 0})
            self.assertEqual(forward.call_args.kwargs["url"], self.frontend.BACKEND_URL + "/api/stats")

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
