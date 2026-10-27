"""Create ROM patches (IPS / BPS) for the Lagrange Point (TC) VRC7-Wide fix.

Three files are involved:

  * the retail Japanese ROM (TOSEC / No-No-Intro dump, 512 KiB PRG),
  * the distributed Chinese translation v1.1 (1 MiB PRG, crashes on accurate
    emulators), and
  * the fixed translation (same 1 MiB image, 14 bytes changed).

Two families of patches are produced:

  * retail JP  -> fixed translation   (BPS only: the file grows by 512 KiB, which
    IPS cannot express); contains the translation data,
  * translation -> fixed translation  (IPS + BPS, 14 bytes of changes only).

Mesen (and most other emulators) detect the format from the file signature, so
either file can be loaded with "Load Patch" / the second command line argument.

Usage:
    python tools/make_rom_patch.py [--retail PATH] [--translated PATH]
                                   [--patched PATH] [--out-dir DIR]
"""

from __future__ import annotations

import os
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RETAIL_JP = os.path.join(HERE, "Lagrange Point (1991-04-26)(Konami)(JP).nes")
ORIGINAL = os.path.join(HERE, "Lagrange+Point+(TC)+Ver1.1.nes")
PATCHED = os.path.join(HERE, "Lagrange+Point+(TC)+Ver1.1 (VRC7-Wide).nes")
OUT_DIR = HERE


def diff_runs(a: bytes, b: bytes) -> list[tuple[int, bytes]]:
    """Return [(offset, new_bytes)] for every region where a and b differ."""
    assert len(a) == len(b), "IPS cannot change the file size"
    runs: list[tuple[int, bytes]] = []
    i = 0
    n = len(a)
    while i < n:
        if a[i] == b[i]:
            i += 1
            continue
        start = i
        while i < n and a[i] != b[i]:
            i += 1
        runs.append((start, b[start:i]))
    return runs


def build_ips(runs: list[tuple[int, bytes]]) -> bytes:
    out = bytearray(b"PATCH")
    for offset, data in runs:
        if offset > 0xFFFFFF:
            raise ValueError("offset beyond IPS range")
        out += bytes([(offset >> 16) & 0xFF, (offset >> 8) & 0xFF, offset & 0xFF])
        out += struct.pack(">H", len(data)) + data
    out += b"EOF"
    return bytes(out)


def _bps_number(value: int) -> bytes:
    out = bytearray()
    while True:
        digit = value & 0x7F
        value >>= 7
        if value == 0:
            out.append(0x80 | digit)
            return bytes(out)
        out.append(digit)
        value -= 1


def _bps_actions(source: bytes, target: bytes) -> list[tuple[int, int, int | bytes | None]]:
    """Action list covering the whole target: (kind, length, payload).

    kind 0 = SourceRead (same offset in source), 1 = TargetRead (literal bytes),
    3 = TargetCopy (repeat the previous byte, payload = absolute output offset).
    """
    n_src, n_tgt = len(source), len(target)
    tail = min(8, n_tgt)
    limit = n_tgt - tail
    actions: list[tuple[int, int, int | bytes | None]] = []

    def repeated_run(pos: int) -> int:
        value = target[pos]
        end = pos
        while end < limit and target[end] == value:
            end += 1
        return end - pos

    def rle_ok(pos: int) -> bool:
        # TargetCopy repeats the byte already written at pos - 1, so the run has
        # to start with that same byte.
        return pos > 0 and target[pos - 1] == target[pos] and repeated_run(pos) >= 8

    i = 0
    while i < limit:
        if i < n_src and source[i] == target[i]:
            start = i
            while i < limit and i < n_src and source[i] == target[i]:
                i += 1
            actions.append((0, i - start, None))
            continue

        if rle_ok(i):
            run = repeated_run(i)
            actions.append((3, run, i - 1))
            i += run
            continue

        start = i
        i += 1
        while i < limit:
            if i < n_src and source[i] == target[i]:
                break
            if rle_ok(i):
                break
            i += 1
        actions.append((1, i - start, bytes(target[start:i])))

    # Mesen's BpsPatcher stops reading actions 12 bytes before the end of the
    # file (it assumes the trailing CRCs are preceded by a longer final action),
    # so a short final action would be skipped and the tail left zeroed.  Ending
    # with a literal TargetRead of the last few bytes keeps the patch both
    # spec-correct and loadable by Mesen.
    actions.append((1, tail, bytes(target[limit:])))
    return actions


def build_bps(source: bytes, target: bytes) -> bytes:
    header = bytearray(b"BPS1")
    header += _bps_number(len(source))
    header += _bps_number(len(target))
    header += _bps_number(0)  # no metadata

    body = bytearray()
    target_relative = 0
    for kind, length, payload in _bps_actions(source, target):
        body += _bps_number(((length - 1) << 2) | kind)
        if kind == 1:
            body += payload  # type: ignore[operator]
        elif kind == 3:
            delta = int(payload) - target_relative  # type: ignore[arg-type]
            body += _bps_number((abs(delta) << 1) | (1 if delta < 0 else 0))
            target_relative = int(payload) + length  # type: ignore[arg-type]

    out = header + body
    out += struct.pack("<I", zlib.crc32(source) & 0xFFFFFFFF)
    out += struct.pack("<I", zlib.crc32(target) & 0xFFFFFFFF)
    return bytes(out)


