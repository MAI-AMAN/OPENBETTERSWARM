"""Hardened zip <-> bytes for .swarm bundles. The zip arrives from an untrusted
party, so unpack defends against zip-slip, zip-bombs, symlinks, and lying size
headers, and only ever writes into a throwaway sandbox dir (never a real store).
pack re-checks that no secret slipped past redaction before writing a byte."""
from __future__ import annotations

import io
import json
import os
import shutil
import tempfile
import zipfile

from .redact import find_denied_keys

MANIFEST_NAME = "manifest.json"

MAX_ENTRIES = 5000
MAX_TOTAL_BYTES = 200 * 1024 * 1024      # 200 MB uncompressed
MAX_FILE_BYTES = 25 * 1024 * 1024        # 25 MB per entry
MAX_RATIO = 200                          # uncompressed / compressed per entry


class BundleError(Exception):
    """Bundle is malformed or unsafe. Message is safe to show the user."""


def pack(manifest: dict, payloads: dict[str, dict], files: dict[str, bytes]) -> bytes:
    """payloads: bundle_id -> JSON payload (-> entities/<bid>/payload.json).
    files: full zip path -> bytes (e.g. entities/<bid>/files/<rel>)."""
    for bid, payload in payloads.items():
        leaked = find_denied_keys(payload)
        if leaked:
            raise BundleError(
                f"refusing to export: secret-shaped field(s) in {bid}: {leaked[:3]}"
            )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(MANIFEST_NAME, json.dumps(manifest, indent=2))
        for bid, payload in sorted(payloads.items()):
            zf.writestr(f"entities/{bid}/payload.json", json.dumps(payload, indent=2))
        for path, data in sorted(files.items()):
            zf.writestr(path, data)
    return buf.getvalue()


def _safe_member_path(name: str, sandbox: str) -> str:
    if name.startswith(("/", "\\")) or (len(name) > 1 and name[1] == ":"):
        raise BundleError("bundle contains an absolute path")
    dest = os.path.realpath(os.path.join(sandbox, name))
    root = os.path.realpath(sandbox)
    if dest != root and not dest.startswith(root + os.sep):
        raise BundleError("bundle contains a path-traversal entry")
    return dest


def is_zip(raw: bytes) -> bool:
    return zipfile.is_zipfile(io.BytesIO(raw))


def has_member(raw: bytes, name: str) -> bool:
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        return name in zf.namelist()


def unpack(raw: bytes) -> str:
    """Extract into a fresh sandbox temp dir and return it. Caller deletes it."""
    if len(raw) > MAX_TOTAL_BYTES:
        raise BundleError("bundle is too large")
    try:
        zf = zipfile.ZipFile(io.BytesIO(raw))
    except zipfile.BadZipFile:
        raise BundleError("not a valid .swarm file")
    infos = zf.infolist()
    if len(infos) > MAX_ENTRIES:
        raise BundleError("bundle has too many entries")
    total = 0
    for zi in infos:
        if zi.file_size > MAX_FILE_BYTES:
            raise BundleError("bundle has an oversized entry")
        total += zi.file_size
        if total > MAX_TOTAL_BYTES:
            raise BundleError("bundle is too large uncompressed")
        if zi.compress_size and zi.file_size / zi.compress_size > MAX_RATIO:
            raise BundleError("bundle entry is suspiciously compressed")
        mode = (zi.external_attr >> 16) & 0o170000
        if mode == 0o120000:
            raise BundleError("bundle contains a symlink")

    sandbox = tempfile.mkdtemp(prefix="swarm-import-")
    try:
        written = 0
        for zi in infos:
            if zi.is_dir():
                continue
            dest = _safe_member_path(zi.filename, sandbox)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with zf.open(zi) as src, open(dest, "wb") as out:
                while True:
                    chunk = src.read(65536)
                    if not chunk:
                        break
                    written += len(chunk)
                    if written > MAX_TOTAL_BYTES:
                        raise BundleError("bundle exceeded size during extraction")
                    out.write(chunk)
    except Exception:
        shutil.rmtree(sandbox, ignore_errors=True)
        raise
    return sandbox


def read_manifest(sandbox: str) -> dict:
    path = os.path.join(sandbox, MANIFEST_NAME)
    if not os.path.isfile(path):
        raise BundleError("bundle has no manifest")
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise BundleError("bundle manifest is unreadable")
