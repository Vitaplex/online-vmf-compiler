import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from threading import Event
from unittest.mock import patch


SRC = Path(__file__).resolve().parents[1] / "src"
with patch.object(sys, "path", [
    str(SRC), str(SRC / "backend"), str(SRC / "loadbalancer"), *sys.path
]):
    import config_watcher
    import game_file_manager
    import helpers
    import loadbalancer_service


class ConfigReloadTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.path = Path(temp.name) / "config.json"

    def write_config(self, value):
        self.path.write_text(json.dumps(value), encoding="utf-8")
        stat = self.path.stat()
        os.utime(self.path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000_000))

    def create_balancer(self, nodes):
        self.write_config(nodes)
        with patch.object(loadbalancer_service, "get_config_path", return_value=str(self.path)):
            return loadbalancer_service.LoadBalancerService()

    def create_manager(self, config):
        self.write_config(config)
        with patch.object(game_file_manager, "get_config_path", return_value=str(self.path)):
            return game_file_manager.GameFileManager()

    def test_listener_detects_file_edits_and_stops(self):
        self.write_config([])
        reloaded = Event()
        observed = []

        def reload_config():
            observed.append(helpers.read_json_config(self.path))
            reloaded.set()

        watcher = config_watcher.ConfigFileWatcher(str(self.path), reload_config, interval=0.01)
        watcher.start()
        thread = watcher._thread
        try:
            self.write_config([{"name": "new"}])
            self.assertTrue(reloaded.wait(3), "Configuration listener did not detect the edit")
            self.assertEqual(observed, [[{"name": "new"}]])
        finally:
            watcher.stop()
        self.assertFalse(thread.is_alive())

    def test_node_reload_detects_atomic_replacement_with_same_mtime_and_size(self):
        original = [{"name": "old", "address": "http://old", "weight": 1}]
        updated = [{"name": "new", "address": "http://new", "weight": 2}]
        service = self.create_balancer(original)
        stat = self.path.stat()
        replacement = self.path.with_name("replacement.json")
        replacement.write_text(json.dumps(updated), encoding="utf-8")
        os.utime(replacement, ns=(stat.st_atime_ns, stat.st_mtime_ns))
        self.assertEqual(replacement.stat().st_size, stat.st_size)
        replacement.replace(self.path)

        service.config_watcher.check_for_changes()

        self.assertIsNone(service.get_node_by_name("old"))
        self.assertEqual(service.resolve_node("new"), updated[0])

    def test_node_reload_keeps_valid_state_on_invalid_edits_and_recovers(self):
        original = [{"name": "old", "address": "http://old", "weight": 1}]
        service = self.create_balancer(original)

        for text in ('[{"name":', '{"not": "an array"}', '["not an object"]'):
            with self.subTest(text=text):
                self.path.write_text(text, encoding="utf-8")
                with self.assertLogs("config_watcher", level="ERROR"):
                    service.config_watcher.check_for_changes()
                self.assertEqual(service.nodes, original)

        updated = [{"name": "recovered", "address": "http://new", "weight": 3}]
        self.write_config(updated)
        service.config_watcher.check_for_changes()
        self.assertEqual(service.nodes, updated)

    def test_deleted_configuration_is_logged_and_reloaded_when_recreated(self):
        original = [{"name": "old", "address": "http://old", "weight": 1}]
        service = self.create_balancer(original)
        self.path.unlink()
        with self.assertLogs("config_watcher", level="ERROR"):
            service.config_watcher.check_for_changes()
        self.assertEqual(service.nodes, original)

        self.write_config([])
        service.config_watcher.check_for_changes()
        self.assertEqual(service.nodes, [])

    def test_unchanged_files_do_not_reparse(self):
        service = self.create_balancer([])
        with patch.object(loadbalancer_service, "parse_nodes_file") as parse:
            service.config_watcher.check_for_changes()
            parse.assert_not_called()

    def test_backend_reload_updates_game_paths_and_vpk_index_together(self):
        original = [{"name": "Old Game", "path": str(self.path.parent), "assetDir": "old"}]
        updated = [{"name": "New Game", "path": str(self.path.parent), "assetDir": "new"}]

        def index_vpks(config):
            return [{game["name"]: {game["assetDir"] + ".txt"}} for game in config]

        with patch.object(game_file_manager, "get_vpk_files_for_all_directories", side_effect=index_vpks):
            manager = self.create_manager(original)
            self.assertEqual(
                manager.get_game_files_not_in_directory({"old.txt", "new.txt"}, "Old Game"),
                ["new.txt"],
            )
            self.write_config(updated)
            manager.config_watcher.check_for_changes()

        self.assertEqual(manager.get_config(), updated)
        self.assertIsNone(manager.get_directory("Old Game"))
        self.assertEqual(manager.get_directory("New Game"), updated[0])
        self.assertEqual(
            manager.get_game_files_not_in_directory({"old.txt", "new.txt"}, "New Game"),
            ["old.txt"],
        )

    def test_backend_keeps_old_configuration_if_vpk_rebuild_fails(self):
        original = [{"name": "Old Game", "path": str(self.path.parent), "assetDir": "old"}]
        updated = [{"name": "New Game", "path": str(self.path.parent), "assetDir": "new"}]
        with patch.object(
            game_file_manager, "get_vpk_files_for_all_directories",
            return_value=[{"Old Game": {"old.txt"}}],
        ):
            manager = self.create_manager(original)

        self.write_config(updated)
        with (
            patch.object(
                game_file_manager, "get_vpk_files_for_all_directories",
                side_effect=OSError("VPK index unavailable"),
            ),
            self.assertLogs("config_watcher", level="ERROR"),
        ):
            manager.config_watcher.check_for_changes()
        self.assertEqual(manager.get_config(), original)
        self.assertEqual(manager.get_game_files_not_in_directory({"old.txt"}, "Old Game"), [])

    def test_both_services_watch_the_effective_override_path(self):
        self.write_config([])
        with patch.object(
            helpers, "try_get_local_config_override_path", return_value=str(self.path)
        ):
            for service in (
                loadbalancer_service.LoadBalancerService(),
                game_file_manager.GameFileManager(),
            ):
                with self.subTest(service=type(service).__name__):
                    self.assertEqual(service.config_watcher.path, self.path)


if __name__ == "__main__":
    unittest.main()
