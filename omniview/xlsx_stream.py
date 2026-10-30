"""Memory-bounded XLSX reader for very large workbooks.

This module deliberately does not import openpyxl.  A 500 MB xlsx can expand
to several GB of XML and millions of cell objects; openpyxl is fine for normal
files but the wrong tool for that size.

The reader:
  * reads workbook/relationship XML only, which is small;
  * builds a disk-backed sharedStrings index in SQLite (bounded memory);
  * streams a worksheet XML into row windows;
  * resolves only the shared strings needed by the current window.
"""
from __future__ import annotations

import os
import posixpath
import re
import sqlite3
import xml.etree.ElementTree as ET
import zipfile

from . import paths


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _col_num(ref: str) -> int:
    n = 0
    for ch in ref:
        if "A" <= ch <= "Z":
            n = n * 26 + ord(ch) - 64
        elif "a" <= ch <= "z":
            n = n * 26 + ord(ch) - 96
        else:
            break
    return n


def _normalize_target(base: str, target: str) -> str:
    target = target.replace("\\", "/")
    if target.startswith("/"):
        return target.lstrip("/")
    p = posixpath.normpath(posixpath.join(posixpath.dirname(base), target))
    return p.lstrip("./")


def read_workbook(path: str) -> dict:
    """Return sheet names/targets and the sharedStrings target."""
    with zipfile.ZipFile(path) as z:
        names = set(z.namelist())
        wb = ET.fromstring(z.read("xl/workbook.xml"))
        rels = {}
        rel_path = "xl/_rels/workbook.xml.rels"
        if rel_path in names:
            for rel in ET.fromstring(z.read(rel_path)):
                rid = rel.attrib.get("Id")
                target = rel.attrib.get("Target")
                if rid and target:
                    rels[rid] = _normalize_target("xl/workbook.xml", target)
        sheets = []
        for sh in wb.iter():
            if _local(sh.tag) != "sheet":
                continue
            rid = ""
            for k, v in sh.attrib.items():
                if _local(k) == "id":
                    rid = v
                    break
            target = rels.get(rid, "")
            if not target:
                # Fallback for malformed/loose packages.
                target = f"xl/worksheets/sheet{len(sheets) + 1}.xml"
            sheets.append({"name": sh.attrib.get("name") or f"Sheet{len(sheets) + 1}", "target": target})
        active = 0
        for node in wb.iter():
            if _local(node.tag) == "workbookView":
                try:
                    active = int(node.attrib.get("activeTab") or 0)
                except Exception:
                    active = 0
                break
        shared = ""
        for rel in rels.values():
            if rel.lower().endswith("sharedstrings.xml"):
                shared = rel
                break
        if not shared and "xl/sharedStrings.xml" in names:
            shared = "xl/sharedStrings.xml"
        return {"sheets": sheets, "shared": shared, "active": min(active, max(0, len(sheets) - 1))}


def dimension(path: str, target: str) -> tuple[int, int]:
    """Read only enough of the sheet XML to get the dimension ref."""
    try:
        with zipfile.ZipFile(path) as z, z.open(target) as f:
            head = f.read(2 * 1024 * 1024).decode("utf-8", "ignore")
        m = re.search(r'<dimension[^>]*ref="([^"]+)"', head)
        if not m:
            return 0, 0
        ref = m.group(1).split(":")[-1]
        mm = re.match(r"([A-Za-z]+)(\d+)", ref)
        if not mm:
            return 0, 0
        return int(mm.group(2)), _col_num(mm.group(1))
    except Exception:
        return 0, 0


def shared_cache_path(path: str) -> str:
    return paths.cache_file(path, "xlsx-strings", "sqlite")


def is_large(path: str, threshold_bytes: int = 8 * 1024 * 1024,
             threshold_rows: int = 20000) -> bool:
    """True when openpyxl would be a bad idea for this workbook."""
    try:
        if os.path.getsize(path) > threshold_bytes:
            return True
        meta = read_workbook(path)
        sheets = meta.get("sheets") or []
        if not sheets:
            return False
        rows, _cols = dimension(path, sheets[meta.get("active", 0)]["target"])
        return rows > threshold_rows
    except Exception:
        return False


