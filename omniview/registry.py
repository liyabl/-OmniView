# -*- coding: utf-8 -*-
"""万象查看器 · 格式注册表

每一个扩展名都归属到一个「馆」，并给出细分的 kind。
kind 决定前端采用哪一种展示方式，而不是简单按扩展名猜测。
"""
from __future__ import annotations

import os

APPS = {
    "doc": {
        "name": "文档馆",
        "en": "Documents",
        "glyph": "文",
        "accent": "#7aa2ff",
        "accent2": "#5b7cfa",
        "tagline": "版式原样，逐页阅读",
        "desc": "PDF、Office、OpenDocument、电子书、Markdown 与 TeX",
    },
    "image": {
        "name": "图像馆",
        "en": "Images",
        "glyph": "图",
        "accent": "#4fd1c5",
        "accent2": "#22a699",
        "tagline": "像素、图层与暗房",
        "desc": "常见图片、SVG、PSD、AI 与相机 RAW",
    },
    "media": {
        "name": "影音馆",
        "en": "Media",
        "glyph": "音",
        "accent": "#f6ad55",
        "accent2": "#ed8936",
        "tagline": "原声原画，随点随播",
        "desc": "音频、视频、MIDI 与字幕",
    },
    "archive": {
        "name": "压缩馆",
        "en": "Archives",
        "glyph": "档",
        "accent": "#b794f4",
        "accent2": "#9f7aea",
        "tagline": "不必解压，直接翻阅",
        "desc": "ZIP、7Z、RAR、TAR、ISO、DMG、CAB 与 JAR",
    },
    "code": {
        "name": "代码馆",
        "en": "Code",
        "glyph": "码",
        "accent": "#68d391",
        "accent2": "#38a169",
        "tagline": "语法着色，即刻编辑",
        "desc": "40+ 种编程语言、配置、日志与 Notebook",
    },
    "data": {
        "name": "数据馆",
        "en": "Data",
        "glyph": "数",
        "accent": "#63b3ed",
        "accent2": "#3182ce",
        "tagline": "表格、模型与邮件",
        "desc": "SQLite、Access、DBF、HDF5、ONNX、PT、PKL 与邮件库",
    },
    "pro": {
        "name": "专业馆",
        "en": "Pro Studio",
        "glyph": "专",
        "accent": "#f687b3",
        "accent2": "#d53f8c",
        "tagline": "三维、图纸与空间数据",
        "desc": "CAD、3D、GIS、可执行文件、字体与安装包",
    },
}

