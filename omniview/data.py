"""Native data-file readers: SQLite, DBF, Access, HDF5, models, mail, Outlook headers."""
from __future__ import annotations

import io
import json
import mailbox
import os
import pickletools
import re
import sqlite3
import struct
import urllib.parse
import zipfile

from . import office, paths, textutil


def sqlite_info(path: str) -> dict:
    uri = "file:" + urllib.parse.quote(os.path.abspath(path).replace("\\", "/"), safe="/:") + "?mode=ro"
    con = sqlite3.connect(uri, uri=True, timeout=5)
    con.row_factory = sqlite3.Row
    try:
        cur = con.cursor()
        tables = []
        for row in cur.execute("SELECT type,name,sql FROM sqlite_master WHERE type IN ('table','view') AND name NOT LIKE 'sqlite_%' ORDER BY name"):
            name = row["name"]
            cols = []
            try:
                for c in cur.execute(f'PRAGMA table_info("{name.replace(chr(34), chr(34)*2)}")'):
                    cols.append({"name": c["name"], "type": c["type"], "pk": bool(c["pk"])})
            except Exception:
                pass
            try:
                n = cur.execute(f'SELECT COUNT(*) FROM "{name.replace(chr(34), chr(34)*2)}"').fetchone()[0]
            except Exception:
                n = None
            tables.append({"name": name, "type": row["type"], "rows": n, "columns": cols, "sql": row["sql"] or ""})
        return {"kind": "sqlite", "tables": tables}
    finally:
        con.close()


def sqlite_rows(path: str, table: str, offset: int = 0, limit: int = 300) -> dict:
    uri = "file:" + urllib.parse.quote(os.path.abspath(path).replace("\\", "/"), safe="/:") + "?mode=ro"
    con = sqlite3.connect(uri, uri=True, timeout=5)
    try:
        cur = con.cursor()
        q = f'"{table.replace(chr(34), chr(34)*2)}"'
        rows = cur.execute(f"SELECT * FROM {q} LIMIT ? OFFSET ?", (limit, offset)).fetchall()
        cols = [d[0] for d in cur.description]
        total = None
        try:
            total = cur.execute(f"SELECT COUNT(*) FROM {q}").fetchone()[0]
        except Exception:
            pass
        return {"columns": cols, "rows": [list(r) for r in rows], "total": total, "offset": offset}
    finally:
        con.close()


def sqlite_query(path: str, sql: str, limit: int = 500) -> dict:
    s = sql.strip().rstrip(";")
    if not re.match(r"(?is)^(select|with|pragma|explain)\b", s) or ";" in s:
        raise ValueError("只允许单条只读查询")
    uri = "file:" + urllib.parse.quote(os.path.abspath(path).replace("\\", "/"), safe="/:") + "?mode=ro"
    con = sqlite3.connect(uri, uri=True, timeout=5)
    try:
        cur = con.cursor()
        cur.execute(s)
        rows = cur.fetchmany(limit)
        cols = [d[0] for d in cur.description] if cur.description else []
        return {"columns": cols, "rows": [list(r) for r in rows]}
    finally:
        con.close()


def _fix_dbf(s):
    if not isinstance(s, str):
        return s
    s = s.strip()
    try:
        if any(ord(c) > 127 for c in s):
            return s.encode("cp936").decode("utf-8")
    except Exception:
        pass
    return s


def dbf_info(path: str) -> dict:
    import dbf
    t = dbf.Table(path, codepage="cp936")
    t.open(mode=dbf.READ_ONLY)
    try:
        structs = [str(x) for x in t.structure()]
        fields = []
        for s in structs:
            m = re.match(r"^(.*?)\s+([A-Za-z])(?:\((\d+)(?:,(\d+))?\))?$", s)
            if m:
                fields.append({"name": _fix_dbf(m.group(1)), "type": m.group(2), "length": int(m.group(3) or 0)})
        return {"kind": "dbf", "tables": [{"name": os.path.basename(path), "rows": len(t), "columns": [f["name"] for f in fields]}],
                "fields": fields}
    finally:
        t.close()


def dbf_rows(path: str, limit: int = 500) -> dict:
    import dbf
    t = dbf.Table(path, codepage="cp936")
    t.open(mode=dbf.READ_ONLY)
    try:
        cols = [_fix_dbf(str(n)) for n in t.field_names]
        rows = []
        for i, rec in enumerate(t):
            if i >= limit:
                break
            rows.append([_fix_dbf(rec[j]) for j in range(len(cols))])
        return {"columns": cols, "rows": rows, "total": len(t)}
    finally:
        t.close()


def access_info(path: str) -> dict:
    from access_parser import AccessParser
    db = AccessParser(path)
    tables = []
    for name in db.catalog:
        if name.startswith("MSys"):
            continue
        try:
            data = db.get_table(name)
            cols = list(data.keys()) if isinstance(data, dict) else []
            n = len(next(iter(data.values()))) if cols else 0
            tables.append({"name": name, "rows": n, "columns": cols})
        except Exception as e:
            tables.append({"name": name, "rows": None, "columns": [], "error": str(e)})
    return {"kind": "access", "tables": tables}