def build_shared_index(path: str, shared_target: str, db_path: str | None = None,
                       progress=None, stop=None) -> str:
    """Build a disk-backed index of sharedStrings; returns the sqlite path."""
    db_path = db_path or shared_cache_path(path)
    if os.path.exists(db_path):
        return db_path
    tmp = db_path + ".tmp"
    try:
        os.remove(tmp)
    except OSError:
        pass
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(tmp)
    try:
        conn.execute("PRAGMA journal_mode=OFF")
        conn.execute("PRAGMA synchronous=OFF")
        conn.execute("CREATE TABLE strings (id INTEGER PRIMARY KEY, text TEXT NOT NULL)")
        batch = []
        idx = 0
        with zipfile.ZipFile(path) as z:
            if shared_target and shared_target in z.namelist():
                with z.open(shared_target) as f:
                    context = ET.iterparse(f, events=("start", "end"))
                    try:
                        _, root = next(context)
                    except StopIteration:
                        root = None
                    for event, elem in context:
                        if stop is not None and stop():
                            raise InterruptedError
                        if event != "end" or _local(elem.tag) != "si":
                            continue
                        text = "".join((t.text or "") for t in elem.iter() if _local(t.tag) == "t")
                        batch.append((idx, text))
                        idx += 1
                        elem.clear()
                        if root is not None and idx % 1000 == 0:
                            root.clear()
                        if len(batch) >= 1000:
                            conn.executemany("INSERT OR REPLACE INTO strings(id,text) VALUES(?,?)", batch)
                            batch.clear()
                            conn.commit()
                            if progress is not None:
                                progress(idx, None)
        if batch:
            conn.executemany("INSERT OR REPLACE INTO strings(id,text) VALUES(?,?)", batch)
            conn.commit()
        conn.execute("PRAGMA optimize")
        conn.close()
        os.replace(tmp, db_path)
        return db_path
    except Exception:
        try:
            conn.close()
        except Exception:
            pass
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise


def _resolve(conn: sqlite3.Connection, ids: set[int]) -> dict[int, str]:
    out = {}
    ids = [i for i in ids if i >= 0]
    for start in range(0, len(ids), 800):
        part = ids[start:start + 800]
        q = "SELECT id,text FROM strings WHERE id IN (" + ",".join("?" * len(part)) + ")"
        for i, text in conn.execute(q, part):
            out[int(i)] = text
    return out


def read_chunk(path: str, sheet_target: str, start_row: int = 1, rows: int = 300,
               max_cols: int = 128, shared_db: str | None = None,
               progress=None, stop=None) -> dict:
    """Stream a window of rows. Only this window is kept in memory."""
    start_row = max(1, int(start_row))
    rows = max(1, int(rows))
    max_cols = max(1, int(max_cols))
    out = []
    max_col = 0
    conn = None
    if shared_db and os.path.exists(shared_db):
        conn = sqlite3.connect(shared_db)
    try:
        with zipfile.ZipFile(path) as z, z.open(sheet_target) as f:
            context = ET.iterparse(f, events=("start", "end"))
            try:
                _, root = next(context)
            except StopIteration:
                root = None
            current_row = 0
            for event, elem in context:
                if stop is not None and stop():
                    raise InterruptedError
                if event != "end":
                    continue
                name = _local(elem.tag)
                if name != "row":
                    continue
                try:
                    row_no = int(elem.attrib.get("r") or current_row + 1)
                except Exception:
                    row_no = current_row + 1
                current_row = row_no
                if row_no < start_row:
                    elem.clear()
                    if root is not None:
                        root.clear()
                    continue
                cells = {}
                last_col = 0
                shared_ids = set()
                for c in elem:
                    if _local(c.tag) != "c":
                        continue
                    ref = c.attrib.get("r") or ""
                    col = _col_num(ref) or last_col + 1
                    last_col = col
                    if col > max_cols:
                        continue
                    t = c.attrib.get("t") or ""
                    v = None
                    formula = ""
                    inline = ""
                    for ch in c:
                        ln = _local(ch.tag)
                        if ln == "v":
                            v = ch.text
                        elif ln == "f":
                            formula = ch.text or ""
                        elif ln == "is":
                            inline = "".join((x.text or "") for x in ch.iter() if _local(x.tag) == "t")
                    if t == "s" and v is not None:
                        try:
                            sid = int(v)
                        except Exception:
                            sid = -1
                        cells[col] = ("s", sid)
                        if sid >= 0:
                            shared_ids.add(sid)
                    elif t == "inlineStr":
                        cells[col] = ("v", inline)
                    elif t == "b":
                        cells[col] = ("v", "TRUE" if v == "1" else "FALSE")
                    elif t == "e":
                        cells[col] = ("v", v or "#ERR")
                    elif v is not None:
                        cells[col] = ("v", v)
                    elif formula:
                        cells[col] = ("v", "=" + formula)
                    else:
                        cells[col] = ("v", "")
                resolved = _resolve(conn, shared_ids) if conn is not None else {}
                values = [""] * min(max_cols, max(cells.keys() or [0]))
                for col, (kind, val) in cells.items():
                    if 1 <= col <= len(values):
                        values[col - 1] = resolved.get(val, f"#{val}") if kind == "s" else val
                max_col = max(max_col, len(values))
                out.append({"n": row_no, "cells": values})
                elem.clear()
                if root is not None:
                    root.clear()
                if len(out) >= rows:
                    break
        return {"rows": out, "cols": max_col, "start": start_row}
    finally:
        if conn is not None:
            conn.close()

