"""Tiny self-extracting launcher for OmniView 0.3.

The real payload (payload.7z) and 7z.exe are bundled by PyInstaller.  At
runtime this launcher extracts the payload to %LOCALAPPDATA%\\OmniView\\0.3
and starts the native app.
"""
from __future__ import annotations

import ctypes
import os
import subprocess
import sys
import time

DEST = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "OmniView", "0.3")


def fail(msg: str) -> None:
    try:
        ctypes.windll.user32.MessageBoxW(None, msg, "OmniView Setup", 0x10)
    except Exception:
        pass


def main() -> int:
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    seven = os.path.join(base, "assets", "7z", "7z.exe")
    payload = os.path.join(base, "payload.7z")
    if not os.path.exists(seven) or not os.path.exists(payload):
        fail("Installer payload is missing.")
        return 2
    os.makedirs(DEST, exist_ok=True)
    try:
        # A previous OmniView may still own Qt6Core.dll / python3.dll.
        # taskkill is precise about the image name and avoids the
        # "Cannot delete output file" extraction error.
        subprocess.run(
            ["taskkill", "/F", "/IM", "OmniView.exe"],
            creationflags=0x08000000,
            capture_output=True,
        )
        time.sleep(1.0)
    except Exception:
        pass
    try:
        r = subprocess.run(
            [seven, "x", "-y", "-aoa", f"-o{DEST}", payload],
            cwd=base,
            creationflags=0x08000000,
            capture_output=True,
        )
        if r.returncode != 0:
            fail("Extraction failed:\n" + r.stderr.decode("utf-8", "replace")[-1200:])
            return 3
    except Exception as e:
        fail(f"Extraction failed:\n{e}")
        return 4
    exe = os.path.join(DEST, "OmniView.exe")
    if not os.path.exists(exe):
        fail("OmniView.exe was not extracted.")
        return 5
    subprocess.Popen([exe], cwd=DEST, close_fds=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

