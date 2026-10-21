"""CPU-only mesh loaders for STL / OBJ / GLB / GLTF / 3MF."""
from __future__ import annotations

import base64
import json
import os
import struct
import zipfile

import numpy as np


def load_mesh(path: str) -> dict:
    ext = os.path.splitext(path)[1].lower().lstrip(".")
    try:
        if ext == "stl":
            v, f = _stl(path)
        elif ext == "obj":
            v, f = _obj(path)
        elif ext in ("glb", "gltf"):
            v, f = _gltf(path)
        elif ext == "3mf":
            v, f = _3mf(path)
        else:
            return {"error": "该三维格式需要专业内核", "vertices": np.zeros((0, 3)), "faces": np.zeros((0, 3), dtype=int)}
        v = np.asarray(v, dtype=np.float32)
        f = np.asarray(f, dtype=np.int64)
        if len(v) == 0 or len(f) == 0:
            return {"error": "模型中没有三角面", "vertices": v, "faces": f}
        mn, mx = v.min(axis=0), v.max(axis=0)
        return {"vertices": v, "faces": f, "min": mn, "max": mx,
                "center": (mn + mx) / 2, "size": mx - mn,
                "triangles": len(f), "vertices_count": len(v)}
    except Exception as e:
        return {"error": str(e), "vertices": np.zeros((0, 3)), "faces": np.zeros((0, 3), dtype=int)}


def _stl(path: str):
    data = open(path, "rb").read()
    if len(data) >= 84:
        n = struct.unpack("<I", data[80:84])[0]
        if len(data) == 84 + n * 50:
            arr = np.frombuffer(data[84:84 + n * 50], dtype=np.uint8).reshape(n, 50)
            tri = arr[:, 12:48].copy().view("<f4").reshape(n, 3, 3)
            return tri.reshape(-1, 3), np.arange(n * 3).reshape(n, 3)
    verts, faces = [], []
    with open(path, "r", errors="replace") as fh:
        for line in fh:
            p = line.split()
            if p and p[0] == "vertex" and len(p) >= 4:
                verts.append([float(p[1]), float(p[2]), float(p[3])])
                if len(verts) % 3 == 0:
                    faces.append([len(verts) - 3, len(verts) - 2, len(verts) - 1])
    return verts, faces


def _obj(path: str):
    verts, faces = [], []
    with open(path, "r", errors="replace") as fh:
        for line in fh:
            p = line.split()
            if not p:
                continue
            if p[0] == "v" and len(p) >= 4:
                verts.append([float(p[1]), float(p[2]), float(p[3])])
            elif p[0] == "f" and len(p) >= 4:
                idx = []
                for x in p[1:]:
                    try:
                        idx.append(int(x.split("/")[0]) - 1)
                    except ValueError:
                        pass
                for i in range(1, len(idx) - 1):
                    faces.append([idx[0], idx[i], idx[i + 1]])
    return verts, faces


def _gltf(path: str):
    if path.lower().endswith(".glb"):
        data = open(path, "rb").read()
        magic, ver, ln = struct.unpack("<4sII", data[:12])
        off = 12
        js = None
        binchunk = b""
        while off + 8 <= len(data):
            clen, ctype = struct.unpack("<II", data[off:off + 8])
            chunk = data[off + 8:off + 8 + clen]
            if ctype == 0x4E4F534A:
                js = json.loads(chunk.decode("utf-8"))
            elif ctype == 0x004E4942:
                binchunk = chunk
            off += 8 + clen + ((4 - clen % 4) % 4)
        j = js or {}
        base = os.path.dirname(path)
    else:
        j = json.load(open(path, "r", encoding="utf-8"))
        base = os.path.dirname(path)
        binchunk = b""
    buffers = []
    for b in j.get("buffers", []):
        uri = b.get("uri")
        if uri and uri.startswith("data:"):
            buffers.append(base64.b64decode(uri.split(",", 1)[1]))
        elif uri:
            buffers.append(open(os.path.join(base, uri), "rb").read())
        else:
            buffers.append(binchunk)
    verts, faces = [], []
    for mesh in j.get("meshes", []):
        for prim in mesh.get("primitives", []):
            attrs = prim.get("attributes", {})
            pos_i = attrs.get("POSITION")
            if pos_i is None:
                continue
            pos = _accessor(j, buffers, pos_i)
            if pos is None:
                continue
            base_idx = len(verts)
            verts.extend(pos.tolist())
            idx_i = prim.get("indices")
            if idx_i is not None:
                idx = _accessor(j, buffers, idx_i)
                if idx is not None:
                    idx = idx.astype(np.int64).ravel()
                    faces.extend((idx.reshape(-1, 3) + base_idx).tolist())
            else:
                n = len(pos) // 3
                faces.extend((np.arange(n).reshape(-1, 3) + base_idx).tolist())
    return verts, faces


def _accessor(j, buffers, idx):
    try:
        a = j["accessors"][idx]
        bv = j["bufferViews"][a["bufferView"]]
        buf = buffers[bv.get("buffer", 0)]
        comp = {5120: np.int8, 5121: np.uint8, 5122: np.int16, 5123: np.uint16,
                5125: np.uint32, 5126: np.float32}[a["componentType"]]
        ncomp = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}[a["type"]]
        count = a["count"]
        start = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
        stride = bv.get("byteStride", ncomp * np.dtype(comp).itemsize)
        out = np.zeros((count, ncomp), dtype=comp)
        for i in range(count):
            out[i] = np.frombuffer(buf, dtype=comp, count=ncomp, offset=start + i * stride)
        return out
    except Exception:
        return None


def _3mf(path: str):
    with zipfile.ZipFile(path) as z:
        name = "3D/3dmodel.model" if "3D/3dmodel.model" in z.namelist() else next(n for n in z.namelist() if n.endswith(".model"))
        import xml.etree.ElementTree as ET
        root = ET.fromstring(z.read(name))
        ns = {"m": "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"}
        verts = []
        for v in root.findall(".//m:vertex", ns):
            verts.append([float(v.attrib["x"]), float(v.attrib["y"]), float(v.attrib["z"])])
        faces = []
        for t in root.findall(".//m:triangle", ns):
            faces.append([int(t.attrib["v1"]), int(t.attrib["v2"]), int(t.attrib["v3"])])
        return verts, faces
