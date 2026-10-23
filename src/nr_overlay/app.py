"""Wires the save watcher, the session tracker, the overlay server and the tray icon."""

import ctypes
import json
import logging
import os
import sys
import threading
import time
from collections.abc import Callable
from logging.handlers import RotatingFileHandler
from pathlib import Path

from nr_overlay.i18n import normalize_language, tr
from nr_overlay.save_reader import RatingSnapshot, SaveFormatError, find_save_files, read_rating
from nr_overlay.server import OverlayServer
from nr_overlay.session import SessionTracker
from nr_overlay.tray import run_tray

APP_NAME = "NightreignRatingOverlay"
DATA_DIR = Path(os.environ.get("APPDATA", Path.home())) / APP_NAME
CONFIG_PATH = DATA_DIR / "config.json"
DEFAULT_CONFIG = {"port": 8765, "save_path": None, "session_max_age_hours": 12, "language": "en"}
POLL_INTERVAL = 1.5

logger = logging.getLogger(__name__)


def load_config() -> dict:
    config = dict(DEFAULT_CONFIG)
    try:
        config.update(json.loads(CONFIG_PATH.read_text(encoding="utf-8")))
    except FileNotFoundError:
        save_config(config)
    except (OSError, ValueError) as e:
        logger.warning("Using default config, could not read %s: %s", CONFIG_PATH, e)
    config["language"] = normalize_language(config.get("language"))
    return config


def save_config(config: dict) -> None:
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
    except OSError as e:
        logger.warning("Could not save config to %s: %s", CONFIG_PATH, e)


class RatingApp:
    def __init__(self, config: dict):
        self._config = config
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._snapshot: RatingSnapshot | None = None
        self._save_path: Path | None = None
        self._error: str | None = None
        self._updated_at: float | None = None
        self._listeners: list[Callable[[], None]] = []
        self.session = SessionTracker(DATA_DIR / "session.json", config["session_max_age_hours"])
        self.server = OverlayServer(int(config["port"]), self.state)

    def on_change(self, listener: Callable[[], None]) -> None:
        self._listeners.append(listener)

    def _notify(self) -> None:
        for listener in self._listeners:
            try:
                listener()
            except Exception:
                logger.exception("State listener failed")

    @property
    def language(self) -> str:
        return self._config["language"]

    def set_language(self, lang: str) -> None:
        self._config["language"] = normalize_language(lang)
        save_config(self._config)
        self._notify()

    @property
    def save_path(self) -> Path | None:
        return self._save_path

    def _resolve_save_path(self) -> Path | None:
        if self._config.get("save_path"):
            path = Path(self._config["save_path"])
            return path if path.exists() else None
        files = find_save_files()
        return files[0] if files else None

    def state(self) -> dict:
        with self._lock:
            snap = self._snapshot
            return {
                "ok": snap is not None,
                "player": snap.player_name if snap else None,
                "rating": snap.rating if snap else None,
                "depth": snap.depth if snap else None,
                "error": self._error,
                "updated_at": self._updated_at,
                "session": self.session.snapshot(),
                "lang": self.language,
            }

    def reset_session(self) -> None:
        with self._lock:
            rating = self._snapshot.rating if self._snapshot else None
        self.session.reset(rating)
        self._notify()

    def _apply(self, snap: RatingSnapshot) -> None:
        with self._lock:
            previous = self._snapshot
            self._snapshot = snap
            self._error = None
            self._updated_at = time.time()
        if previous and previous.player_name != snap.player_name:
            logger.info("Save switched to player %s, starting a new session", snap.player_name)
            self.session.reset(snap.rating)
        else:
            self.session.observe(snap.rating)
        logger.info("Rating %s (depth %s) for %s", snap.rating, snap.depth, snap.player_name)
        self._notify()

    def _set_error(self, code: str) -> None:
        with self._lock:
            changed = self._error != code
            self._error = code
        if changed:
            self._notify()

    def _watch(self) -> None:
        last_seen: tuple[Path, float] | None = None
        while not self._stop.is_set():
            path = self._resolve_save_path()
            self._save_path = path
            if path is None:
                self._set_error("save_not_found")
                last_seen = None
            else:
                try:
                    mtime = path.stat().st_mtime
                    if last_seen != (path, mtime):
                        snap = read_rating(path)
                        last_seen = (path, snap.save_mtime)
                        self._apply(snap)
                except (OSError, SaveFormatError) as e:
                    logger.warning("Could not read %s: %s", path, e)
                    self._set_error("read_failed")
            self._stop.wait(POLL_INTERVAL)

    def start(self) -> None:
        self.server.start()
        threading.Thread(target=self._watch, name="save-watcher", daemon=True).start()

    def stop(self) -> None:
        self._stop.set()
        self.server.stop()


def _setup_logging() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(DATA_DIR / "app.log", maxBytes=1_000_000, backupCount=1, encoding="utf-8")
    handlers: list[logging.Handler] = [handler]
    if sys.stderr is not None:  # absent in the windowed PyInstaller build
        handlers.append(logging.StreamHandler())
    # force: in the windowed build the root logger can already have a (useless) stderr handler,
    # which would otherwise turn this call into a silent no-op.
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s", handlers=handlers, force=True
    )


def _message_box(text: str) -> None:
    ctypes.windll.user32.MessageBoxW(None, text, "Nightreign Rating Overlay", 0x10)


def _acquire_single_instance():
    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, f"Local\\{APP_NAME}")
    if ctypes.windll.kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
        return None
    return mutex


def main() -> None:
    _setup_logging()
    config = load_config()
    mutex = _acquire_single_instance()
    if mutex is None:
        _message_box(tr(config["language"], "already_running"))
        return
    try:
        app = RatingApp(config)
    except OSError as e:
        logger.error("Could not start the overlay server: %s", e)
        _message_box(tr(config["language"], "port_busy", port=config["port"], error=e, config=CONFIG_PATH))
        return
    app.start()
    try:
        run_tray(app)
    finally:
        app.stop()
