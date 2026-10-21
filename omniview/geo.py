"""GIS readers with no online tiles and no external GIS install."""
from __future__ import annotations

import json
import os
import re
import zipfile
from xml.etree import ElementTree as ET


def _strip(tag: str) -> str:
    return tag.split("}")[-1]


def _coords(text):
    out = []
    for token in (text or "").replace("\n", " ").split():
        parts = token.split(",")
        if len(parts) >= 2:
            try:
                out.append([float(parts[0]), float(parts[1])])
            except ValueError:
                pass
    return out


def load_geo(path: str) -> dict:
    ext = os.path.splitext(path)[1].lower().lstrip(".")
    if ext in ("shp", "shx"):
        return _shp(path)
    if ext in ("kml", "kmz"):
        return _kml(path)
    if ext == "gpx":
        return _gpx(path)
    if ext == "geojson":
        return _geojson(path)
    return {"features": [], "bounds": None, "crs": "", "error": "不支持的地理格式"}


def _shp(path: str) -> dict:
    import shapefile
    r = shapefile.Reader(path)
    fields = [f[0] for f in r.fields[1:]]
    feats = []
    for sr in r.iterShapeRecords():
        g = sr.shape.__geo_interface__
        props = {k: str(v) for k, v in zip(fields, sr.record)}
        feats.append({"type": g.get("type"), "coordinates": g.get("coordinates"), "props": props})
    r.close()
    crs = "WGS84"
    prj = os.path.splitext(path)[0] + ".prj"
    if os.path.exists(prj):
        try:
            txt = open(prj, "r", encoding="utf-8", errors="replace").read()
            if "WGS_1984" in txt or "WGS 84" in txt:
                crs = "WGS84"
            else:
                crs = "投影坐标（未重投影）"
        except Exception:
            pass
    return {"features": feats, "fields": fields, "crs": crs}


def _kml(path: str) -> dict:
    data = open(path, "rb").read()
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as z:
            names = [n for n in z.namelist() if n.lower().endswith(".kml")]
            if not names:
                return {"features": [], "bounds": None, "crs": "WGS84", "error": "KMZ 中没有 KML"}
            data = z.read(names[0])
    root = ET.fromstring(data)
    feats = []

    def geom(el):
        tag = _strip(el.tag)
        if tag == "Point":
            c = _coords(el.findtext(".//{*}coordinates"))
            if c:
                return [{"type": "Point", "coordinates": c[0]}]
        if tag == "LineString":
            c = _coords(el.findtext(".//{*}coordinates"))
            if c:
                return [{"type": "LineString", "coordinates": c}]
        if tag == "Polygon":
            rings = []
            for ring in el.findall(".//{*}LinearRing"):
                rings.append(_coords(ring.findtext(".//{*}coordinates")))
            if rings:
                return [{"type": "Polygon", "coordinates": rings}]
        if tag == "MultiGeometry":
            out = []
            for ch in el:
                out.extend(geom(ch))
            return out
        return []

    for pm in root.iter():
        if _strip(pm.tag) != "Placemark":
            continue
        name = ""
        props = {}
        gs = []
        for ch in pm:
            tag = _strip(ch.tag)
            if tag == "name":
                name = ch.text or ""
            elif tag == "description":
                props["description"] = ch.text or ""
            elif tag in ("Point", "LineString", "Polygon", "MultiGeometry"):
                gs.extend(geom(ch))
            elif tag == "ExtendedData":
                for d in ch.iter():
                    if _strip(d.tag) == "Data":
                        props[d.attrib.get("name", "")] = d.findtext("{*}value") or ""
        for g in gs:
            g["name"] = name
            g["props"] = props
            feats.append(g)
    return {"features": feats, "fields": list(props.keys()), "crs": "WGS84"}


def _gpx(path: str) -> dict:
    root = ET.fromstring(open(path, "rb").read())
    feats = []
    for trk in [e for e in root.iter() if _strip(e.tag) == "trk"]:
        name = next((e.text for e in trk if _strip(e.tag) == "name"), "")
        for seg in [e for e in trk.iter() if _strip(e.tag) == "trkseg"]:
            pts = [[float(p.attrib["lon"]), float(p.attrib["lat"])] for p in seg.iter()
                   if _strip(p.tag) == "trkpt" and "lon" in p.attrib]
            if len(pts) >= 2:
                feats.append({"type": "LineString", "coordinates": pts, "name": name, "props": {"points": len(pts)}})
    for wpt in [e for e in root.iter() if _strip(e.tag) == "wpt"]:
        try:
            feats.append({"type": "Point", "coordinates": [float(wpt.attrib["lon"]), float(wpt.attrib["lat"])],
                          "name": next((e.text for e in wpt if _strip(e.tag) == "name"), ""), "props": {}})
        except Exception:
            pass
    return {"features": feats, "fields": [], "crs": "WGS84"}


def _geojson(path: str) -> dict:
    obj = json.load(open(path, "r", encoding="utf-8-sig"))
    if obj.get("type") == "Feature":
        fs = [obj]
    elif obj.get("type") == "FeatureCollection":
        fs = obj.get("features", [])
    else:
        fs = [{"type": "Feature", "geometry": obj, "properties": {}}]
    feats = []
    for f in fs:
        g = f.get("geometry") or {}
        feats.append({"type": g.get("type"), "coordinates": g.get("coordinates"),
                      "name": (f.get("properties") or {}).get("name", ""), "props": f.get("properties") or {}})
    return {"features": feats, "fields": [], "crs": "WGS84"}
