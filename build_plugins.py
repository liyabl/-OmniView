"""Build the independent .ovp plugins from installed packages.

Usage:  python build_plugins.py
Output: plugins/ebook.ovp, data.ovp, pro.ovp, raw.ovp
"""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import site
import sys
import sysconfig
import zipfile

ROOT = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(ROOT, "build_plugins")
OUT = os.path.join(ROOT, "plugins")

SITE_ROOTS = []
for p in [sysconfig.get_paths().get("purelib"), sysconfig.get_paths().get("platlib"),
          *site.getsitepackages(), site.getusersitepackages(), *sys.path]:
    if p and os.path.isdir(p) and p not in SITE_ROOTS:
        SITE_ROOTS.append(p)

PKGS = {
    "ebook": ["mobi", "loguru", "imghdr", "unidecode"],
    "data": ["h5py", "onnx", "google", "ml_dtypes", "tflite", "flatbuffers", "dbf", "aenum",
             "access_parser", "construct", "tabulate", "extract_msg", "olefile", "tzlocal",
             "compressed_rtf", "ebcdic", "bs4", "RTFDE", "red_black_dict_mod", "red_black_set_mod", "chardet"],
    "pro": ["ezdxf", "pyparsing", "shapefile", "fontTools", "pefile", "elftools",
            "macholib", "altgraph", "rpmfile", "zstandard"],
    "raw": ["rawpy", "psd_tools", "attrs"],
}
FORMATS = {
    "ebook": ["epub", "mobi", "azw3"],
    "data": ["mdb", "accdb", "dbf", "h5", "hdf5", "onnx", "pt", "pth", "pkl", "tflite", "pb",
             "msg", "pst", "ost", "mbox"],
    "pro": ["stl", "obj", "glb", "gltf", "3mf", "fbx", "usdz", "dxf", "dwg", "shp", "shx", "prj",
            "kml", "kmz", "geojson", "gpx", "exe", "dll", "so", "dylib", "sys", "ttf", "otf",
            "woff", "woff2", "step", "stp"],
    "raw": ["psd", "psb", "ai", "raw", "cr2", "cr3", "nef", "arw", "dng", "orf", "rw2", "raf", "pef", "srw"],
}
NAMES = {"ebook": "电子书", "data": "数据与模型", "pro": "3D / CAD / GIS", "raw": "RAW / PSD"}


def _find_dir(name: str) -> str | None:
    spec = importlib.util.find_spec(name)
    if spec and spec.origin:
        return os.path.dirname(spec.origin) if spec.submodule_search_locations else spec.origin
    for root in SITE_ROOTS:
        for cand in (os.path.join(root, name), os.path.join(root, name + ".py")):
            if os.path.exists(cand):
                return cand
    return None


def copy_name(name: str, dest: str) -> bool:
    src = _find_dir(name)
    if not src:
        return False
    target = os.path.join(dest, os.path.basename(src) if os.path.isfile(src) else name)
    if os.path.isdir(src):
        shutil.copytree(src, target, dirs_exist_ok=True)
    else:
        shutil.copy2(src, target)
    return True


def main() -> int:
    shutil.rmtree(BUILD, ignore_errors=True)
    os.makedirs(BUILD, exist_ok=True)
    os.makedirs(OUT, exist_ok=True)
    for pid, pkgs in PKGS.items():
        d = os.path.join(BUILD, pid)
        site_dir = os.path.join(d, "site-packages")
        os.makedirs(site_dir, exist_ok=True)
        missing = [name for name in pkgs if not copy_name(name, site_dir)]
        for side in ("rawpy.libs", "psd_tools.libs", "h5py.libs"):
            src = _find_dir(side)
            if src and os.path.isdir(src):
                shutil.copytree(src, os.path.join(site_dir, side), dirs_exist_ok=True)
        # google is a namespace package (find_spec returns origin=None)
        if pid == "data" and not os.path.isdir(os.path.join(site_dir, "google")):
            for root in SITE_ROOTS:
                src = os.path.join(root, "google")
                if os.path.isdir(src):
                    shutil.copytree(src, os.path.join(site_dir, "google"))
                    break
        manifest = {"id": pid, "name": NAMES[pid], "version": "0.3.0",
                    "formats": FORMATS[pid], "entry": ""}
        json.dump(manifest, open(os.path.join(d, "plugin.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        out = os.path.join(OUT, pid + ".ovp")
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
            for base, _dirs, files in os.walk(d):
                for f in files:
                    p = os.path.join(base, f)
                    z.write(p, os.path.relpath(p, d))
        print(pid, "missing:", missing, "size:", round(os.path.getsize(out) / 1024 / 1024, 1), "MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
