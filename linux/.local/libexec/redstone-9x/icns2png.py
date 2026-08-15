#!/usr/bin/env python3
"""Decode the NeXTSpirit ICNS subset to strictly verified RGBA PNG files."""
from __future__ import annotations

import argparse
import binascii
import struct
import zlib
from pathlib import Path

PNG = b"\x89PNG\r\n\x1a\n"


class DecodeError(ValueError):
    pass


def _chunk(kind: bytes, payload: bytes) -> bytes:
    return (struct.pack(">I", len(payload)) + kind + payload
            + struct.pack(">I", binascii.crc32(kind + payload) & 0xffffffff))


def encode_png(width: int, height: int, rgba: bytes) -> bytes:
    if len(rgba) != width * height * 4:
        raise DecodeError("wrong RGBA byte count")
    rows = b"".join(b"\0" + rgba[y * width * 4:(y + 1) * width * 4]
                    for y in range(height))
    return (PNG + _chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
            + _chunk(b"IDAT", zlib.compress(rows, 9)) + _chunk(b"IEND", b""))


def verify_png(data: bytes, expected: tuple[int, int] | None = None) -> tuple[int, int]:
    if not data.startswith(PNG):
        raise DecodeError("PNG signature missing")
    pos, dims, compressed, saw_iend = 8, None, bytearray(), False
    while pos < len(data):
        if pos + 12 > len(data):
            raise DecodeError("truncated PNG chunk")
        length = struct.unpack_from(">I", data, pos)[0]
        kind = data[pos + 4:pos + 8]
        end = pos + 8 + length
        if end + 4 > len(data):
            raise DecodeError("PNG chunk exceeds file")
        payload = data[pos + 8:end]
        crc = struct.unpack_from(">I", data, end)[0]
        if (binascii.crc32(kind + payload) & 0xffffffff) != crc:
            raise DecodeError(f"bad PNG CRC in {kind!r}")
        if kind == b"IHDR":
            if dims is not None or pos != 8 or len(payload) != 13:
                raise DecodeError("invalid IHDR placement or size")
            width, height, depth, colour, compression, filtering, interlace = struct.unpack(">IIBBBBB", payload)
            if (depth, colour, compression, filtering, interlace) != (8, 6, 0, 0, 0):
                raise DecodeError("PNG is not non-interlaced RGBA8")
            dims = (width, height)
        elif kind == b"IDAT":
            compressed.extend(payload)
        elif kind == b"IEND":
            if payload or end + 4 != len(data):
                raise DecodeError("IEND is not the exact file boundary")
            saw_iend = True
        pos = end + 4
    if dims is None or not compressed or not saw_iend:
        raise DecodeError("PNG missing IHDR, IDAT, or IEND")
    if expected is not None and dims != expected:
        raise DecodeError(f"PNG dimensions {dims} != {expected}")
    try:
        zlib.decompress(bytes(compressed))
    except zlib.error as error:
        raise DecodeError(f"invalid PNG zlib stream: {error}") from error
    return dims


def elements(container: bytes) -> list[tuple[str, bytes]]:
    if len(container) < 8 or container[:4] != b"icns":
        raise DecodeError("not an ICNS container")
    declared = struct.unpack_from(">I", container, 4)[0]
    if declared != len(container):
        raise DecodeError(f"ICNS declared length {declared} != {len(container)}")
    result, pos = [], 8
    while pos < declared:
        if pos + 8 > declared:
            raise DecodeError("trailing partial ICNS element")
        code = container[pos:pos + 4].decode("latin1")
        length = struct.unpack_from(">I", container, pos + 4)[0]
        if length < 8 or pos + length > declared:
            raise DecodeError(f"bad {code!r} element length {length}")
        result.append((code, container[pos + 8:pos + length]))
        pos += length
    return result


def _unpack_plane(data: bytes, start: int, expected: int, bias: int) -> tuple[bytes, int]:
    out, pos = bytearray(), start
    while len(out) < expected:
        if pos >= len(data):
            raise DecodeError("truncated ICNS RLE plane")
        command = data[pos]; pos += 1
        if command & 0x80:
            count = (command & 0x7f) + bias
            if pos >= len(data):
                raise DecodeError("truncated ICNS RLE repeat")
            out.extend(bytes((data[pos],)) * count); pos += 1
        else:
            count = command + 1
            if pos + count > len(data):
                raise DecodeError("truncated ICNS RLE literal")
            out.extend(data[pos:pos + count]); pos += count
        if len(out) > expected:
            raise DecodeError("ICNS RLE plane overrun")
    return bytes(out), pos


def _rgb(payload: bytes, size: int, code: str) -> bytes:
    plane = size * size
    starts = [4, 0] if code == "it32" or payload[:4] == b"\0\0\0\0" else [0]
    for start in starts:
        if len(payload) - start == plane * 3:
            p = [payload[start + i * plane:start + (i + 1) * plane] for i in range(3)]
            return bytes(v for triplet in zip(*p) for v in triplet)
    for start in starts:
        for bias in (3, 1):
            try:
                p, pos = [], start
                for _ in range(3):
                    decoded, pos = _unpack_plane(payload, pos, plane, bias); p.append(decoded)
                return bytes(v for triplet in zip(*p) for v in triplet)
            except DecodeError:
                pass
    raise DecodeError(f"cannot decode {code} {size}x{size}")


def _rgba(rgb: bytes, alpha: bytes) -> bytes:
    return b"".join(rgb[i:i + 3] + bytes((alpha[i // 3],)) for i in range(0, len(rgb), 3))


def decode(path: Path, output: Path, stem: str) -> dict[str, dict[str, object]]:
    data = path.read_bytes()
    ordered = elements(data)
    by_code = dict(ordered)
    required = {"ics#", "ics8", "is32", "s8mk", "ICN#", "icl8", "il32", "l8mk",
                "it32", "t8mk", "ic08", "ic09"}
    missing = sorted(required - by_code.keys())
    if missing:
        raise DecodeError(f"missing required elements: {', '.join(missing)}")
    output.mkdir(parents=True, exist_ok=True)
    report: dict[str, dict[str, object]] = {}
    for code, size, mask in (("is32", 16, "s8mk"), ("il32", 32, "l8mk"), ("it32", 128, "t8mk")):
        rgb = _rgb(by_code[code], size, code)
        alpha = by_code[mask]
        if len(alpha) < size * size:
            raise DecodeError(f"short {mask} alpha mask")
        encoded = encode_png(size, size, _rgba(rgb, alpha[:size * size]))
        verify_png(encoded, (size, size))
        target = output / f"{stem}-{size}.png"
        target.write_bytes(encoded)
        report[code] = {"size": size, "bytes": len(encoded)}
    for code, size in (("ic08", 256), ("ic09", 512)):
        payload = by_code[code]
        verify_png(payload, (size, size))
        target = output / f"{stem}-{size}.png"
        target.write_bytes(payload)
        verify_png(target.read_bytes(), (size, size))
        report[code] = {"size": size, "bytes": len(payload)}
    report["container"] = {"elements": [code for code, _ in ordered]}
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--stem")
    args = parser.parse_args()
    decode(args.input, args.output, args.stem or args.input.stem)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