# app -> {ext: kind}
_GROUPS: dict[str, dict[str, str]] = {
    "doc": {
        "pdf": "pdf",
        "docx": "word",
        "odt": "word",
        "rtf": "word",
        "md": "markdown",
        "markdown": "markdown",
        "txt": "text",
        "text": "text",
        "xlsx": "sheet",
        "xlsm": "sheet",
        "csv": "csv",
        "tsv": "csv",
        "pptx": "slides",
        "odp": "slides",
        "epub": "epub",
        "mobi": "mobi",
        "azw3": "mobi",
        "tex": "tex",
        "latex": "tex",
    },
    "image": {
        "jpg": "image",
        "jpeg": "image",
        "jpe": "image",
        "png": "image",
        "gif": "image",
        "webp": "image",
        "bmp": "image",
        "tif": "tiff",
        "tiff": "tiff",
        "ico": "icon",
        "svg": "svg",
        "psd": "psd",
        "psb": "psd",
        "ai": "ai",
        "raw": "raw",
        "cr2": "raw",
        "cr3": "raw",
        "nef": "raw",
        "arw": "raw",
        "dng": "raw",
        "orf": "raw",
        "rw2": "raw",
        "raf": "raw",
        "pef": "raw",
        "srw": "raw",
    },
    "media": {
        "mp3": "audio",
        "aac": "audio",
        "m4a": "audio",
        "flac": "audio",
        "wav": "audio",
        "ogg": "audio",
        "oga": "audio",
        "opus": "audio",
        "aiff": "audio",
        "aif": "audio",
        "wma": "audio",
        "ape": "audio",
        "mid": "midi",
        "midi": "midi",
        "mp4": "video",
        "mkv": "video",
        "webm": "video",
        "mov": "video",
        "m4v": "video",
        "avi": "video",
        "wmv": "video",
        "flv": "video",
        "rmvb": "video",
        "rm": "video",
        "mpg": "video",
        "mpeg": "video",
        "ts": "video",
        "m2ts": "video",
        "vob": "video",
        "ogv": "video",
    },
    "archive": {
        "zip": "archive",
        "7z": "archive",
        "rar": "archive",
        "tar": "archive",
        "gz": "archive",
        "gzip": "archive",
        "bz2": "archive",
        "xz": "archive",
        "tgz": "archive",
        "tbz2": "archive",
        "txz": "archive",
        "zst": "archive",
        "iso": "archive",
        "img": "archive",
        "dmg": "archive",
        "cab": "archive",
        "jar": "archive",
        "war": "archive",
        "whl": "archive",
        "apk": "package",
        "xapk": "package",
    },
    "code": {
        "c": "code",
        "h": "code",
        "cpp": "code",
        "cxx": "code",
        "cc": "code",
        "hpp": "code",
        "hh": "code",
        "cs": "code",
        "java": "code",
        "py": "code",
        "pyw": "code",
        "js": "code",
        "mjs": "code",
        "cjs": "code",
        "jsx": "code",
        "ts": "code",
        "tsx": "code",
        "vue": "code",
        "svelte": "code",
        "html": "html",
        "htm": "html",
        "xhtml": "html",
        "css": "code",
        "scss": "code",
        "sass": "code",
        "less": "code",
        "php": "code",
        "rb": "code",
        "go": "code",
        "rs": "code",
        "kt": "code",
        "kts": "code",
        "swift": "code",
        "lua": "code",
        "r": "code",
        "sql": "sql",
        "json": "json",
        "jsonl": "json",
        "geojson": "json",
        "xml": "xml",
        "xsd": "xml",
        "xsl": "xml",
        "yaml": "yaml",
        "yml": "yaml",
        "toml": "toml",
        "ini": "config",
        "cfg": "config",
        "conf": "config",
        "properties": "config",
        "env": "config",
        "sh": "code",
        "bash": "code",
        "zsh": "code",
        "fish": "code",
        "bat": "code",
        "cmd": "code",
        "ps1": "code",
        "psm1": "code",
        "ipynb": "notebook",
        "log": "log",
        "bak": "text",
        "tmp": "text",
        "diff": "code",
        "patch": "code",
        "cmake": "code",
        "mk": "code",
        "dockerfile": "code",
    },
    "data": {
        "db": "sqlite",
        "sqlite": "sqlite",
        "sqlite3": "sqlite",
        "db3": "sqlite",
        "mdb": "access",
        "accdb": "access",
        "dbf": "dbf",
        "frm": "mysqlfile",
        "myd": "mysqlfile",
        "myi": "mysqlfile",
        "ibd": "mysqlfile",
        "mdf": "sqlserverfile",
        "ldf": "sqlserverfile",
        "ora": "oraclefile",
        "h5": "hdf5",
        "hdf5": "hdf5",
        "hdf": "hdf5",
        "onnx": "onnx",
        "pt": "torch",
        "pth": "torch",
        "pkl": "pickle",
        "pickle": "pickle",
        "tflite": "tflite",
        "pb": "protobuf",
        "eml": "email",
        "msg": "msg",
        "pst": "pst",
        "ost": "pst",
        "mbox": "mbox",
        "mbx": "mbox",
    },
    "pro": {
        "dwg": "dwg",
        "dxf": "dxf",
        "stl": "model3d",
        "step": "step",
        "stp": "step",
        "iges": "step",
        "igs": "step",
        "obj": "model3d",
        "fbx": "model3d",
        "glb": "model3d",
        "gltf": "model3d",
        "usdz": "model3d",
        "3mf": "model3d",
        "blend": "blend",
        "skp": "skp",
        "shp": "shp",
        "shx": "shp",
        "prj": "prj",
        "kml": "kml",
        "kmz": "kml",
        "geojson": "geojson",
        "gpx": "gpx",
        "exe": "pe",
        "dll": "pe",
        "sys": "pe",
        "scr": "pe",
        "cpl": "pe",
        "ocx": "pe",
        "msi": "msi",
        "msix": "package",
        "appx": "package",
        "app": "macapp",
        "deb": "deb",
        "rpm": "rpm",
        "so": "elf",
        "dylib": "macho",
        "ttf": "font",
        "otf": "font",
        "ttc": "font",
        "woff": "font",
        "woff2": "font",
        "eot": "font",
    },
}

EXT_APP: dict[str, str] = {}
EXT_KIND: dict[str, str] = {}
for _app, _m in _GROUPS.items():
    for _ext, _kind in _m.items():
        EXT_APP[_ext] = _app
        EXT_KIND[_ext] = _kind

# 双扩展名优先
MULTI_EXT = {
    "tar.gz": ("archive", "archive"),
    "tar.bz2": ("archive", "archive"),
    "tar.xz": ("archive", "archive"),
    "tar.zst": ("archive", "archive"),
    "tar.lz": ("archive", "archive"),
    "tar.lzma": ("archive", "archive"),
    "app.tar.gz": ("archive", "archive"),
}

