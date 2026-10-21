"""On-demand plugin manager for .ovp packages (OmniView 0.3).

An .ovp is a zip:

  plugin.json
  plugin.py            (optional custom viewer factory)
  site-packages/       (optional dependencies)

plugin.json:
  id, name, version, formats, entry (optional), factory (optional), api
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import shutil
import sys
import urllib.request
import zipfile

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import QDialog, QLabel, QProgressBar, QVBoxLayout, QMessageBox

from . import paths

PLUGIN_BASE_URL = os.environ.get(
    "OMNIVIEW_PLUGIN_BASE",
    "https://github.com/USER/OmniView/releases/download/plugins-v0.3",
)

CATALOG = {
    "office": {
        "name": "Office 文档", "en": "Office Documents",
        "desc": "DOCX / ODT / RTF / XLSX / PPTX / ODP 原生解析，无需 Office/WPS。",
        "size": "约 7 MB",
        "formats": {"docx", "odt", "rtf", "xlsx", "pptx", "odp"},
    },
    "ebook": {
        "name": "电子书", "en": "E-books",
        "desc": "EPUB / MOBI / AZW3 拆包与阅读。",
        "size": "约 2 MB",
        "formats": {"epub", "mobi", "azw3"},
    },
    "data": {
        "name": "数据与模型", "en": "Data & Models",
        "desc": "Access / DBF / HDF5 / ONNX / PT / PKL / TFLite / 邮件库。",
        "size": "约 30 MB",
        "formats": {"mdb", "accdb", "dbf", "h5", "hdf5", "onnx", "pt", "pth", "pkl",
                    "tflite", "pb", "msg", "pst", "ost", "mbox"},
    },
    "pro": {
        "name": "3D / CAD / GIS", "en": "3D / CAD / GIS",
        "desc": "STL/OBJ/GLB、DXF、SHP/KML/GPX、EXE/ELF、字体。",
        "size": "约 12 MB",
        "formats": {"stl", "obj", "glb", "gltf", "3mf", "fbx", "usdz", "dxf", "dwg",
                    "shp", "shx", "prj", "kml", "kmz", "geojson", "gpx",
                    "exe", "dll", "so", "dylib", "sys", "ttf", "otf", "woff", "woff2", "step", "stp"},
    },
    "raw": {
        "name": "RAW / PSD", "en": "RAW / PSD",
        "desc": "相机 RAW、Photoshop PSD、AI 的增强解码。",
        "size": "约 15 MB",
        "formats": {"psd", "psb", "ai", "raw", "cr2", "cr3", "nef", "arw", "dng", "orf", "rw2", "raf", "pef", "srw"},
    },
}

FORMAT_PLUGIN = {}
for _pid, _info in CATALOG.items():
    for _ext in _info["formats"]:
        FORMAT_PLUGIN[_ext] = _pid

ID_RE = re.compile(r"^[a-zA-Z0-9_.-]{1,64}$")


class PluginError(RuntimeError):
    pass


def plugin_root() -> str:
    d = os.path.join(paths.DATA, "plugins")
    os.makedirs(d, exist_ok=True)
    return d


def plugin_dir(pid: str) -> str:
    if not ID_RE.match(pid or ""):
        raise PluginError(f"非法插件 id：{pid!r}")
    return os.path.join(plugin_root(), pid)


def installed(pid: str) -> bool:
    try:
        return os.path.isfile(os.path.join(plugin_dir(pid), "plugin.json"))
    except PluginError:
        return False


def installed_ids() -> list[str]:
    out = []
    root = plugin_root()
    try:
        for name in os.listdir(root):
            if os.path.isfile(os.path.join(root, name, "plugin.json")):
                out.append(name)
    except OSError:
        pass
    return out


def info(pid: str) -> dict:
    try:
        p = os.path.join(plugin_dir(pid), "plugin.json")
        return json.load(open(p, "r", encoding="utf-8-sig"))
    except Exception:
        return {}


def plugin_for(ext: str) -> str | None:
    ext = ext.lower().lstrip(".")
    # installed/user plugins take precedence, then the built-in catalog
    for pid in installed_ids():
        formats = info(pid).get("formats") or []
        if ext in {str(x).lower().lstrip(".") for x in formats}:
            return pid
    return FORMAT_PLUGIN.get(ext)


def preload_installed() -> None:
    for pid in installed_ids():
        try:
            activate(pid)
        except Exception:
            pass


def activate(pid: str) -> bool:
    d = plugin_dir(pid)
    if not installed(pid):
        return False
    for p in (os.path.join(d, "site-packages"), d):
        if os.path.isdir(p) and p not in sys.path:
            sys.path.insert(0, p)
    return True


def factory(pid: str):
    """Return the plugin's create_viewer callable, or None for dependency packs."""
    meta = info(pid)
    entry = (meta.get("entry") or "").strip()
    if not entry:
        return None
    activate(pid)
    d = plugin_dir(pid)
    module = None
    # file entry (recommended for user-made OVPs)
    candidates = []
    if entry.endswith(".py"):
        candidates.append(os.path.join(d, *entry.split("/")))
    else:
        candidates.append(os.path.join(d, *entry.split("/")) + ".py")
        candidates.append(os.path.join(d, *entry.split("/"), "__init__.py"))
    for p in candidates:
        if os.path.isfile(p):
            try:
                spec = importlib.util.spec_from_file_location(f"ovp_{pid}", p)
                module = importlib.util.module_from_spec(spec)
                sys.modules[f"ovp_{pid}"] = module
                spec.loader.exec_module(module)
            except Exception as e:
                raise PluginError(f"插件 {pid} 的 {entry} 导入失败：{e}") from e
            break
    if module is None:
        try:
            module = __import__(entry, fromlist=["*"])
        except Exception as e:
            raise PluginError(f"插件 {pid} 的入口 {entry!r} 不存在或导入失败：{e}") from e
    fname = (meta.get("factory") or "create_viewer").strip()
    fn = getattr(module, fname, None)
    if not callable(fn):
        raise PluginError(f"插件 {pid} 的入口 {entry!r} 没有可调用的 {fname}()")
    return fn


