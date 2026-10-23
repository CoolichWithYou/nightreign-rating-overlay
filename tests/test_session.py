import json
import time

from nr_overlay.session import SessionTracker


def test_counts_wins_losses_and_delta(tmp_path):
    tracker = SessionTracker(tmp_path / "session.json")
    for rating in (1800, 1800, 2000, 1800, 2000, 2200):
        tracker.observe(rating)
    s = tracker.snapshot()
    assert (s["start_rating"], s["delta"], s["wins"], s["losses"]) == (1800, 400, 3, 1)


def test_survives_restart(tmp_path):
    path = tmp_path / "session.json"
    SessionTracker(path).observe(1800)
    tracker = SessionTracker(path)
    tracker.observe(2000)
    assert tracker.snapshot()["delta"] == 200


def test_stale_session_starts_fresh(tmp_path):
    path = tmp_path / "session.json"
    path.write_text(json.dumps({"started_at": time.time() - 13 * 3600, "start_rating": 1000, "last_rating": 1600,
                                "wins": 3, "losses": 0}))
    tracker = SessionTracker(path, max_age_hours=12)
    tracker.observe(1600)
    assert tracker.snapshot() | {"started_at": 0} == {"started_at": 0, "start_rating": 1600, "delta": 0,
                                                      "wins": 0, "losses": 0}


def test_reset(tmp_path):
    tracker = SessionTracker(tmp_path / "session.json")
    tracker.observe(1800)
    tracker.observe(2000)
    tracker.reset(2000)
    assert tracker.snapshot()["delta"] == 0 and tracker.snapshot()["wins"] == 0
