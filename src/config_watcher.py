import logging
from pathlib import Path
from threading import Event, Thread
from typing import Callable


logger = logging.getLogger(__name__)


class ConfigFileWatcher:
    def __init__(self, path: str, reload_config: Callable[[], None], interval: float = 1):
        self.path = Path(path)
        self.reload_config = reload_config
        self.interval = interval
        self._stop = Event()
        self._thread: Thread | None = None
        self._signature = self._get_signature()

    def _get_signature(self):
        try:
            stat = self.path.stat()
        except FileNotFoundError:
            return None
        return stat.st_mtime_ns, stat.st_size, stat.st_ino

    def check_for_changes(self):
        try:
            signature = self._get_signature()
            if signature == self._signature:
                return
            self._signature = signature
            self.reload_config()
        except (OSError, ValueError, TypeError, KeyError):
            logger.exception(
                "Could not reload %s; keeping the last valid configuration", self.path
            )
        else:
            logger.info("Reloaded configuration from %s", self.path)

    def start(self):
        if self._thread is not None:
            return
        self._stop.clear()
        self._thread = Thread(
            target=self._run, name=f"config-watcher:{self.path.name}", daemon=True
        )
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread is not None:
            self._thread.join()
            self._thread = None

    def _run(self):
        while not self._stop.wait(self.interval):
            self.check_for_changes()