KIND_LABEL = {
    "pdf": "PDF 文档", "word": "文字文档", "sheet": "电子表格", "csv": "CSV 表格",
    "slides": "演示文稿", "markdown": "Markdown", "text": "纯文本", "tex": "TeX 排版",
    "epub": "EPUB 电子书", "mobi": "Kindle 电子书",
    "image": "位图图像", "tiff": "TIFF 图像", "icon": "图标", "svg": "矢量图",
    "psd": "Photoshop 文档", "ai": "Illustrator 文档", "raw": "相机 RAW",
    "audio": "音频", "midi": "MIDI 音乐", "video": "视频",
    "archive": "压缩包", "package": "安装包",
    "code": "源代码", "html": "网页", "json": "JSON", "xml": "XML", "yaml": "YAML",
    "toml": "TOML", "config": "配置文件", "log": "日志", "notebook": "Jupyter Notebook",
    "sqlite": "SQLite 数据库", "access": "Access 数据库", "dbf": "DBF 数据表",
    "mysqlfile": "MySQL 数据文件", "sqlserverfile": "SQL Server 数据文件",
    "oraclefile": "Oracle 数据文件", "hdf5": "HDF5 科学数据", "onnx": "ONNX 模型",
    "torch": "PyTorch 权重", "pickle": "Pickle 对象", "tflite": "TFLite 模型",
    "protobuf": "Protocol Buffers", "email": "电子邮件", "msg": "Outlook 邮件",
    "pst": "Outlook 数据文件", "mbox": "MBOX 邮件库",
    "dwg": "AutoCAD 图纸", "dxf": "DXF 图纸", "model3d": "三维模型", "step": "STEP 模型",
    "blend": "Blender 工程", "skp": "SketchUp 模型", "shp": "Shapefile",
    "prj": "坐标参考", "kml": "KML 地理数据", "geojson": "GeoJSON", "gpx": "GPX 轨迹",
    "pe": "Windows 可执行文件", "elf": "ELF 二进制", "macho": "Mach-O 二进制",
    "msi": "Windows 安装包", "macapp": "macOS 应用包", "deb": "Debian 包", "rpm": "RPM 包",
    "font": "字体",
    "unsupported": "未知格式",
}

# 前端 tab / 文件浏览器用的短标签
SHORT = {
    "pdf": "PDF", "word": "DOC", "sheet": "XLS", "csv": "CSV", "slides": "PPT",
    "markdown": "MD", "text": "TXT", "tex": "TEX", "epub": "EPUB", "mobi": "MOBI",
    "image": "IMG", "tiff": "TIF", "icon": "ICO", "svg": "SVG", "psd": "PSD",
    "ai": "AI", "raw": "RAW", "audio": "AUD", "midi": "MID", "video": "VID",
    "archive": "ZIP", "package": "PKG", "code": "CODE", "html": "HTML", "json": "JSON",
    "xml": "XML", "yaml": "YAML", "toml": "TOML", "config": "CFG", "log": "LOG",
    "notebook": "IPYNB", "sqlite": "DB", "access": "MDB", "dbf": "DBF",
    "mysqlfile": "MYD", "sqlserverfile": "MDF", "oraclefile": "ORA", "hdf5": "H5",
    "onnx": "ONNX", "torch": "PT", "pickle": "PKL", "tflite": "TFL", "protobuf": "PB",
    "email": "EML", "msg": "MSG", "pst": "PST", "mbox": "MBOX", "dwg": "DWG",
    "dxf": "DXF", "model3d": "3D", "step": "STEP", "blend": "BLEND", "skp": "SKP",
    "shp": "SHP", "prj": "PRJ", "kml": "KML", "geojson": "GEO", "gpx": "GPX",
    "pe": "EXE", "elf": "ELF", "macho": "DYLIB", "msi": "MSI", "macapp": "APP",
    "deb": "DEB", "rpm": "RPM", "font": "FONT",
}


def split_ext(name: str) -> str:
    """返回小写扩展名；识别 .tar.gz 之类的双扩展名。"""
    lower = name.lower()
    for multi in sorted(MULTI_EXT, key=len, reverse=True):
        if lower.endswith("." + multi):
            return multi
    base = os.path.basename(lower)
    if "." not in base:
        # Dockerfile / Makefile 之类的特例
        if base in {"dockerfile", "makefile", "cmakelists.txt", "gemfile", "rakefile"}:
            return base
        return ""
    return base.rsplit(".", 1)[-1]


def resolve(name: str) -> tuple[str, str]:
    """(app, kind)。未知扩展名归到代码馆的文本/十六进制视图。"""
    ext = split_ext(name)
    if ext in MULTI_EXT:
        return MULTI_EXT[ext]
    if ext in EXT_APP:
        return EXT_APP[ext], EXT_KIND[ext]
    base = os.path.basename(name.lower())
    if base in {"dockerfile", "makefile", "cmakelists.txt", "gemfile", "rakefile", "license", "readme"}:
        return "code", "code"
    return "code", "unknown"


def kind_label(kind: str) -> str:
    return KIND_LABEL.get(kind, "文件")


def short(kind: str, ext: str = "") -> str:
    if kind in SHORT:
        return SHORT[kind]
    return (ext or "FILE").upper()[:5]


def app_meta(app: str) -> dict:
    return APPS.get(app, APPS["code"])
