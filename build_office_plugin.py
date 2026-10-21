"""Build the Office .ovp plugin from installed pure-Python dependencies."""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import zipfile

ROOT = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.join(ROOT, "plugins", "office")
SITE = os.path.join(PLUGIN, "site-packages")

MODULES = ["mammoth", "cobble", "docx", "openpyxl", "et_xmlfile", "pptx", "odf", "striprtf", "lxml"]


def main() -> int:
    shutil.rmtree(PLUGIN, ignore_errors=True)
    os.makedirs(SITE, exist_ok=True)
    missing = []
    for name in MODULES:
        spec = importlib.util.find_spec(name)
        if not spec or not spec.origin:
            missing.append(name)
            continue
        src = os.path.dirname(spec.origin) if spec.submodule_search_locations else spec.origin
        dst = os.path.join(SITE, name if spec.submodule_search_locations else os.path.basename(spec.origin))
        if os.path.isdir(src):
            shutil.copytree(src, dst, dirs_exist_ok=True)
        else:
            shutil.copy2(src, dst)
        print("copied", name)
    if missing:
        print("optional/missing:", ", ".join(missing))
    json.dump({
        "id": "office",
        "name": "Office 文档",
        "version": "0.3.0",
        "formats": ["docx", "odt", "rtf", "xlsx", "pptx", "odp"],
        "entry": "",
    }, open(os.path.join(PLUGIN, "plugin.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    out = os.path.join(ROOT, "plugins", "office.ovp")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for base, _dirs, files in os.walk(PLUGIN):
            for f in files:
                p = os.path.join(base, f)
                z.write(p, os.path.relpath(p, PLUGIN))
    print(f"built {out} ({os.path.getsize(out) / 1024 / 1024:.1f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

