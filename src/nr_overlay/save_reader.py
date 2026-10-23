"""Read the Deep of Night rating from an ELDEN RING NIGHTREIGN save (NR0000.sl2).

The save is a BND4 container whose entries are AES-128-CBC encrypted with the
key FromSoftware has used since Dark Souls II. Entry 0 (USER_DATA000) is the
character block; the rating sits at a fixed distance after the player name.

This module is strictly read-only: the file is opened for a few milliseconds,
only the header and the character block are read, nothing is written back.
"""

import hashlib
import os
import struct
import time
from dataclasses import dataclass
from pathlib import Path

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

SAVE_KEY = bytes.fromhex("18f6326605bd178a5524523ac0a0c609")
SAVE_SUFFIXES = (".sl2", ".co2")  # .co2 is the Seamless Co-op copy

BND4_MAGIC = b"BND4"
BND4_HEADER_LEN = 64
BND4_ENTRY_LEN = 32
BND4_ENTRY_MAGIC = b"\x40\x00\x00\x00\xff\xff\xff\xff"
IV_LEN = 16
CHECKSUM_TAIL = 28  # md5 (16 bytes) + 12 bytes padding at the end of an entry

# Layout of the decrypted character block.
ITEM_STATES_OFFSET = 0x14
ITEM_STATE_SLOTS = 5120
ITEM_STATE_SIZES = {0x80000000: 88, 0x90000000: 16, 0xC0000000: 80}  # weapon, armor, relic
EMPTY_ITEM_STATE_SIZE = 8
PLAYER_NAME_GAP = 0x94  # between the last item state and the player name
PLAYER_NAME_CHARS = 16
RATING_OFFSET = 0x104  # relative to the player name

DEPTH_THRESHOLDS = (0, 1000, 2000, 4000, 6000)  # rating needed for depth 1..5
MAX_SANE_RATING = 100_000


class SaveFormatError(Exception):
    """The file is not a save we understand, or it was caught mid-write."""


@dataclass(frozen=True)
class RatingSnapshot:
    player_name: str
    rating: int
    depth: int
    save_mtime: float


def default_save_dir() -> Path:
    return Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")) / "Nightreign"


def find_save_files(save_dir: Path | None = None) -> list[Path]:
    """All NR0000 saves under every Steam ID folder, most recently written first."""
    root = save_dir or default_save_dir()
    files = [p for p in root.glob("*/NR0000.*") if p.suffix.lower() in SAVE_SUFFIXES]
    return sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)


def depth_for_rating(rating: int) -> int:
    return sum(1 for threshold in DEPTH_THRESHOLDS if rating >= threshold)


def decrypt_entry(encrypted: bytes) -> bytes:
    iv, payload = encrypted[:IV_LEN], encrypted[IV_LEN:]
    if len(payload) % 16:
        raise SaveFormatError("encrypted entry is not block aligned")
    decryptor = Cipher(algorithms.AES(SAVE_KEY), modes.CBC(iv)).decryptor()
    block = decryptor.update(payload) + decryptor.finalize()
    checksum_at = len(block) - CHECKSUM_TAIL
    expected = hashlib.md5(block[4:checksum_at], usedforsecurity=False).digest()
    if block[checksum_at:checksum_at + 16] != expected:
        raise SaveFormatError("character block checksum mismatch (save is being written?)")
    return block


def read_character_block(path: Path) -> bytes:
    with open(path, "rb") as f:
        header = f.read(BND4_HEADER_LEN + BND4_ENTRY_LEN)
        if header[:4] != BND4_MAGIC:
            raise SaveFormatError("not a BND4 save")
        if header[BND4_HEADER_LEN:BND4_HEADER_LEN + 8] != BND4_ENTRY_MAGIC:
            raise SaveFormatError("unexpected BND4 entry header")
        size, _, data_offset = struct.unpack_from("<iii", header, BND4_HEADER_LEN + 8)
        f.seek(data_offset)
        encrypted = f.read(size)
    if size <= IV_LEN or len(encrypted) != size:
        raise SaveFormatError("character block is truncated")
    return decrypt_entry(encrypted)


def find_player_name_offset(block: bytes) -> int:
    offset = ITEM_STATES_OFFSET
    for _ in range(ITEM_STATE_SLOTS):
        (handle,) = struct.unpack_from("<I", block, offset)
        offset += ITEM_STATE_SIZES.get(handle & 0xF0000000, EMPTY_ITEM_STATE_SIZE) if handle else EMPTY_ITEM_STATE_SIZE
    return offset + PLAYER_NAME_GAP


def parse_character_block(block: bytes, save_mtime: float = 0.0) -> RatingSnapshot:
    try:
        name_at = find_player_name_offset(block)
        raw_name = block[name_at:name_at + PLAYER_NAME_CHARS * 2]
        (rating,) = struct.unpack_from("<I", block, name_at + RATING_OFFSET)
    except struct.error as e:
        raise SaveFormatError(f"character block is too short: {e}") from e

    name = raw_name.decode("utf-16-le", errors="ignore").split("\x00", 1)[0]
    if not name or rating > MAX_SANE_RATING:
        raise SaveFormatError("character block layout not recognised (game update?)")
    return RatingSnapshot(player_name=name, rating=rating, depth=depth_for_rating(rating), save_mtime=save_mtime)


def read_rating(path: Path, attempts: int = 5, retry_delay: float = 0.4) -> RatingSnapshot:
    """Read the rating, retrying while the game is in the middle of writing the save."""
    last_error: Exception | None = None
    for attempt in range(attempts):
        if attempt:
            time.sleep(retry_delay)
        try:
            mtime_before = path.stat().st_mtime
            block = read_character_block(path)
            if path.stat().st_mtime != mtime_before:
                raise SaveFormatError("save changed while reading")
            return parse_character_block(block, mtime_before)
        except (OSError, SaveFormatError) as e:
            last_error = e
    assert last_error is not None
    raise last_error
