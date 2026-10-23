import json
import re

import pytest

from nr_overlay import app
from nr_overlay.i18n import DEFAULT_LANGUAGE, LANGUAGES, STRINGS, tr


def test_every_language_has_every_key_and_placeholder():
    reference = STRINGS[DEFAULT_LANGUAGE]
    for lang in LANGUAGES:
        assert STRINGS[lang].keys() == reference.keys(), lang
        for key, text in reference.items():
            assert set(re.findall(r"{(\w+)}", STRINGS[lang][key])) == set(re.findall(r"{(\w+)}", text)), (lang, key)


def test_unknown_language_falls_back_to_english():
    assert tr("de", "quit") == "Quit"
    assert tr("zh", "rating", rating=1800, depth=2) == "评分：1800（深度 2）"


@pytest.fixture
def config_path(tmp_path, monkeypatch):
    path = tmp_path / "config.json"
    monkeypatch.setattr(app, "DATA_DIR", tmp_path)
    monkeypatch.setattr(app, "CONFIG_PATH", path)
    return path


def test_language_defaults_to_english(config_path):
    config_path.write_text(json.dumps({"port": 9000}))  # config from a version without "language"
    assert app.load_config()["language"] == "en"


def test_bad_language_in_config_is_replaced(config_path):
    config_path.write_text(json.dumps({"language": "klingon"}))
    assert app.load_config()["language"] == "en"


def test_saved_language_survives_reload(config_path):
    config = app.load_config()
    config["language"] = "zh"
    app.save_config(config)
    assert app.load_config()["language"] == "zh"
