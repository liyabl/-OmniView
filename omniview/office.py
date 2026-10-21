"""Self-contained document converters (no WPS / Office / LibreOffice needed)."""
from __future__ import annotations

import base64
import html
import io
import json
import os
import re
import zipfile
from xml.etree import ElementTree as ET

from . import paths


def _wrap(body: str, title: str = "", css: str = "") -> str:
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>{html.escape(title)}</title>
<style>
html,body{{margin:0;padding:0;background:#ffffff;color:#1f2937;}}
body{{font-family:'Microsoft YaHei','Segoe UI',sans-serif;font-size:15px;line-height:1.85;padding:42px 54px;}}
h1,h2,h3,h4{{color:#0f172a;line-height:1.45;margin:1.1em 0 .55em;}}
h1{{font-size:28px;border-bottom:1px solid #e5e7eb;padding-bottom:10px;}}
h2{{font-size:22px;}} h3{{font-size:18px;}}
p{{margin:.7em 0;}}
table{{border-collapse:collapse;margin:1em 0;max-width:100%;}}
td,th{{border:1px solid #cbd5e1;padding:6px 10px;vertical-align:top;}}
th{{background:#f1f5f9;}}
img{{max-width:100%;}}
pre{{background:#f6f8fa;border:1px solid #e5e7eb;border-radius:6px;padding:12px 14px;white-space:pre-wrap;font-family:Consolas,monospace;font-size:12.5px;}}
code{{font-family:Consolas,monospace;background:#f1f5f9;padding:1px 5px;border-radius:4px;}}
blockquote{{border-left:3px solid #93c5fd;background:#f8fafc;margin:1em 0;padding:6px 16px;color:#475569;}}
ul,ol{{padding-left:26px;}}
a{{color:#1d4ed8;}}
{css}
</style></head><body>{body}</body></html>"""


def _img_src(path: str) -> str:
    from PySide6.QtCore import QUrl
    return QUrl.fromLocalFile(path).toString()


def docx_to_html(path: str) -> str:
    """Convert DOCX to rich HTML with locally saved images."""
    try:
        import mammoth
    except Exception as e:
        return _wrap(f"<p>无法解析 DOCX：{html.escape(str(e))}</p>")
    outdir = paths.temp_dir("docx-img-")

    def save_image(image):
        try:
            with image.open() as f:
                data = f.read()
            ext = (image.content_type or "image/png").split("/")[-1].split("+")[0]
            if ext == "jpeg":
                ext = "jpg"
            p = os.path.join(outdir, f"img-{abs(hash(data)) & 0xFFFFFFFF:x}.{ext}")
            with open(p, "wb") as f:
                f.write(data)
            return {"src": _img_src(p)}
        except Exception:
            return {}

    try:
        with open(path, "rb") as f:
            result = mammoth.convert_to_html(f, convert_image=mammoth.images.img_element(save_image))
        body = result.value
        if not body.strip():
            body = "<p>文档中没有可显示的正文。</p>"
        return _wrap(body, os.path.basename(path))
    except Exception as e:
        return _wrap(f"<p>DOCX 解析失败：{html.escape(str(e))}</p>")


def odt_to_html(path: str) -> str:
    try:
        from odf.opendocument import load
        from odf import text as odftext, table as odftable, teletype
        doc = load(path)
        out = []

        def txt(el) -> str:
            try:
                return teletype.extractText(el)
            except Exception:
                return ""

        for child in doc.text.childNodes:
            name = getattr(child, "qname", (None, None))[1]
            if name == "p":
                t = txt(child)
                if t.strip():
                    out.append(f"<p>{html.escape(t)}</p>")
            elif name in ("h", "h1", "h2", "h3", "h4", "h5", "h6"):
                level = name[1] if name[1:].isdigit() else "1"
                out.append(f"<h{level}>{html.escape(txt(child))}</h{level}>")
            elif name == "list":
                items = []
                for li in child.getElementsByType(odftext.ListItem):
                    items.append(f"<li>{html.escape(txt(li))}</li>")
                out.append("<ul>" + "".join(items) + "</ul>")
            elif name == "table":
                rows = []
                for tr in child.getElementsByType(odftable.TableRow):
                    cells = []
                    for tc in tr.getElementsByType(odftable.TableCell):
                        cells.append(f"<td>{html.escape(txt(tc))}</td>")
                    rows.append("<tr>" + "".join(cells) + "</tr>")
                out.append("<table>" + "".join(rows) + "</table>")
        body = "\n".join(out) or "<p>文档中没有可显示的正文。</p>"
        return _wrap(body, os.path.basename(path))
    except Exception as e:
        return _wrap(f"<p>ODT 解析失败：{html.escape(str(e))}</p>")


def rtf_to_html(path: str) -> str:
    try:
        from striprtf.striprtf import rtf_to_text
        raw = open(path, "rb").read().decode("latin-1", "replace")
        text = rtf_to_text(raw, errors="ignore")
        paras = [p.strip() for p in text.replace("\r\n", "\n").split("\n")]
        return _wrap("".join(f"<p>{html.escape(p)}</p>" for p in paras if p), os.path.basename(path))
    except Exception:
        raw = open(path, "rb").read().decode("latin-1", "replace")
        raw = re.sub(r"\\'([0-9a-fA-F]{2})", lambda m: chr(int(m.group(1), 16)), raw)
        raw = re.sub(r"\\[a-zA-Z]+-?\d* ?", "", raw).replace("{", "").replace("}", "")
        return _wrap("<p>" + html.escape(raw[:300000]).replace("\n", "<br>") + "</p>")


def markdown_to_html(path: str) -> str:
    try:
        import markdown
        text = open(path, "r", encoding="utf-8-sig", errors="replace").read()
        body = markdown.markdown(text, extensions=["tables", "fenced_code", "sane_lists", "nl2br"])
        from PySide6.QtCore import QUrl
        base = QUrl.fromLocalFile(os.path.dirname(path) + os.sep).toString()
        body = re.sub(r'(<img[^>]+src=")([^"]+)"', lambda m: m.group(1) + (m.group(2) if "://" in m.group(2) else base + m.group(2)) + '"', body)
        return _wrap(body, os.path.basename(path))
    except Exception as e:
        return _wrap(f"<p>Markdown 解析失败：{html.escape(str(e))}</p>")


def html_to_document(path: str) -> str:
    """Return HTML with a base URL friendly to QTextBrowser."""
    raw = open(path, "r", encoding="utf-8-sig", errors="replace").read()
    return raw


def pptx_slides(path: str) -> dict:
    """Return a renderer-friendly description of a PPTX (or ODP best effort)."""
    from pptx import Presentation
    from pptx.enum.shapes import MSO_SHAPE_TYPE
    prs = Presentation(path)
    out = {"width": prs.slide_width, "height": prs.slide_height, "slides": []}
    tmp = paths.temp_dir("pptx-img-")
    for si, slide in enumerate(prs.slides):
        shapes = []
        try:
            bg = slide.background.fill
            if bg.type is not None:
                shapes.append({"kind": "rect", "x": 0, "y": 0, "w": prs.slide_width, "h": prs.slide_height,
                               "fill": _rgb(bg.fore_color) if bg.type == 1 else "#ffffff"})
        except Exception:
            pass
        for sh in slide.shapes:
            item = {"x": sh.left, "y": sh.top, "w": sh.width, "h": sh.height}
            try:
                if sh.shape_type == MSO_SHAPE_TYPE.PICTURE:
                    data = sh.image.blob
                    ext = (sh.image.ext or "png").lower()
                    p = os.path.join(tmp, f"s{si}-{len(shapes)}.{ext}")
                    open(p, "wb").write(data)
                    item.update(kind="image", path=p)
                    shapes.append(item)
                    continue
            except Exception:
                pass
            try:
                fill = sh.fill
                if fill.type == 1:
                    item["fill"] = _rgb(fill.fore_color)
                line = sh.line
                if line.color and line.color.type is not None:
                    item["line"] = _rgb(line.color)
                    item["line_width"] = line.width or 1
            except Exception:
                pass
            if getattr(sh, "has_text_frame", False) and sh.has_text_frame:
                item["kind"] = "text"
                item["paras"] = []
                for p in sh.text_frame.paragraphs:
                    runs = []
                    psize = p.font.size.pt if p.font.size else None
                    pcolor = _rgb(p.font.color) if p.font.color and p.font.color.type is not None else None
                    for r in p.runs:
                        rsize = r.font.size.pt if r.font.size else psize
                        rcolor = _rgb(r.font.color) if r.font.color and r.font.color.type is not None else pcolor
                        runs.append({
                            "text": r.text,
                            "size": rsize,
                            "bold": bool(r.font.bold) if r.font.bold is not None else bool(p.font.bold),
                            "italic": bool(r.font.italic) if r.font.italic is not None else bool(p.font.italic),
                            "color": rcolor,
                        })
                    item["paras"].append({"runs": runs, "align": str(p.alignment) if p.alignment else ""})
            else:
                item.setdefault("kind", "rect")
            if item.get("kind") != "image":
                shapes.append(item)
        out["slides"].append({"shapes": shapes, "notes": ""})
    return out


def _rgb(color) -> str:
    try:
        if color is None:
            return "#000000"
        if color.type == 1:  # RGB
            return "#" + str(color.rgb)
        if color.type == 2:  # theme
            return "#5b7cfa"
    except Exception:
        pass
    return "#000000"


def epub_extract(path: str) -> dict:
    """Extract an EPUB to a temp dir and return metadata/spine/toc."""
    outdir = paths.temp_dir("epub-")
    with zipfile.ZipFile(path) as z:
        for info in z.infolist():
            name = info.filename.replace("\\", "/")
            if name.startswith("/") or ".." in name.split("/"):
                continue
            target = os.path.join(outdir, *name.split("/"))
            os.makedirs(os.path.dirname(target), exist_ok=True)
            if not info.is_dir():
                with z.open(info) as src, open(target, "wb") as dst:
                    dst.write(src.read())
    container = os.path.join(outdir, "META-INF", "container.xml")
    opf = None
    if os.path.exists(container):
        try:
            root = ET.fromstring(open(container, "rb").read())
            for el in root.iter():
                if el.tag.endswith("rootfile"):
                    opf = el.attrib.get("full-path")
                    break
        except Exception:
            pass
    if not opf:
        for base, _dirs, files in os.walk(outdir):
            for f in files:
                if f.lower().endswith(".opf"):
                    opf = os.path.relpath(os.path.join(base, f), outdir).replace("\\", "/")
                    break
            if opf:
                break
    meta = {"title": os.path.splitext(os.path.basename(path))[0], "creator": "", "language": "", "toc": [], "spine": [], "root": outdir}
    if not opf:
        files = []
        for base, _dirs, names in os.walk(outdir):
            for f in names:
                if f.lower().endswith((".html", ".htm", ".xhtml")):
                    files.append(os.path.relpath(os.path.join(base, f), outdir).replace("\\", "/"))
        meta["spine"] = [{"href": f, "title": os.path.basename(f)} for f in sorted(files)]
        return meta
    opf_path = os.path.join(outdir, *opf.split("/"))
    base_dir = os.path.dirname(opf_path)
    meta["base"] = os.path.dirname(opf).replace("\\", "/")
    try:
        root = ET.fromstring(open(opf_path, "rb").read())
        ns = {"dc": "http://purl.org/dc/elements/1.1/"}
        for key in ("title", "creator", "language"):
            el = root.find(f".//dc:{key}", ns)
            if el is not None and el.text:
                meta[key] = el.text.strip()
        manifest = {}
        for item in root.findall(".//{*}manifest/{*}item"):
            manifest[item.attrib.get("id")] = item.attrib.get("href")
        for itemref in root.findall(".//{*}spine/{*}itemref"):
            href = manifest.get(itemref.attrib.get("idref"))
            if href:
                full = os.path.normpath(os.path.join(base_dir, href))
                rel = os.path.relpath(full, outdir).replace("\\", "/")
                meta["spine"].append({"href": rel, "title": os.path.splitext(os.path.basename(rel))[0]})
        # nav / ncx
        toc = []
        for item in root.findall(".//{*}manifest/{*}item"):
            if "nav" in (item.attrib.get("properties") or ""):
                nav = os.path.normpath(os.path.join(base_dir, item.attrib.get("href", "")))
                if os.path.exists(nav):
                    try:
                        nr = ET.fromstring(open(nav, "rb").read())
                        for a in nr.iter():
                            if a.tag.endswith("a") and a.attrib.get("href"):
                                toc.append({"label": "".join(a.itertext()).strip(), "href": a.attrib["href"]})
                    except Exception:
                        pass
        meta["toc"] = toc[:200]
    except Exception:
        pass
    if not meta["spine"]:
        meta["spine"] = [{"href": opf, "title": "正文"}]
    return meta


def mobi_to_epub(path: str) -> str:
    dst = paths.cache_file(path, "mobi", "epub")
    if os.path.exists(dst):
        return dst
    import mobi
    tmp, _ = mobi.extract(path)
    found = None
    for base, _dirs, files in os.walk(tmp):
        for f in files:
            if f.lower().endswith(".epub"):
                found = os.path.join(base, f)
                break
        if found:
            break
    if not found:
        for base, _dirs, files in os.walk(tmp):
            for f in files:
                if f.lower().endswith((".html", ".htm", ".xhtml")):
                    found = os.path.join(base, f)
                    break
            if found:
                break
    if not found:
        raise RuntimeError("MOBI 解包后没有可显示的正文")
    if found.lower().endswith(".epub"):
        import shutil
        shutil.copy2(found, dst)
        return dst
    raise RuntimeError("MOBI 解包结果不是 EPUB")


def notebook_to_html(path: str) -> str:
    try:
        nb = json.load(open(path, "r", encoding="utf-8-sig"))
        import markdown
        parts = []
        for i, cell in enumerate(nb.get("cells", [])[:400]):
            src = cell.get("source", "")
            if isinstance(src, list):
                src = "".join(src)
            if cell.get("cell_type") == "markdown":
                parts.append(f"<div class='nb-md'>{markdown.markdown(src, extensions=['tables','fenced_code'])}</div>")
            elif cell.get("cell_type") == "code":
                parts.append(f"<div class='nb-code'><pre>{html.escape(src)}</pre>")
                for o in cell.get("outputs", [])[:20]:
                    if "text" in o:
                        txt = "".join(o["text"]) if isinstance(o["text"], list) else o["text"]
                        parts.append(f"<pre class='nb-out'>{html.escape(txt)}</pre>")
                    elif "data" in o and "image/png" in o["data"]:
                        b64 = o["data"]["image/png"]
                        if isinstance(b64, list):
                            b64 = "".join(b64)
                        parts.append(f"<img src='data:image/png;base64,{b64}' style='max-width:100%'>")
                parts.append("</div>")
        return _wrap("".join(parts), os.path.basename(path))
    except Exception as e:
        return _wrap(f"<p>Notebook 解析失败：{html.escape(str(e))}</p>")


def email_to_html(path: str) -> dict:
    import email
    from email import policy
    from email.parser import BytesParser
    with open(path, "rb") as f:
        msg = BytesParser(policy=policy.default).parse(f)
    cid = {}
    attachments = []
    text_body = ""
    html_body = ""
    idx = 0
    tmp = paths.temp_dir("mail-img-")
    for part in msg.walk():
        ctype = part.get_content_type()
        disp = (part.get_content_disposition() or "").lower()
        key = (part.get("Content-ID") or "").strip("<>")
        if ctype.startswith("text/") and disp != "attachment":
            try:
                content = part.get_content()
            except Exception:
                content = (part.get_payload(decode=True) or b"").decode(part.get_content_charset() or "utf-8", "replace")
            if ctype == "text/html" and not html_body:
                html_body = content
            elif ctype == "text/plain" and not text_body:
                text_body = content
        elif key and ctype.startswith("image/"):
            data = part.get_payload(decode=True) or b""
            ext = ctype.split("/")[-1]
            p = os.path.join(tmp, f"cid-{idx}.{ext}")
            open(p, "wb").write(data)
            cid[key] = _img_src(p)
            idx += 1
        elif disp == "attachment" or part.get_filename():
            data = part.get_payload(decode=True) or b""
            attachments.append({"name": part.get_filename() or f"attachment-{idx}", "size": len(data),
                                "data": data, "index": idx})
            idx += 1
    if html_body:
        for k, v in cid.items():
            html_body = html_body.replace("cid:" + k, v)
        body = html_body
        mode = "html"
    else:
        body = "<pre>" + html.escape(text_body) + "</pre>"
        mode = "text"
    from email.header import decode_header, make_header
    def hdr(name):
        try:
            return str(make_header(decode_header(msg.get(name, ""))))
        except Exception:
            return msg.get(name, "")
    return {
        "html": _wrap(body, hdr("Subject")),
        "subject": hdr("Subject"), "from": hdr("From"), "to": hdr("To"), "cc": hdr("Cc"),
        "date": hdr("Date"), "attachments": attachments, "mode": mode,
    }
