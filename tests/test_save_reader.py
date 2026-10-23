import hashlib
import os
import struct

import pytest
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from nr_overlay import save_reader as sr

BLOCK_SIZE = 0x30000


def make_character_block(name: str, rating: int, depth_index: int, relics: int = 3) -> bytearray:
    block = bytearray(BLOCK_SIZE)
    offset = sr.ITEM_STATES_OFFSET
    for i in range(relics):  # a few 80-byte relic states shift everything after them
        struct.pack_into("<II", block, offset, 0xC0000000 | (0x800000 + i), 0x80000000 | 1000)
        offset += 80
    offset += (sr.ITEM_STATE_SLOTS - relics) * sr.EMPTY_ITEM_STATE_SIZE + sr.PLAYER_NAME_GAP
    block[offset:offset + len(name) * 2] = name.encode("utf-16-le")
    struct.pack_into("<I", block, offset + sr.RATING_OFFSET, rating)
    struct.pack_into("<I", block, offset + sr.DEPTH_INDEX_OFFSET, depth_index)
    checksum_at = len(block) - sr.CHECKSUM_TAIL
    block[checksum_at:checksum_at + 16] = hashlib.md5(block[4:checksum_at]).digest()
    return block


def encrypt(block: bytes) -> bytes:
    iv = os.urandom(16)
    encryptor = Cipher(algorithms.AES(sr.SAVE_KEY), modes.CBC(iv)).encryptor()
    return iv + encryptor.update(bytes(block)) + encryptor.finalize()


def make_save(block: bytes) -> bytes:
    entry = encrypt(block)
    data_offset = sr.BND4_HEADER_LEN + sr.BND4_ENTRY_LEN
    header = bytearray(sr.BND4_HEADER_LEN)
    header[:4] = sr.BND4_MAGIC
    struct.pack_into("<i", header, 12, 1)
    entry_header = sr.BND4_ENTRY_MAGIC + struct.pack("<iiiii", len(entry), 0, data_offset, 0, 0) + bytes(4)
    return bytes(header) + entry_header + entry


@pytest.fixture
def save_file(tmp_path):
    def write(block: bytes):
        path = tmp_path / "76561190000000000" / "NR0000.sl2"
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(make_save(block))
        return path

    return write


def test_reads_rating_depth_and_name(save_file):
    path = save_file(make_character_block("player", 1800, 1))
    snap = sr.read_rating(path)
    assert (snap.player_name, snap.rating, snap.depth) == ("player", 1800, 2)


def test_corrupted_block_is_rejected(save_file):
    block = make_character_block("player", 2400, 2)
    block[100] ^= 0xFF  # breaks the md5, as a half-written save would
    path = save_file(block)
    with pytest.raises(sr.SaveFormatError):
        sr.read_rating(path, attempts=1)


def test_not_a_save(tmp_path):
    path = tmp_path / "NR0000.sl2"
    path.write_bytes(b"nope" * 100)
    with pytest.raises(sr.SaveFormatError):
        sr.read_rating(path, attempts=1)


def test_unknown_depth_index_falls_back_to_thresholds():
    block = make_character_block("player", 4200, 99)
    assert sr.parse_character_block(bytes(block)).depth == 4


@pytest.mark.parametrize("rating,depth", [(0, 1), (999, 1), (1000, 2), (3999, 3), (4000, 4), (6000, 5), (9000, 5)])
def test_depth_for_rating(rating, depth):
    assert sr.depth_for_rating(rating) == depth


def test_find_save_files_prefers_newest(tmp_path):
    old = tmp_path / "1" / "NR0000.sl2"
    new = tmp_path / "2" / "NR0000.co2"
    for p in (old, new):
        p.parent.mkdir()
        p.write_bytes(b"x")
    os.utime(old, (1, 1))
    (tmp_path / "2" / "NR0000.sl2.bak").write_bytes(b"x")
    assert sr.find_save_files(tmp_path) == [new, old]
