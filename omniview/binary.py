"""CAD (DXF) reader and native binary / package inspectors."""
from __future__ import annotations

import os
import re
import struct
import textwrap

from . import textutil


def dxf_info(path: str) -> dict:
    import ezdxf
    doc = ezdxf.readfile(path)
    msp = doc.modelspace()
    ents = []
    types = {}
    for e in msp:
        t = e.dxftype()
        types[t] = types.get(t, 0) + 1
        try:
            if t == "LINE":
                ents.append({"type": "line", "a": list(e.dxf.start)[:2], "b": list(e.dxf.end)[:2], "layer": e.dxf.layer, "color": e.dxf.color})
            elif t == "CIRCLE":
                c = e.dxf.center
                ents.append({"type": "circle", "c": [c.x, c.y], "r": e.dxf.radius, "layer": e.dxf.layer})
            elif t == "ARC":
                c = e.dxf.center
                ents.append({"type": "arc", "c": [c.x, c.y], "r": e.dxf.radius,
                             "start": e.dxf.start_angle, "end": e.dxf.end_angle, "layer": e.dxf.layer})
            elif t in ("LWPOLYLINE", "POLYLINE"):
                pts = []
                if t == "LWPOLYLINE":
                    pts = [[p[0], p[1]] for p in e.get_points()]
                else:
                    pts = [[v.dxf.location.x, v.dxf.location.y] for v in e.vertices]
                if pts:
                    ents.append({"type": "poly", "pts": pts, "closed": bool(e.closed), "layer": e.dxf.layer})
            elif t in ("TEXT", "MTEXT"):
                try:
                    ins = e.dxf.insert
                    px, py = float(ins.x), float(ins.y)
                except Exception:
                    px = py = 0.0
                try:
                    txt = e.dxf.text if t == "TEXT" else e.plain_text()
                except Exception:
                    try:
                        txt = e.plain_text()
                    except Exception:
                        txt = ""
                try:
                    h = float(e.dxf.height)
                except Exception:
                    h = 2.5
                try:
                    rot = float(e.dxf.rotation)
                except Exception:
                    rot = 0.0
                try:
                    layer = e.dxf.layer
                except Exception:
                    layer = "0"
                if txt:
                    ents.append({"type": "text", "p": [px, py], "text": str(txt),
                                 "h": h, "layer": layer, "rot": rot})
        except Exception:
            continue
    ext_min = ext_max = None
    try:
        ext_min = list(doc.header["$EXTMIN"])[:2]
        ext_max = list(doc.header["$EXTMAX"])[:2]
    except Exception:
        pass
    return {"kind": "dxf", "entities": ents, "types": types, "layers": [l.dxf.name for l in doc.layers],
            "extents": [ext_min, ext_max], "version": doc.dxfversion}


def dwg_info(path: str) -> dict:
    head = open(path, "rb").read(256)
    return {"kind": "dwg", "version": head[:6].decode("ascii", "replace"),
            "header": textutil.hexdump(path, 0, 512),
            "strings": textutil.strings(path, 5, 200),
            "note": "DWG 是 AutoCAD 私有格式。本程序内置 DXF 渲染器，但 DWG 需要 LibreDWG/AutoCAD 内核；此页展示结构、字符串与文件头。"}


def pe_info(path: str) -> dict:
    import pefile
    pe = pefile.PE(path, fast_load=False)
    out = {"kind": "pe", "machine": pefile.MACHINE_TYPE.get(pe.FILE_HEADER.Machine, hex(pe.FILE_HEADER.Machine)),
           "subsystem": pefile.SUBSYSTEM_TYPE.get(pe.OPTIONAL_HEADER.Subsystem, hex(pe.OPTIONAL_HEADER.Subsystem)),
           "entry": hex(pe.OPTIONAL_HEADER.AddressOfEntryPoint), "image_base": hex(pe.OPTIONAL_HEADER.ImageBase),
           "dll": bool(pe.FILE_HEADER.Characteristics & 0x2000), "sections": [], "imports": [],
           "version": {}, "size": os.path.getsize(path)}
    for s in pe.sections:
        try:
            name = s.Name.decode("utf-8", "replace").rstrip("\x00")
        except Exception:
            name = "?"
        out["sections"].append({"name": name, "va": hex(s.VirtualAddress), "vsize": s.Misc_VirtualSize,
                                "raw": s.SizeOfRawData, "entropy": round(s.get_entropy(), 2)})
    if hasattr(pe, "DIRECTORY_ENTRY_IMPORT"):
        for e in pe.DIRECTORY_ENTRY_IMPORT:
            funcs = [(i.name.decode("utf-8", "replace") if i.name else f"ord_{i.ordinal}") for i in e.imports[:60]]
            out["imports"].append({"dll": e.dll.decode("utf-8", "replace"), "count": len(e.imports), "functions": funcs})
    if hasattr(pe, "FileInfo"):
        for fi in pe.FileInfo:
            for entry in fi:
                if hasattr(entry, "StringTable"):
                    for st in entry.StringTable:
                        for k, v in st.entries.items():
                            out["version"][k.decode("utf-8", "replace")] = v.decode("utf-8", "replace")
    pe.close()
    return out