def apply_ips(source: bytes, patch: bytes) -> bytes:
    """Reference IPS applier (spec: PATCH, 3-byte offset, 2-byte size, EOF, RLE)."""
    if not patch.startswith(b"PATCH"):
        raise ValueError("not an IPS patch")
    out = bytearray(source)
    i = 5
    while True:
        if patch[i:i + 3] == b"EOF":
            break
        offset = (patch[i] << 16) | (patch[i + 1] << 8) | patch[i + 2]
        size = (patch[i + 3] << 8) | patch[i + 4]
        i += 5
        if size == 0:
            count = (patch[i] << 8) | patch[i + 1]
            value = patch[i + 2]
            i += 3
            for k in range(count):
                out[offset + k] = value
        else:
            out[offset:offset + size] = patch[i:i + size]
            i += size
    return bytes(out)


def _read_bps_number(data: bytes, pos: int) -> tuple[int, int]:
    shift = 1
    value = 0
    while True:
        byte = data[pos]
        pos += 1
        value += (byte & 0x7F) * shift
        if byte & 0x80:
            return value, pos
        shift <<= 7
        value += shift


def apply_bps(source: bytes, patch: bytes) -> bytes:
    if not patch.startswith(b"BPS1"):
        raise ValueError("not a BPS patch")
    pos = 4
    source_size, pos = _read_bps_number(patch, pos)
    target_size, pos = _read_bps_number(patch, pos)
    metadata_size, pos = _read_bps_number(patch, pos)
    pos += metadata_size
    # the two CRC32 values live at the very end of the file
    source_crc, target_crc = struct.unpack_from("<II", patch, len(patch) - 8)
    if source_size != len(source) or (zlib.crc32(source) & 0xFFFFFFFF) != source_crc:
        raise ValueError("source ROM does not match the patch")

    out = bytearray()
    source_relative = 0
    target_relative = 0
    while pos < len(patch) - 8:
        data, pos = _read_bps_number(patch, pos)
        length = (data >> 2) + 1
        action = data & 3
        if action == 0:      # SourceRead
            out += source[len(out):len(out) + length]
        elif action == 1:    # TargetRead
            out += patch[pos:pos + length]
            pos += length
        elif action == 2:    # SourceCopy
            delta, pos = _read_bps_number(patch, pos)
            source_relative += (-1 if delta & 1 else 1) * (delta >> 1)
            out += source[source_relative:source_relative + length]
            source_relative += length
        else:                # TargetCopy
            delta, pos = _read_bps_number(patch, pos)
            target_relative += (-1 if delta & 1 else 1) * (delta >> 1)
            for _ in range(length):
                out.append(out[target_relative])
                target_relative += 1

    if len(out) != target_size or (zlib.crc32(out) & 0xFFFFFFFF) != target_crc:
        raise ValueError("BPS output mismatch")
    return bytes(out)


def main(argv: list[str]) -> int:
    retail_jp, original, patched, out_dir = RETAIL_JP, ORIGINAL, PATCHED, OUT_DIR
    i = 0
    while i < len(argv):
        arg = argv[i]
        if i + 1 >= len(argv):
            raise SystemExit(f"missing value for {arg}")
        value = os.path.abspath(argv[i + 1])
        if arg == "--retail":
            retail_jp = value
        elif arg == "--translated":
            original = value
        elif arg == "--patched":
            patched = value
        elif arg == "--out-dir":
            out_dir = value
        else:
            raise SystemExit(f"unknown option {arg}")
        i += 2

    out_ips = os.path.join(out_dir, "LagrangePointTC-Ver1.1-vrc7wide.ips")
    out_bps = os.path.join(out_dir, "LagrangePointTC-Ver1.1-vrc7wide.bps")
    out_full_bps = os.path.join(out_dir, "LagrangePoint-JP-to-TC-Ver1.1-vrc7wide.bps")

    original_data = open(original, "rb").read()
    patched_data = open(patched, "rb").read()
    runs = diff_runs(original_data, patched_data)

    print(f"translation {len(original_data)} bytes, patched {len(patched_data)} bytes")
    print(f"{len(runs)} differing region(s), {sum(len(d) for _, d in runs)} byte(s):")
    for offset, data in runs:
        print(f"  0x{offset:06X}  {len(data):2d}  {data.hex(' ')}")

    ips = build_ips(runs)
    bps = build_bps(original_data, patched_data)
    with open(out_ips, "wb") as fh:
        fh.write(ips)
    with open(out_bps, "wb") as fh:
        fh.write(bps)
    print(f"wrote {out_ips} ({len(ips)} bytes)")
    print(f"wrote {out_bps} ({len(bps)} bytes)")

    assert apply_ips(original_data, ips) == patched_data, "IPS round-trip failed"
    assert apply_bps(original_data, bps) == patched_data, "BPS round-trip failed"
    print("round-trip check: both patches reproduce the patched ROM exactly")

    # Patch against the TOSEC dump of the retail Japanese release: this is the
    # file people actually own, and the target is 512 KiB larger, so BPS is the
    # only option (IPS cannot change the file length).
    jp = open(retail_jp, "rb").read()
    full = build_bps(jp, patched_data)
    with open(out_full_bps, "wb") as fh:
        fh.write(full)
    print(f"\nretail JP {len(jp)} bytes -> patched {len(patched_data)} bytes")
    print(f"wrote {out_full_bps} ({len(full)} bytes)")
    assert apply_bps(jp, full) == patched_data, "full BPS round-trip failed"
    print("round-trip check: retail Japanese ROM + patch == patched ROM exactly")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
