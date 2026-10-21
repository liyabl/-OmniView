"""Build a user-made .ovp plugin package.

Examples:
  python build_ovp.py --template myplugin
  python build_ovp.py --source plugins/hello --out plugins/hello.ovp
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import zipfile

ID_RE = re.compile(r"^[a-zA-Z0-9_.-]{1,64}$")

TEMPLATE_MANIFEST = {
    "id": "hello",
    "name": "Hello Viewer",
    "version": "1.0.0",
    "api": 1,
    "formats": ["hello"],
    "entry": "plugin.py",
    "factory": "create_viewer",
}

TEMPLATE_PLUGIN = '''"""Example OmniView plugin. Must return a ViewerBase subclass."""
from __future__ import annotations

import os

from PySide6.QtWidgets import QLabel, QVBoxLayout

from omniview.ui.common import ViewerBase


class HelloViewer(ViewerBase):
    def __init__(self, path, parent=None):
        super().__init__(path, parent)
        text = open(path, "r", encoding="utf-8", errors="replace").read()
        label = QLabel(text)
        label.setWordWrap(True)
        label.setStyleSheet("font-size:15pt;color:#e6edf7;padding:32px;")
        self.root.addWidget(label, 1)
        self.info = {"格式": "HELLO", "插件": "hello", "大小": os.path.getsize(path)}


def create_viewer(path, parent=None):
    return HelloViewer(path, parent)
'''


def create_template(target: str) -> None:
    os.makedirs(target, exist_ok=True)
    json.dump(TEMPLATE_MANIFEST, open(os.path.join(target, "plugin.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    open(os.path.join(target, "plugin.py"), "w", encoding="utf-8").write(TEMPLATE_PLUGIN)
    open(os.path.join(target, "README.txt"), "w", encoding="utf-8").write(
        "1. Edit plugin.json and plugin.py.\n"
        "2. Run: python build_ovp.py --source . --out hello.ovp\n"
        "3. Install hello.ovp from OmniView -> Help -> Plugin Manager.\n"
        "4. Open a .hello file.\n"
    )
    print(f"template created: {target}")


def build(source: str, out: str) -> None:
    manifest_path = os.path.join(source, "plugin.json")
    if not os.path.exists(manifest_path):
        raise SystemExit("source must contain plugin.json")
    meta = json.load(open(manifest_path, "r", encoding="utf-8-sig"))
    if not ID_RE.match(str(meta.get("id", ""))):
        raise SystemExit("plugin.json id is invalid")
    entry = str(meta.get("entry") or "")
    if entry and not os.path.exists(os.path.join(source, entry.replace("/", os.sep))):
        raise SystemExit(f"entry does not exist: {entry}")
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for base, _dirs, files in os.walk(source):
            for f in files:
                p = os.path.join(base, f)
                rel = os.path.relpath(p, source).replace(os.sep, "/")
                z.write(p, rel)
    print(f"built {out} ({os.path.getsize(out)/1024:.1f} KB)")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--template", help="create a starter template directory")
    ap.add_argument("--source", help="directory containing plugin.json")
    ap.add_argument("--out", help="output .ovp")
    a = ap.parse_args()
    if a.template:
        create_template(a.template)
    if a.source and a.out:
        build(a.source, a.out)
    if not a.template and not (a.source and a.out):
        ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