def validate_manifest(meta: dict, zip_names: set[str] | None = None) -> dict:
    if not isinstance(meta, dict):
        raise PluginError("plugin.json 必须是 JSON 对象")
    pid = str(meta.get("id") or "").strip()
    if not ID_RE.match(pid):
        raise PluginError("plugin.json 缺少合法 id（只能包含字母、数字、_ . -）")
    name = str(meta.get("name") or "").strip()
    if not name:
        raise PluginError("plugin.json 缺少 name")
    formats = meta.get("formats") or []
    if not isinstance(formats, list) or not formats:
        raise PluginError("plugin.json 的 formats 必须是非空数组")
    meta["id"] = pid
    meta["name"] = name
    meta["version"] = str(meta.get("version") or "0.0.0")
    meta["formats"] = [str(x).lower().lstrip(".") for x in formats if str(x).strip()]
    entry = str(meta.get("entry") or "").strip()
    if entry:
        if ".." in entry.replace("\\", "/").split("/"):
            raise PluginError("entry 不能包含 ..")
        if zip_names is not None:
            e = entry.replace("\\", "/")
            if e.endswith(".py"):
                ok = e in zip_names
            else:
                ok = e + ".py" in zip_names or e + "/__init__.py" in zip_names
            if not ok:
                raise PluginError(f"entry 指向的文件不在包内：{entry}")
    meta["entry"] = entry
    meta["factory"] = str(meta.get("factory") or "create_viewer")
    meta["api"] = int(meta.get("api") or 1)
    return meta


def validate_zip(path: str) -> dict:
    try:
        with zipfile.ZipFile(path) as z:
            names = set(z.namelist())
            if "plugin.json" not in names:
                raise PluginError("不是有效的 .ovp：根目录缺少 plugin.json")
            try:
                meta = json.loads(z.read("plugin.json").decode("utf-8-sig"))
            except Exception as e:
                raise PluginError(f"plugin.json 解析失败：{e}") from e
            return validate_manifest(meta, names)
    except zipfile.BadZipFile as e:
        raise PluginError("不是有效的 .ovp（不是 zip 压缩包）") from e


