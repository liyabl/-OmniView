"""Image decoding for native Qt display."""
from __future__ import annotations

import io
import os

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QImage, QImageReader, QPixmap

from . import paths

RAWS = {"raw", "cr2", "cr3", "nef", "arw", "dng", "orf", "rw2", "raf", "pef", "srw"}


def _ext(path: str) -> str:
    return os.path.splitext(path)[1].lower().lstrip(".")


def pil_to_qimage(im) -> QImage:
    im = im.convert("RGBA")
    data = im.tobytes("raw", "RGBA")
    return QImage(data, im.width, im.height, im.width * 4, QImage.Format.Format_RGBA8888).copy()


def qimage_from_pil(im) -> QImage:
    return pil_to_qimage(im)


def _from_pillow(path: str) -> QImage:
    from PIL import Image, ImageOps
    im = Image.open(path)
    im.seek(0)
    im = ImageOps.exif_transpose(im)
    if im.mode in ("I;16", "I;16B", "I;16L", "I", "F"):
        arr = im.convert("F")
        lo, hi = arr.getextrema()
        if hi <= lo:
            hi = lo + 1
        im = arr.point(lambda x: (x - lo) * (255.0 / (hi - lo))).convert("L")
    if im.mode not in ("RGB", "RGBA", "L", "LA"):
        im = im.convert("RGBA")
    if max(im.size) > 8000:
        im.thumbnail((8000, 8000))
    return pil_to_qimage(im)


def _from_psd(path: str) -> QImage:
    from psd_tools import PSDImage
    psd = PSDImage.open(path)
    im = psd.composite(force=True)
    if im is None:
        raise RuntimeError("PSD 没有可合成的图层")
    if max(im.size) > 8000:
        im.thumbnail((8000, 8000))
    return pil_to_qimage(im)


def _from_raw(path: str) -> QImage:
    import rawpy
    from PIL import Image
    with rawpy.imread(path) as raw:
        try:
            thumb = raw.extract_thumb()
            if thumb.format == rawpy.ThumbFormat.JPEG:
                im = Image.open(io.BytesIO(thumb.data))
                return pil_to_qimage(im)
            if thumb.format == rawpy.ThumbFormat.BITMAP:
                return pil_to_qimage(Image.fromarray(thumb.data))
        except Exception:
            pass
        rgb = raw.postprocess(use_camera_wb=True, no_auto_bright=False, output_bps=8)
        return pil_to_qimage(Image.fromarray(rgb))


def _from_ai(path: str) -> QImage:
    from PySide6.QtPdf import QPdfDocument
    doc = QPdfDocument()
    err = doc.load(path)
    if err != QPdfDocument.Error.None_ or doc.pageCount() == 0:
        raise RuntimeError("AI 不是 PDF 兼容格式")
    size = doc.pagePointSize(0)
    target = QSize(max(1, int(size.width() * 2)), max(1, int(size.height() * 2)))
    return doc.render(0, target)


def load_image(path: str) -> QImage:
    ext = _ext(path)
    if ext in RAWS:
        return _from_raw(path)
    if ext in ("psd", "psb"):
        return _from_psd(path)
    if ext == "ai":
        return _from_ai(path)
    reader = QImageReader(path)
    reader.setAutoTransform(True)
    img = reader.read()
    if not img.isNull():
        return img
    # Qt lacks a codec (TIFF/older formats) -> Pillow
    return _from_pillow(path)


def load_preview(path: str, max_side: int = 1200) -> QImage:
    img = load_image(path)
    if max(img.width(), img.height()) > max_side:
        img = img.scaled(max_side, max_side, Qt.AspectRatioMode.KeepAspectRatio,
                         Qt.TransformationMode.SmoothTransformation)
    return img


def image_info(path: str) -> dict:
    ext = _ext(path)
    out = {"format": ext.upper(), "width": None, "height": None, "mode": "", "frames": 1,
           "dpi": None, "alpha": False, "exif": {}, "size": os.path.getsize(path)}
    try:
        if ext in RAWS:
            import rawpy
            with rawpy.imread(path) as raw:
                out.update(width=raw.sizes.width, height=raw.sizes.height, mode="RAW")
                for k in ("make", "model", "timestamp", "aperture", "shutter", "iso_speed", "focal_len"):
                    v = getattr(raw.metadata, k, None)
                    if v:
                        out["exif"][k] = str(v)
            return out
        if ext in ("psd", "psb"):
            from psd_tools import PSDImage
            psd = PSDImage.open(path)
            out.update(width=psd.width, height=psd.height,
                       mode=getattr(getattr(psd, "color_mode", ""), "name", str(getattr(psd, "color_mode", ""))),
                       alpha=bool(getattr(psd, "_merged_alpha", False)),
                       layers=len(list(psd.descendants())))
            return out
        if ext == "ai":
            from PySide6.QtPdf import QPdfDocument
            doc = QPdfDocument()
            if doc.load(path) == QPdfDocument.Error.None_:
                s = doc.pagePointSize(0)
                out.update(width=round(s.width(), 1), height=round(s.height(), 1), format="AI (PDF)", frames=doc.pageCount())
                return out
        from PIL import Image
        im = Image.open(path)
        out.update(width=im.width, height=im.height, mode=im.mode, format=im.format or ext.upper(),
                   frames=getattr(im, "n_frames", 1), alpha=("A" in im.getbands()))
        dpi = im.info.get("dpi")
        if dpi:
            out["dpi"] = [round(float(x), 1) for x in dpi]
        try:
            ex = im.getexif()
            for k, v in list(ex.items())[:40]:
                tag = __import__("PIL.ExifTags", fromlist=["TAGS"]).TAGS.get(k, str(k))
                out["exif"][str(tag)] = str(v)[:160]
        except Exception:
            pass
    except Exception as e:
        out["error"] = str(e)
    return out
