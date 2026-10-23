"""System tray icon: current rating at a glance plus a few actions for streamers."""

import os
import subprocess
import webbrowser
from typing import TYPE_CHECKING

import pystray
from PIL import Image, ImageDraw

from nr_overlay.i18n import LANGUAGES, tr

if TYPE_CHECKING:
    from nr_overlay.app import RatingApp


def make_icon_image(size: int = 64) -> Image.Image:
    """A crescent moon on a deep-night disc."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse((2, 2, size - 2, size - 2), fill=(24, 18, 52, 255), outline=(150, 120, 255, 255), width=3)
    moon = (size * 0.22, size * 0.2, size * 0.74, size * 0.8)
    draw.ellipse(moon, fill=(225, 210, 255, 255))
    shift = size * 0.16
    draw.ellipse((moon[0] + shift, moon[1] - shift * 0.4, moon[2] + shift, moon[3] - shift * 0.4), fill=(24, 18, 52, 255))
    return img


def _format_delta(delta: int) -> str:
    return f"+{delta}" if delta > 0 else str(delta)


def _rating_line(app: "RatingApp") -> str:
    state = app.state()
    if state["ok"]:
        return tr(app.language, "rating", rating=state["rating"], depth=state["depth"])
    return tr(app.language, state["error"] or "waiting")


def _session_line(app: "RatingApp") -> str:
    s = app.state()["session"]
    return tr(app.language, "session", delta=_format_delta(s["delta"]), wins=s["wins"], losses=s["losses"])


def _copy_to_clipboard(text: str) -> None:
    subprocess.run(["clip"], input=text.encode("ascii"), check=False, creationflags=subprocess.CREATE_NO_WINDOW)


def _language_item(app: "RatingApp", code: str, name: str) -> pystray.MenuItem:
    return pystray.MenuItem(
        name,
        lambda icon, item: app.set_language(code),
        checked=lambda item: app.language == code,
        radio=True,
    )


def run_tray(app: "RatingApp") -> None:
    def label(key: str):
        return lambda item: tr(app.language, key)

    def open_save_folder(icon, item):
        if app.save_path:
            os.startfile(app.save_path.parent)

    icon = pystray.Icon(
        "nightreign-rating",
        make_icon_image(),
        "Nightreign Rating",
        menu=pystray.Menu(
            pystray.MenuItem(lambda item: _rating_line(app), None, enabled=False),
            pystray.MenuItem(lambda item: _session_line(app), None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(label("open_overlay"), lambda icon, item: webbrowser.open(app.server.url), default=True),
            pystray.MenuItem(label("copy_url"), lambda icon, item: _copy_to_clipboard(app.server.url)),
            pystray.MenuItem(label("new_session"), lambda icon, item: app.reset_session()),
            pystray.MenuItem(label("open_save_folder"), open_save_folder, enabled=lambda item: app.save_path is not None),
            pystray.MenuItem(label("language"), pystray.Menu(*(_language_item(app, c, n) for c, n in LANGUAGES.items()))),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(label("quit"), lambda icon, item: icon.stop()),
        ),
    )

    def refresh():
        icon.title = f"Nightreign — {_rating_line(app)}"[:127]
        icon.update_menu()

    app.on_change(refresh)
    icon.run(setup=lambda icon: (setattr(icon, "visible", True), refresh()))
