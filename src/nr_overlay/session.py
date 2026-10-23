"""Per-stream rating session: start rating, net change, wins and losses.

Persisted to disk so restarting the app mid-stream keeps the counters. A session
older than `max_age_hours` is treated as finished and a new one starts.
"""

import json
import logging
import threading
import time
from dataclasses import asdict, dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class Session:
    started_at: float
    start_rating: int | None = None
    last_rating: int | None = None
    wins: int = 0
    losses: int = 0

    @property
    def delta(self) -> int:
        if self.start_rating is None or self.last_rating is None:
            return 0
        return self.last_rating - self.start_rating


class SessionTracker:
    def __init__(self, path: Path, max_age_hours: float = 12):
        self._path = path
        self._max_age = max_age_hours * 3600
        self._lock = threading.Lock()
        self._session = self._load()

    def _load(self) -> Session:
        try:
            session = Session(**json.loads(self._path.read_text(encoding="utf-8")))
        except FileNotFoundError:
            return Session(started_at=time.time())
        except (OSError, ValueError, TypeError) as e:
            logger.warning("Ignoring unreadable session file %s: %s", self._path, e)
            return Session(started_at=time.time())
        if time.time() - session.started_at > self._max_age:
            return Session(started_at=time.time())
        return session

    def _save(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(json.dumps(asdict(self._session)), encoding="utf-8")
        except OSError as e:
            logger.warning("Could not save session to %s: %s", self._path, e)

    def observe(self, rating: int) -> None:
        """Record the rating read from the save. A rise counts as a win, a drop as a loss."""
        with self._lock:
            s = self._session
            if s.start_rating is None:
                s.start_rating = rating
            elif s.last_rating is not None and rating != s.last_rating:
                if rating > s.last_rating:
                    s.wins += 1
                else:
                    s.losses += 1
            s.last_rating = rating
            self._save()

    def reset(self, current_rating: int | None) -> None:
        with self._lock:
            self._session = Session(started_at=time.time(), start_rating=current_rating, last_rating=current_rating)
            self._save()

    def snapshot(self) -> dict:
        with self._lock:
            s = self._session
            return {
                "started_at": s.started_at,
                "start_rating": s.start_rating,
                "delta": s.delta,
                "wins": s.wins,
                "losses": s.losses,
            }
