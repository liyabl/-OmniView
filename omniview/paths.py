"""Paths, cache helpers, and small utilities for the native app."""
from __future__ import annotations

import hashlib
import os
import re
import shutil
import sys
import tempfile
import time

APP_NAME = "OmniView"
APP_VERSION = "0.3.0"


def bundle_dir() -> str:
    if getattr(sys, "frozen", False):
        return getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def data_dir() -> str:
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    d = os.path.join(base, APP_NAME)
    os.makedirs(d, exist_ok=True)
    return d


DATA = data_dir()
CACHE = os.path.join(DATA, "cache")
TEMP = os.path.join(DATA, "temp")
BACKUPS = os.path.join(DATA, "backups")
for _p in (CACHE, TEMP, BACKUPS):
    os.makedirs(_p, exist_ok=True)


def bundled(*parts: str) -> str:
    return os.path.join(bundle_dir(), *parts)


def cache_key(path: str, kind: str, extra: str = "") -> str:
    try:
        st = os.stat(path)
        sig = f"{os.path.abspath(path).lower()}|{st.st_size}|{st.st_mtime_ns}"
    except OSError:
        sig = os.path.abspath(path).lower()
    return hashlib.sha1(f"{sig}|{kind}|{extra}".encode("utf-8", "surrogatepass")).hexdigest()


def cache_file(path: str, kind: str, ext: str, extra: str = "") -> str:
    key = cache_key(path, kind, extra)
    d = os.path.join(CACHE, kind)
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, key + "." + ext.lstrip("."))


def temp_dir(prefix: str = "ov-") -> str:
    return tempfile.mkdtemp(prefix=prefix, dir=TEMP)


def safe_name(name: str, maxlen: int = 90) -> str:
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name).strip(" .")
    if not name:
        name = "file"
    if len(name) > maxlen:
        base, ext = os.path.splitext(name)
        name = base[: max(8, maxlen - len(ext))] + ext
    return name


def human_size(n) -> str:
    try:
        n = float(n)
    except (TypeError, ValueError):
        return "—"
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"


def human_time(ts) -> str:
    try:
        return time.strftime("%Y-%m-%d %H:%M", time.localtime(float(ts)))
    except Exception:
        return "—"


def open_folder(path: str) -> None:
    try:
        if os.path.isdir(path):
            os.startfile(path)  # type: ignore[attr-defined]
        else:
            os.startfile(os.path.dirname(path))  # type: ignore[attr-defined]
    except Exception:
        pass


def clear_cache() -> None:
    for d in (CACHE, TEMP):
        shutil.rmtree(d, ignore_errors=True)
        os.makedirs(d, exist_ok=True)

