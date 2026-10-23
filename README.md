# Nightreign Rating Overlay

A tray app that shows your ELDEN RING NIGHTREIGN Deep of Night rating on a page for OBS.
Windows only.

## Usage

1. Run `NightreignRatingOverlay.exe`. A crescent moon icon appears in the tray.
2. Right-click the icon → "Copy OBS link" (`http://127.0.0.1:8765/`).
3. In OBS: Sources → "+" → Browser → paste the link, width 420, height 120.
   The page background is transparent.

Link options (can be combined, e.g. `http://127.0.0.1:8765/?scale=1.5&lang=ru`):

| Option            | What it does                                                    |
|-------------------|-----------------------------------------------------------------|
| `lang=en\|ru\|zh` | pin the overlay language (without it, the tray language is used) |
| `session=0`       | hide the "this stream" line                                     |
| `bg=none`         | no card background, text only                                   |
| `scale=1.5`       | resize everything                                               |

The tray menu shows the current rating and the session summary, and has: open the overlay in
a browser, copy the OBS link, "Start new session" (resets the "this stream" counters), open
the save folder, language, quit.

The session survives app restarts and starts over by itself once it is more than 12 hours old.

## Language

English (default), Русский, 中文. Pick it in the tray: Language / Язык / 语言.
The choice is saved and applies right away to the tray menu and the overlay: OBS picks it up
within a second, no need to refresh the source.

## Where the rating comes from

There is no official API, so the rating is read from the local save
`%APPDATA%\Nightreign\<SteamID>\NR0000.sl2` (or `NR0000.co2` for Seamless Co-op):

- the save is a BND4 container; each entry is AES-128-CBC encrypted with the key FromSoftware
  has used since Dark Souls II (the first 16 bytes of an entry are the IV, an MD5 of the
  contents sits at the end);
- entry 0 (`USER_DATA000`) is the character data. After 5120 item records and a 0x94 gap comes
  the player name (UTF-16); the rating is a `uint32` at name + 0x104, the zero-based depth
  is a `uint32` at name + 0x10C.

The app checks the file every 1.5 s. When it changes, the app reads only the header and the
character entry and verifies the MD5, so a half-written save is never shown.

## Is it safe (EAC / bans)

The app **only reads** the save file from disk. It does not touch the game process (no memory
reading, no injection, no network interception) and never writes to the save. Easy Anti-Cheat
watches the game process, not who reads files in `AppData`; Steam Cloud, antivirus software
and save backup tools read the same file.

Save-related bans in FromSoftware games are for *modified* saves (spawned items and the like).
This app never modifies the save.

## Limitations

- Wins and losses are counted from rating changes: a rise is a win, a drop is a loss. A loss
  that costs no points (depth 1, or the final day at depth 2) is not counted.
- A game update may shift the save layout. The tray will then show "Could not read the save",
  and `%APPDATA%\NightreignRatingOverlay\app.log` will have the reason.

## Settings

`%APPDATA%\NightreignRatingOverlay\config.json`:

```json
{ "port": 8765, "save_path": null, "session_max_age_hours": 12, "language": "en" }
```

`language` is `en`, `ru` or `zh`; switching it from the tray is easier.

`save_path` points at a specific save if auto-detection picked the wrong one (by default the
most recently written `NR0000.sl2`/`.co2` across all SteamID folders is used).

## Building from source

Requires Python 3.12+.

```powershell
.\build.ps1          # venv, dependencies, tests, dist\NightreignRatingOverlay.exe
```

Run without building:

```powershell
.venv\Scripts\python -m nr_overlay
```

## License

MIT, see [LICENSE](LICENSE). The prebuilt executable bundles third-party libraries under their
own licenses, including pystray (LGPL-3.0); see [THIRD_PARTY_NOTICES.txt](THIRD_PARTY_NOTICES.txt).

Not affiliated with or endorsed by FromSoftware or Bandai Namco Entertainment.
ELDEN RING NIGHTREIGN is a trademark of its respective owners.
