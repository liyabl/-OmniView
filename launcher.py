"""Tiny self-extracting launcher for OmniView.

The real payload (payload.7z) and 7z.exe are bundled by PyInstaller.  The
version comes from version.txt inside the SFX, so bumping the release does not
require editing this file.
"""
from __future__ import annotations

import ctypes
import os
import shutil
import subprocess
import sys
import time

ROOT = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "OmniView")


def fail(msg: str) -> None:
    try:
        ctypes.windll.user32.MessageBoxW(None, msg, "OmniView Setup", 0x10)
    except Exception:
        pass


def wait_unlocked(dest: str) -> bool:
    """Give Windows time to release Qt/python DLL handles after taskkill."""
    for _ in range(20):
        if not os.path.exists(dest):
            return True
        try:
            old = dest + ".old"
            shutil.rmtree(old, ignore_errors=True)
            os.rename(dest, old)
            shutil.rmtree(old, ignore_errors=True)
            return True
        except OSError:
            time.sleep(0.5)
    return False


def main() -> int:
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    seven = os.path.join(base, "assets", "7z", "7z.exe")
    payload = os.path.join(base, "payload.7z")
    if not os.path.exists(seven) or not os.path.exists(payload):
        fail("Installer payload is missing.")
        return 2
    version = "0.3"
    try:
        with open(os.path.join(base, "version.txt"), "r", encoding="utf-8") as f:
            version = f.read().strip() or version
    except Exception:
        pass
    dest = os.path.join(ROOT, version)
    os.makedirs(dest, exist_ok=True)

    try:
        subprocess.run(["taskkill", "/F", "/IM", "OmniView.exe"],
                       creationflags=0x08000000, capture_output=True)
    except Exception:
        pass
    time.sleep(1.0)

    # If the old directory is still locked, extract to a unique sibling rather
    # than showing "Cannot delete output file".
    target = dest
    if not wait_unlocked(dest):
        target = dest + "-" + time.strftime("%Y%m%d%H%M%S")
        os.makedirs(target, exist_ok=True)

    last_err = b""
    for _attempt in range(3):
        try:
            r = subprocess.run([seven, "x", "-y", "-aoa", f"-o{target}", payload],
                               cwd=base, creationflags=0x08000000, capture_output=True)
            last_err = r.stderr
            if r.returncode == 0:
                break
        except Exception as e:
            last_err = str(e).encode("utf-8", "replace")
        time.sleep(1.0)
    else:
        fail("Extraction failed:\n" + last_err.decode("utf-8", "replace")[-1200:])
        return 3

    exe = os.path.join(target, "OmniView.exe")
    if not os.path.exists(exe):
        fail("OmniView.exe was not extracted.")
        return 5
    # Remember the last successfully extracted runtime for diagnostics.
    try:
        with open(os.path.join(ROOT, "current.txt"), "w", encoding="utf-8") as f:
            f.write(target + "\n")
    except Exception:
        pass
    subprocess.Popen([exe], cwd=target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
