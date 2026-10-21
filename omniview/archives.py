"""Archive listing and extraction with a bundled 7-Zip (no user install needed)."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tarfile
import zipfile

from . import paths


def sevenzip() -> str:
    p = paths.bundled("7z", "7z.exe")
    if os.path.exists(p):
        return p
    for cand in (r"C:\Program Files\7-Zip\7z.exe", r"C:\Program Files (x86)\7-Zip\7z.exe"):
        if os.path.exists(cand):
            return cand
    return "7z"


def _run(args, timeout=300):
    flags = 0x08000000 if os.name == "nt" else 0
    p = subprocess.run(args, capture_output=True, timeout=timeout, creationflags=flags,
                       env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    return p.returncode, (p.stdout or b"").decode("utf-8", "replace") + "\n" + (p.stderr or b"").decode("utf-8", "replace")


def _ext(path: str) -> str:
    low = path.lower()
    for m in ("tar.gz", "tar.bz2", "tar.xz", "tar.zst"):
        if low.endswith("." + m):
            return m
    return os.path.splitext(path)[1].lower().lstrip(".")


def _fix_zip_name(name: str, flags: int) -> str:
    if flags & 0x800:
        return name
    try:
        raw = name.encode("cp437")
    except Exception:
        return name
    best, score = name, _score(name)
    for enc in ("utf-8", "gb18030", "big5", "shift_jis"):
        try:
            cand = raw.decode(enc)
        except Exception:
            continue
        sc = _score(cand)
        if sc > score:
            best, score = cand, sc
    return best


def _score(s: str) -> float:
    good = cjk = bad = 0
    for ch in s:
        o = ord(ch)
        if 0x4E00 <= o <= 0x9FFF or 0x3000 <= o <= 0x30FF or 0xAC00 <= o <= 0xD7AF:
            good += 1
            cjk += 1
        elif o < 32 or ch == "\ufffd":
            bad += 2
        elif 0x80 <= o <= 0xFF:
            bad += 0.2
        else:
            good += 1
    return good - bad + cjk * 1.5


def _zip_entries(path: str) -> list[dict]:
    out = []
    with zipfile.ZipFile(path) as z:
        for info in z.infolist()[:50000]:
            name = _fix_zip_name(info.filename, info.flag_bits).replace("\\", "/")
            out.append({"path": name.rstrip("/"), "dir": name.endswith("/"),
                        "size": info.file_size, "packed": info.compress_size,
                        "mtime": "%04d-%02d-%02d %02d:%02d" % info.date_time[:5],
                        "encrypted": bool(info.flag_bits & 0x1)})
    return out


def _tar_entries(path: str) -> list[dict]:
    out = []
    with tarfile.open(path, "r:*") as t:
        for m in t.getmembers()[:50000]:
            out.append({"path": m.name.rstrip("/"), "dir": m.isdir(), "size": m.size,
                        "packed": 0, "mtime": "", "encrypted": False})
    return out


def _7z_entries(path: str) -> list[dict]:
    code, text = _run([sevenzip(), "l", "-slt", "-ba", "-sccUTF-8", path])
    if code not in (0, 1):
        raise RuntimeError("7-Zip 无法打开该压缩包")
    entries = []
    cur = {}
    for line in text.splitlines():
        if not line.strip():
            if cur.get("Path"):
                entries.append(cur)
            cur = {}
        elif " = " in line:
            k, v = line.split(" = ", 1)
            cur[k.strip()] = v
    if cur.get("Path"):
        entries.append(cur)
    out = []
    for e in entries:
        p = e.get("Path", "").replace("\\", "/")
        if not p:
            continue
        attr = e.get("Attributes", "")
        out.append({"path": p.rstrip("/"), "dir": attr.startswith("D") or p.endswith("/"),
                    "size": int(e.get("Size", "0") or 0), "packed": int(e.get("Packed Size", "0") or 0),
                    "mtime": e.get("Modified", ""),
                    "encrypted": e.get("Encrypted", "").strip() not in ("", "-")})
    return out


def listing(path: str) -> dict:
    ext = _ext(path)
    if ext in ("zip", "jar", "apk", "whl", "epub"):
        try:
            entries = _zip_entries(path)
        except Exception:
            entries = _7z_entries(path)
    elif ext in ("tar", "tgz", "tar.gz", "tar.bz2", "tar.xz", "tar.zst", "gz", "bz2", "xz"):
        try:
            entries = _tar_entries(path)
        except Exception:
            entries = _7z_entries(path)
    else:
        entries = _7z_entries(path)
    entries.sort(key=lambda x: (not x["dir"], x["path"].lower()))
    return {"entries": entries, "count": len(entries), "files": sum(1 for e in entries if not e["dir"]),
            "total": sum(e["size"] for e in entries if not e["dir"]),
            "encrypted": any(e["encrypted"] for e in entries), "format": ext.upper()}


def _safe_join(base: str, rel: str) -> str:
    rel = rel.replace("\\", "/").lstrip("/")
    parts = [p for p in rel.split("/") if p not in ("", ".", "..")]
    target = os.path.abspath(os.path.join(base, *parts))
    if not (target == os.path.abspath(base) or target.startswith(os.path.abspath(base) + os.sep)):
        raise ValueError("非法路径")
    return target


def extract_entry(path: str, entry: str) -> str:
    base = os.path.join(paths.CACHE, "unpack", paths.cache_key(path, "unpack"))
    target = _safe_join(base, entry)
    if os.path.exists(target):
        return target
    os.makedirs(base, exist_ok=True)
    ext = _ext(path)
    if ext in ("zip", "jar", "apk", "whl", "epub"):
        with zipfile.ZipFile(path) as z:
            for info in z.infolist():
                name = _fix_zip_name(info.filename, info.flag_bits).replace("\\", "/").rstrip("/")
                if name == entry.rstrip("/"):
                    if info.flag_bits & 0x1:
                        raise RuntimeError("该条目已加密")
                    os.makedirs(os.path.dirname(target), exist_ok=True)
                    with z.open(info) as src, open(target, "wb") as dst:
                        shutil.copyfileobj(src, dst, 1024 * 1024)
                    return target
    tmp = paths.temp_dir("un7z-")
    code, text = _run([sevenzip(), "x", "-y", "-sccUTF-8", f"-o{tmp}", path, entry])
    found = None
    for root, _dirs, files in os.walk(tmp):
        for f in files:
            found = os.path.join(root, f)
            break
        if found:
            break
    if code != 0 or not found:
        shutil.rmtree(tmp, ignore_errors=True)
        raise RuntimeError("解包失败：" + text[-400:])
    os.makedirs(os.path.dirname(target), exist_ok=True)
    shutil.move(found, target)
    shutil.rmtree(tmp, ignore_errors=True)
    return target
