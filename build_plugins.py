"""Build the independent .ovp plugins from installed packages.

Usage:  python build_plugins.py
Output: plugins/ebook.ovp, data.ovp, pro.ovp, raw.ovp

Each plugin contains its dependencies plus LICENSE files.  A smoke import is
run before packaging; missing modules abort the build instead of failing later
when a user opens a file.
"""
from __future__ import annotations

import importlib.metadata as md
import importlib.util
import json
import os
import shutil
import site
import subprocess
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
             "compressed_rtf", "ebcdic", "bs4", "RTFDE", "red_black_dict_mod",
             "red_black_set_mod", "chardet"],
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
    "raw": ["psd", "psb", "ai", "raw", "cr2", "cr3", "nef", "arw", "dng", "orf", "rw2", "raf",
            "pef", "srw"],
}
NAMES = {"ebook": "电子书", "data": "数据与模型", "pro": "3D / CAD / GIS", "raw": "RAW / PSD"}

DIST_NAMES = {
    "ebook": ["mobi", "loguru", "standard-imghdr", "Unidecode"],
    "data": ["h5py", "onnx", "protobuf", "ml-dtypes", "tflite", "flatbuffers", "dbf", "aenum",
             "access-parser", "construct", "tabulate", "extract-msg", "olefile", "tzlocal",
             "compressed-rtf", "ebcdic", "beautifulsoup4", "RTFDE", "red-black-tree-mod",
             "chardet"],
    "pro": ["ezdxf", "pyparsing", "pyshp", "fonttools", "pefile", "pyelftools", "macholib",
            "altgraph", "rpmfile", "zstandard"],
    "raw": ["rawpy", "psd-tools", "attrs", "Pillow", "numpy"],
}


def _find_dir(name: str) -> str | None:
    spec = importlib.util.find_spec(name)
    if spec and spec.origin is not None:
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
        shutil.copytree(src, target, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    else:
        shutil.copy2(src, target)
    return True


def smoke_import(pid: str, site_dir: str, modules: list[str]) -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = site_dir + os.pathsep + env.get("PYTHONPATH", "")
    code = "import importlib\n" + "\n".join(f"importlib.import_module({m!r})" for m in modules)
    r = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True)
    if r.returncode != 0:
        detail = (r.stderr or r.stdout).strip().splitlines()[-5:]
        raise SystemExit(f"{pid}: smoke import failed:\n" + "\n".join(detail))


def copy_licenses(pid: str, dest: str) -> None:
    lic_dir = os.path.join(dest, "licenses")
    os.makedirs(lic_dir, exist_ok=True)
    for name in DIST_NAMES.get(pid, []):
        try:
            dist = md.distribution(name)
        except Exception:
            continue
        target = os.path.join(lic_dir, name)
        os.makedirs(target, exist_ok=True)
        copied = 0
        for f in dist.files or []:
            low = f.name.lower()
            if low.startswith(("license", "copying", "notice", "authors")):
                try:
                    src = dist.locate_file(f)
                    if os.path.isfile(src):
                        shutil.copy2(src, os.path.join(target, f.name))
                        copied += 1
                except Exception:
                    pass
        if not copied:
            text = (dist.metadata.get("License") or "").strip()
            if text:
                with open(os.path.join(target, "LICENSE.txt"), "w", encoding="utf-8") as f:
                    f.write(text + "\n")
    with open(os.path.join(lic_dir, "README.txt"), "w", encoding="utf-8") as f:
        f.write("License files collected from each dependency's installed metadata.\n"
                "Source packages: https://pypi.org/\n")


def main() -> int:
    shutil.rmtree(BUILD, ignore_errors=True)
    os.makedirs(BUILD, exist_ok=True)
    os.makedirs(OUT, exist_ok=True)
    for pid, pkgs in PKGS.items():
        d = os.path.join(BUILD, pid)
        site_dir = os.path.join(d, "site-packages")
        os.makedirs(site_dir, exist_ok=True)
        missing = [name for name in pkgs if not copy_name(name, site_dir)]
        if missing:
            raise SystemExit(f"{pid}: missing dependencies: {', '.join(missing)}")
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
        copy_licenses(pid, d)
        smoke_import(pid, site_dir, [("google.protobuf" if m == "google" else m) for m in pkgs])
        manifest = {"id": pid, "name": NAMES[pid], "version": "0.3.0",
                    "formats": FORMATS[pid], "entry": ""}
        with open(os.path.join(d, "plugin.json"), "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=1)
        out = os.path.join(OUT, pid + ".ovp")
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
            for base, _dirs, files in os.walk(d):
                for f in files:
                    p = os.path.join(base, f)
                    z.write(p, os.path.relpath(p, d))
        print(pid, "size:", round(os.path.getsize(out) / 1024 / 1024, 1), "MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