def elf_info(path: str) -> dict:
    from elftools.elf.elffile import ELFFile
    with open(path, "rb") as f:
        elf = ELFFile(f)
        return {"kind": "elf", "class": elf.elfclass, "machine": elf.header.e_machine,
                "entry": hex(elf.header.e_entry), "sections": [
                    {"name": s.name, "type": s["sh_type"], "size": s["sh_size"], "addr": hex(s["sh_addr"])}
                    for s in elf.iter_sections()], "size": os.path.getsize(path)}


def macho_info(path: str) -> dict:
    from macholib.MachO import MachO
    m = MachO(path)
    return {"kind": "macho", "headers": [
        {"magic": hex(h.magic), "cputype": h.header.cputype, "filetype": h.header.filetype,
         "ncmds": h.header.ncmds} for h in m.headers], "size": os.path.getsize(path)}


def step_info(path: str) -> dict:
    text = open(path, "r", encoding="utf-8", errors="replace").read(8 * 1024 * 1024)
    types = {}
    ents = 0
    for m in re.finditer(r"=\s*([A-Z0-9_]+)\s*\(", text):
        types[m.group(1)] = types.get(m.group(1), 0) + 1
        ents += 1
    names = re.findall(r"PRODUCT\s*\(\s*'([^']*)'", text)
    return {"kind": "step", "entities": ents, "types": dict(sorted(types.items(), key=lambda kv: -kv[1])[:40]),
            "names": names[:20], "header": text[:1800],
            "note": "STEP 精确曲面需要 CAD 内核；这里展示 B-Rep 实体结构、类型统计与产品名。"}


def blend_info(path: str) -> dict:
    head = open(path, "rb").read(12)
    if not head.startswith(b"BLENDER"):
        raise RuntimeError("不是 Blender 文件")
    return {"kind": "blend", "version": head[9:12].decode("ascii", "replace"),
            "header": textutil.hexdump(path, 0, 256),
            "strings": textutil.strings(path, 5, 100),
            "note": "Blender 工程需要 Blender 才能完整还原；这里展示版本、文件头与内嵌字符串。"}


def skp_info(path: str) -> dict:
    head = open(path, "rb").read(256)
    return {"kind": "skp", "version": head[:4].decode("ascii", "replace"),
            "header": textutil.hexdump(path, 0, 512), "strings": textutil.strings(path, 5, 100),
            "note": "SketchUp 私有格式；这里展示文件头与内嵌字符串。"}


def font_info(path: str) -> dict:
    from fontTools.ttLib import TTFont
    f = TTFont(path, fontNumber=0, lazy=True)
    name = f["name"]

    def get(nid):
        for r in name.names:
            if r.nameID == nid:
                try:
                    return r.toUnicode()
                except Exception:
                    pass
        return ""
    return {"kind": "font", "family": get(1), "subfamily": get(2), "full": get(4),
            "postscript": get(6), "version": get(5), "glyphs": f["maxp"].numGlyphs,
            "units": getattr(f["head"], "unitsPerEm", 1000),
            "tables": sorted(f.keys()), "size": os.path.getsize(path)}


def apk_info(path: str) -> dict:
    import zipfile
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        manifest = b""
        if "AndroidManifest.xml" in names:
            manifest = z.read("AndroidManifest.xml")
        strings = [s.decode("ascii", "replace") for s in re.findall(rb"[\x20-\x7e]{4,}", manifest)][:80]
    return {"kind": "apk", "count": len(names), "entries": names[:1200],
            "manifest_strings": strings, "size": os.path.getsize(path)}


def deb_info(path: str) -> dict:
    import io
    import tarfile
    data = open(path, "rb").read()
    if not data.startswith(b"!<arch>\n"):
        raise RuntimeError("不是 Debian 包")
    pos = 8
    out = {"kind": "deb", "control": {}, "files": []}
    while pos + 60 <= len(data):
        hdr = data[pos:pos + 60]
        name = hdr[:16].decode("ascii", "replace").strip().rstrip("/")
        size = int(hdr[48:58].decode("ascii", "replace").strip() or 0)
        body = data[pos + 60:pos + 60 + size]
        pos += 60 + size + (size % 2)
        if name.startswith("control.tar"):
            with tarfile.open(fileobj=io.BytesIO(body)) as tf:
                for m in tf.getmembers():
                    if m.name.lstrip("./") == "control":
                        for line in tf.extractfile(m).read().decode("utf-8", "replace").splitlines():
                            if ": " in line:
                                k, v = line.split(": ", 1)
                                out["control"][k] = v
        if name.startswith("data.tar"):
            with tarfile.open(fileobj=io.BytesIO(body)) as tf:
                out["files"] = [m.name for m in tf.getmembers()[:3000]]
    return out


def rpm_info(path: str) -> dict:
    import rpmfile
    with rpmfile.open(path) as r:
        h = {str(k): (v.decode("utf-8", "replace") if isinstance(v, bytes) else str(v)) for k, v in (r.headers or {}).items()}
        return {"kind": "rpm", "headers": h, "files": [m.name for m in r.getmembers()[:2000]]}