def access_rows(path: str, table: str, limit: int = 300) -> dict:
    from access_parser import AccessParser
    db = AccessParser(path)
    data = db.get_table(table)
    cols = list(data.keys())
    n = max((len(v) for v in data.values()), default=0)
    rows = [[data[c][i] if i < len(data[c]) else None for c in cols] for i in range(min(n, limit))]
    return {"columns": cols, "rows": rows, "total": n}


def hdf5_info(path: str) -> dict:
    import h5py
    nodes = []
    with h5py.File(path, "r") as f:
        def walk(name, obj):
            item = {"name": name, "type": "group" if isinstance(obj, h5py.Group) else "dataset",
                    "attrs": {k: str(v)[:120] for k, v in obj.attrs.items()}}
            if isinstance(obj, h5py.Dataset):
                item.update(shape=list(obj.shape), dtype=str(obj.dtype))
            nodes.append(item)
        f.visititems(walk)
    return {"kind": "hdf5", "nodes": nodes}


def hdf5_values(path: str, name: str, limit: int = 2000) -> dict:
    import h5py
    import numpy as np
    with h5py.File(path, "r") as f:
        ds = f[name]
        arr = np.asarray(ds[()])
        total = int(arr.size)
        flat = arr.ravel()
        step = max(1, flat.size // limit)
        vals = flat[::step][:limit].tolist()
        out = {"shape": list(ds.shape), "dtype": str(ds.dtype), "values": vals, "total": total,
               "attrs": {k: str(v)[:160] for k, v in ds.attrs.items()}}
        if np.issubdtype(ds.dtype, np.number) and arr.size:
            out["stats"] = {"min": float(np.nanmin(arr)), "max": float(np.nanmax(arr)),
                            "mean": float(np.nanmean(arr))}
        return out


def onnx_info(path: str) -> dict:
    import onnx
    from onnx import TensorProto
    m = onnx.load(path, load_external_data=False)
    g = m.graph

    def dims(v):
        try:
            return [d.dim_value if d.dim_value else (d.dim_param or "?") for d in v.type.tensor_type.shape.dim]
        except Exception:
            return []

    def dt(v):
        try:
            return TensorProto.DataType.Name(v.type.tensor_type.elem_type)
        except Exception:
            return "?"

    nodes = []
    producer = {}
    for i, n in enumerate(g.node):
        nodes.append({"id": i, "op": n.op_type, "name": n.name or f"{n.op_type}_{i}",
                      "inputs": list(n.input), "outputs": list(n.output)})
        for o in n.output:
            producer[o] = i
    for n in nodes:
        n["layer"] = max([nodes[producer[x]]["layer"] for x in n["inputs"] if x in producer and "layer" in nodes[producer[x]]] or [-1]) + 1
    edges = [[producer[x], n["id"]] for n in nodes for x in n["inputs"] if x in producer]
    hist = {}
    for n in nodes:
        hist[n["op"]] = hist.get(n["op"], 0) + 1
    return {"kind": "onnx", "graph": g.name, "nodes": nodes, "edges": edges,
            "inputs": [{"name": i.name, "shape": dims(i), "dtype": dt(i)} for i in g.input],
            "outputs": [{"name": o.name, "shape": dims(o), "dtype": dt(o)} for o in g.output],
            "initializers": len(g.initializer), "op_hist": dict(sorted(hist.items(), key=lambda kv: -kv[1])),
            "ir_version": m.ir_version, "producer": m.producer_name}


def _pickle_ops(data: bytes, limit=1200):
    ops = []
    try:
        for op, arg, pos in pickletools.genops(data):
            ops.append((op.name, str(arg)[:180]))
            if len(ops) >= limit:
                break
    except Exception:
        pass
    return ops


def torch_info(path: str) -> dict:
    info = {"kind": "torch", "entries": [], "strings": [], "protocol": None}
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as z:
            names = z.namelist()
            info["entries"] = [{"name": n, "size": z.getinfo(n).file_size} for n in names[:400]]
            pkl = next((n for n in names if n.endswith("data.pkl")), None)
            if pkl:
                ops = _pickle_ops(z.read(pkl))
                info["strings"] = [a for n, a in ops if n in ("BINUNICODE", "SHORT_BINUNICODE", "GLOBAL")][:200]
                info["protocol"] = ops[0][0] if ops else None
    return info


def pickle_info(path: str) -> dict:
    data = open(path, "rb").read(8 * 1024 * 1024)
    ops = _pickle_ops(data)
    counts = {}
    for n, _ in ops:
        counts[n] = counts.get(n, 0) + 1
    return {"kind": "pickle", "ops": ops[:600], "counts": dict(sorted(counts.items(), key=lambda kv: -kv[1])[:30]),
            "strings": [a for n, a in ops if n in ("BINUNICODE", "SHORT_BINUNICODE", "GLOBAL")][:120],
            "hex": textutil.hexdump(path, 0, 512)}


def tflite_info(path: str) -> dict:
    import tflite
    buf = open(path, "rb").read()
    m = tflite.Model.GetRootAsModel(buf, 0)
    sg = m.Subgraphs(0)
    tensors = []
    for i in range(sg.TensorsLength()):
        t = sg.Tensors(i)
        tensors.append({"name": t.Name().decode("utf-8", "replace") if t.Name() else "",
                        "shape": list(t.ShapeAsNumpy()) if t.ShapeLength() else []})
    ops = []
    for i in range(sg.OperatorsLength()):
        o = sg.Operators(i)
        code = m.OperatorCodes(o.OpcodeIndex())
        ops.append({"opcode": int(code.BuiltinCode()), "inputs": list(o.InputsAsNumpy()), "outputs": list(o.OutputsAsNumpy())})
    return {"kind": "tflite", "tensors": tensors, "operators": ops, "description": (m.Description() or b"").decode("utf-8", "replace")}


def protobuf_info(path: str) -> dict:
    data = open(path, "rb").read()
    fields = []
    pos = 0

    def varint(p):
        v = 0
        s = 0
        while p < len(data) and s < 64:
            b = data[p]
            p += 1
            v |= (b & 0x7F) << s
            if not b & 0x80:
                return v, p
            s += 7
        return None, p

    while pos < len(data) and len(fields) < 200:
        key, pos = varint(pos)
        if key is None:
            break
        fn, wt = key >> 3, key & 7
        if fn == 0:
            break
        item = {"field": fn, "wire": wt}
        if wt == 0:
            v, pos = varint(pos)
            item["value"] = v
        elif wt == 2:
            ln, pos = varint(pos)
            raw = data[pos:pos + ln]
            pos += ln
            try:
                s = raw.decode("utf-8")
                item["value"] = s if s.isprintable() else raw[:32].hex()
            except Exception:
                item["value"] = raw[:32].hex()
            item["length"] = ln
        elif wt == 1:
            item["value"] = struct.unpack("<d", data[pos:pos + 8])[0] if len(data[pos:pos + 8]) == 8 else ""
            pos += 8
        elif wt == 5:
            item["value"] = struct.unpack("<f", data[pos:pos + 4])[0] if len(data[pos:pos + 4]) == 4 else ""
            pos += 4
        else:
            break
        fields.append(item)
    return {"kind": "protobuf", "fields": fields, "hex": textutil.hexdump(path, 0, 512)}


def email_info(path: str) -> dict:
    if os.path.splitext(path)[1].lower() == ".msg":
        return msg_info(path)
    return {"kind": "email", **office.email_to_html(path)}


def msg_info(path: str) -> dict:
    import extract_msg
    m = extract_msg.Message(path)
    try:
        body = m.body or ""
        html_body = m.htmlBody or b""
        if isinstance(html_body, bytes):
            html_body = html_body.decode("utf-8", "replace")
        if html_body:
            html_text = html_body
            mode = "html"
        else:
            html_text = "<pre>" + __import__("html").escape(body) + "</pre>"
            mode = "text"
        atts = []
        for i, a in enumerate(m.attachments or []):
            atts.append({"index": i, "name": a.longFilename or a.shortFilename or f"attachment-{i}",
                         "size": len(a.data or b""), "data": a.data or b""})
        return {"kind": "msg", "subject": m.subject or "", "from": m.sender or "", "to": m.to or "",
                "cc": m.cc or "", "date": str(m.date or ""), "html": office._wrap(html_text),
                "mode": mode, "attachments": atts}
    finally:
        try:
            m.close()
        except Exception:
            pass


def mbox_list(path: str, limit: int = 2000) -> dict:
    box = mailbox.mbox(path, create=False)
    try:
        items = []
        for i, msg in enumerate(box):
            if i >= limit:
                break
            items.append({"index": i, "from": msg.get("From", ""), "subject": msg.get("Subject", ""),
                          "date": msg.get("Date", "")})
        return {"kind": "mbox", "messages": items, "count": len(box)}
    finally:
        box.close()


def mbox_message(path: str, index: int) -> dict:
    box = mailbox.mbox(path, create=False)
    try:
        msg = box[index]
        import tempfile
        fd, tmp = tempfile.mkstemp(suffix=".eml", dir=paths.TEMP)
        os.close(fd)
        open(tmp, "wb").write(msg.as_bytes())
        try:
            return email_info(tmp)
        finally:
            os.remove(tmp)
    finally:
        box.close()


def pst_info(path: str) -> dict:
    head = open(path, "rb").read(1024)
    return {"kind": "pst", "magic": head[:4].hex(" ").upper(),
            "encrypted": bool(head[0x1CD] & 1) if len(head) > 0x1CD else None,
            "header": textutil.hexdump(path, 0, 512),
            "strings": textutil.strings(path, 6, 200),
            "note": "PST/OST 是 Outlook 私有数据库；本程序只读取文件头、加密标志与内嵌字符串。"}