def install_zip(pid: str | None, zip_path: str) -> dict:
    meta = validate_zip(zip_path)
    real_pid = meta["id"]
    if pid and pid != real_pid:
        # The manifest is authoritative; callers usually pass the same id.
        pass
    d = plugin_dir(real_pid)
    tmp = d + ".tmp"
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp, exist_ok=True)
    with zipfile.ZipFile(zip_path) as z:
        for zi in z.infolist():
            name = zi.filename.replace("\\", "/")
            if name.startswith("/") or ".." in name.split("/"):
                continue
            target = os.path.join(tmp, *name.split("/"))
            os.makedirs(os.path.dirname(target), exist_ok=True)
            if not zi.is_dir():
                with z.open(zi) as src, open(target, "wb") as dst:
                    shutil.copyfileobj(src, dst)
    shutil.rmtree(d, ignore_errors=True)
    os.replace(tmp, d)
    activate(real_pid)
    return meta


def remove(pid: str) -> None:
    shutil.rmtree(plugin_dir(pid), ignore_errors=True)


def catalog_entry(pid: str) -> dict:
    meta = info(pid)
    base = CATALOG.get(pid, {})
    return {
        "id": pid,
        "name": meta.get("name") or base.get("name") or pid,
        "desc": base.get("desc") or "用户插件",
        "size": base.get("size") or "自定义",
        "formats": meta.get("formats") or base.get("formats") or [],
        "installed": installed(pid),
        "version": meta.get("version", ""),
        "path": plugin_dir(pid) if installed(pid) else "",
        "custom": pid not in CATALOG,
    }


class _Download(QThread):
    progress = Signal(int)
    done = Signal(str)
    failed = Signal(str)

    def __init__(self, pid, dest):
        super().__init__()
        self.pid = pid
        self.dest = dest

    def run(self):
        try:
            local_candidates = [
                os.path.join(paths.bundled("plugins"), self.pid + ".ovp"),
                os.path.join(os.path.dirname(sys.executable), "plugins", self.pid + ".ovp"),
                os.path.join(paths.DATA, "plugins", self.pid + ".ovp"),
            ]
            local = next((p for p in local_candidates if os.path.exists(p)), None)
            if local:
                self.progress.emit(100)
                self.done.emit(local)
                return
            url = f"{PLUGIN_BASE_URL}/{self.pid}.ovp"
            tmp = self.dest + ".part"
            with urllib.request.urlopen(url, timeout=45) as r, open(tmp, "wb") as f:
                total = int(r.headers.get("Content-Length") or 0)
                got = 0
                while True:
                    chunk = r.read(256 * 1024)
                    if not chunk:
                        break
                    f.write(chunk)
                    got += len(chunk)
                    if total:
                        self.progress.emit(min(99, int(got * 100 / total)))
            self.done.emit(tmp)
        except Exception as e:
            self.failed.emit(str(e))


class InstallDialog(QDialog):
    """Download a catalog plugin, then install it."""

    def __init__(self, pid, parent=None):
        super().__init__(parent)
        self.pid = pid
        self.setWindowTitle("OmniView · Plugin")
        self.resize(460, 150)
        lay = QVBoxLayout(self)
        name = CATALOG.get(pid, {}).get("name", pid)
        lay.addWidget(QLabel(f"正在安装插件：{name}"))
        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        lay.addWidget(self.bar)
        self.msg = QLabel("下载中…")
        self.msg.setStyleSheet("color:#91a4bd;font-size:9pt;")
        lay.addWidget(self.msg)
        self.ok = False
        self.dest = os.path.join(plugin_root(), pid + ".ovp")
        self.thread = _Download(pid, self.dest)
        self.thread.progress.connect(self.bar.setValue)
        self.thread.done.connect(self._done)
        self.thread.failed.connect(self._failed)
        self.thread.start()

    def _done(self, path):
        try:
            self.bar.setValue(100)
            self.msg.setText("解压并启用…")
            install_zip(self.pid, path)
            self.ok = True
            self.accept()
        except Exception as e:
            self._failed(str(e))

    def _failed(self, msg):
        self.msg.setText("安装失败：" + msg)
        QMessageBox.warning(self, "插件安装失败", f"{msg}\n\n插件目录：\n{plugin_root()}")
        self.reject()

