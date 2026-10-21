# -*- coding: utf-8 -*-
"""文本解码、编码猜测、十六进制与二进制辅助。"""
from __future__ import annotations

import codecs
import math
import os
import re
import unicodedata

BOMS = [
    (codecs.BOM_UTF32_LE, "utf-32-le", "UTF-32 LE"),
    (codecs.BOM_UTF32_BE, "utf-32-be", "UTF-32 BE"),
    (codecs.BOM_UTF8, "utf-8-sig", "UTF-8 BOM"),
    (codecs.BOM_UTF16_LE, "utf-16-le", "UTF-16 LE"),
    (codecs.BOM_UTF16_BE, "utf-16-be", "UTF-16 BE"),
]

CANDIDATES = [
    ("utf-8", "UTF-8"),
    ("gb18030", "GB18030 / GBK"),
    ("big5", "Big5"),
    ("shift_jis", "Shift-JIS"),
    ("euc-kr", "EUC-KR"),
    ("cp1252", "Windows-1252"),
    ("latin-1", "Latin-1"),
]

ENCODING_CHOICES = [
    ("auto", "自动识别"),
    ("utf-8", "UTF-8"),
    ("utf-8-sig", "UTF-8（带 BOM）"),
    ("gb18030", "GB18030 / 简体中文"),
    ("gbk", "GBK"),
    ("big5", "Big5 / 繁体中文"),
    ("shift_jis", "Shift-JIS / 日文"),
    ("euc-kr", "EUC-KR / 韩文"),
    ("utf-16-le", "UTF-16 LE"),
    ("utf-16-be", "UTF-16 BE"),
    ("cp1252", "Windows-1252"),
    ("latin-1", "Latin-1"),
]

LANG_BY_EXT = {
    "c": "text/x-csrc", "h": "text/x-csrc", "cpp": "text/x-c++src",
    "cxx": "text/x-c++src", "cc": "text/x-c++src", "hpp": "text/x-c++src",
    "hh": "text/x-c++src", "cs": "text/x-csharp", "java": "text/x-java",
    "py": "text/x-python", "pyw": "text/x-python", "js": "text/javascript",
    "mjs": "text/javascript", "cjs": "text/javascript", "jsx": "text/jsx",
    "ts": "text/typescript", "tsx": "text/typescript-jsx", "vue": "text/html",
    "svelte": "text/html", "html": "text/html", "htm": "text/html",
    "xhtml": "application/xhtml+xml", "css": "text/css", "scss": "text/x-scss",
    "sass": "text/x-sass", "less": "text/x-less", "php": "application/x-httpd-php",
    "rb": "text/x-ruby", "go": "text/x-go", "rs": "text/x-rustsrc",
    "kt": "text/x-kotlin", "kts": "text/x-kotlin", "swift": "text/x-swift",
    "lua": "text/x-lua", "r": "text/x-rsrc", "sql": "text/x-sql",
    "json": "application/json", "jsonl": "application/json", "xml": "application/xml",
    "xsd": "application/xml", "xsl": "application/xml", "yaml": "text/x-yaml",
    "yml": "text/x-yaml", "toml": "text/x-toml", "ini": "text/x-properties",
    "cfg": "text/x-properties", "conf": "text/x-properties",
    "properties": "text/x-properties", "sh": "text/x-sh", "bash": "text/x-sh",
    "zsh": "text/x-sh", "fish": "text/x-sh", "bat": "text/x-sh",
    "cmd": "text/x-sh", "ps1": "text/x-powershell", "psm1": "text/x-powershell",
    "tex": "text/x-stex", "latex": "text/x-stex", "md": "text/x-markdown",
    "markdown": "text/x-markdown", "ipynb": "application/json",
    "log": "text/plain", "txt": "text/plain", "text": "text/plain",
    "diff": "text/x-diff", "patch": "text/x-diff", "cmake": "text/x-cmake",
    "mk": "text/x-makefile",
}


def lang_for(ext: str) -> str:
    return LANG_BY_EXT.get(ext, "text/plain")


def _score(text: str) -> float:
    """对解码结果打分：可打印字符多、控制字符少、替换符少。"""
    if not text:
        return 0.0
    n = len(text)
    good = bad = cjk = 0
    for ch in text:
        o = ord(ch)
        if ch in "\r\n\t":
            good += 1
        elif o < 32 or 0x7F <= o < 0xA0:
            bad += 3
        elif ch == "\ufffd":
            bad += 10
        elif 0x4E00 <= o <= 0x9FFF or 0x3400 <= o <= 0x4DBF:
            cjk += 1
            good += 1
        elif 0x3000 <= o <= 0x30FF or 0xAC00 <= o <= 0xD7AF:
            good += 1
        elif unicodedata.category(ch).startswith("C"):
            bad += 2
        else:
            good += 1
    return (good - bad) / max(n, 1) + min(cjk / max(n, 1), 0.35)


def _decode_with(data: bytes, enc: str) -> str | None:
    try:
        return data.decode(enc, errors="strict")
    except (UnicodeDecodeError, LookupError):
        return None


def _looks_binary(data: bytes) -> bool:
    if not data:
        return False
    sample = data[:8192]
    if b"\x00" in sample:
        # UTF-16 会被 BOM/探测提前处理；这里只判定真正的二进制
        nul = sample.count(0)
        if nul / len(sample) < 0.25:
            return True
        return True
    ctrl = sum(1 for b in sample if b < 9 or (13 < b < 32))
    return ctrl / max(len(sample), 1) > 0.12


def decode_bytes(data: bytes, encoding: str = "auto") -> dict:
    """返回 {text, encoding, label, confidence, bom, binary, newline, truncated}"""
    result = {
        "text": "",
        "encoding": "utf-8",
        "label": "UTF-8",
        "confidence": 1.0,
        "bom": False,
        "binary": False,
        "newline": "LF",
        "truncated": False,
    }
    if encoding and encoding != "auto":
        try:
            label = dict(ENCODING_CHOICES).get(encoding, encoding)
            text = data.decode(encoding, errors="replace")
            result.update(text=text, encoding=encoding, label=label,
                          confidence=0.99, newline=_newline(text))
            return result
        except LookupError:
            pass

    # BOM
    for bom, enc, label in BOMS:
        if data.startswith(bom):
            body = data[len(bom):]
            try:
                text = body.decode(enc, errors="replace")
                result.update(text=text, encoding=enc, label=label, confidence=1.0,
                              bom=True, newline=_newline(text))
                return result
            except Exception:
                pass

    if _looks_binary(data):
        result["binary"] = True

    # UTF-16 无 BOM（大量 0 字节，且集中在奇/偶位）
    if len(data) >= 8:
        even_nul = data[0::2].count(0)
        odd_nul = data[1::2].count(0)
        half = len(data) / 2
        if odd_nul > half * 0.55 and even_nul < half * 0.1:
            text = data.decode("utf-16-le", errors="replace")
            result.update(text=text, encoding="utf-16-le", label="UTF-16 LE（无 BOM）",
                          confidence=0.9, newline=_newline(text))
            return result
        if even_nul > half * 0.55 and odd_nul < half * 0.1:
            text = data.decode("utf-16-be", errors="replace")
            result.update(text=text, encoding="utf-16-be", label="UTF-16 BE（无 BOM）",
                          confidence=0.9, newline=_newline(text))
            return result

    # UTF-8 严格优先
    text = _decode_with(data, "utf-8")
    if text is not None:
        result.update(text=text, encoding="utf-8", label="UTF-8",
                      confidence=1.0, newline=_newline(text))
        return result

    # charset_normalizer 通常对中文更准
    guess = None
    try:
        from charset_normalizer import from_bytes
        best = from_bytes(data[:512_000]).best()
        if best is not None and best.encoding:
            enc = best.encoding.lower().replace("_", "-")
            # 统一别名
            alias = {
                "gb2312": "gb18030", "gbk": "gb18030", "gb18030": "gb18030",
                "big5": "big5", "shift-jis": "shift_jis", "shift_jis": "shift_jis",
                "euc-kr": "euc-kr", "cp1252": "cp1252", "windows-1252": "cp1252",
                "ascii": "utf-8", "utf-8": "utf-8",
            }.get(enc, enc)
            if alias in dict(CANDIDATES):
                decoded = _decode_with(data, alias)
                if decoded is not None:
                    guess = (alias, decoded, float(best.coherence or 0.5))
    except Exception:
        guess = None

    if guess is None:
        best_score = -9e9
        best = None
        for enc, label in CANDIDATES:
            decoded = _decode_with(data, enc)
            if decoded is None:
                continue
            score = _score(decoded)
            # 对常见的单字节编码轻微惩罚，避免把中文误判成 cp1252
            if enc in ("cp1252", "latin-1") and any(b >= 0x80 for b in data[:4096]):
                score -= 0.08
            if score > best_score:
                best_score = score
                best = (enc, decoded, label)
        if best:
            enc, decoded, label = best
            result.update(text=decoded, encoding=enc, label=label,
                          confidence=max(0.3, min(0.95, best_score)),
                          newline=_newline(decoded))
            return result

    if guess:
        enc, decoded, coherence = guess
        label = dict(CANDIDATES).get(enc, enc)
        result.update(text=decoded, encoding=enc, label=label,
                      confidence=min(0.99, max(0.55, coherence)),
                      newline=_newline(decoded))
        return result

    # 最终兜底
    text = data.decode("utf-8", errors="replace")
    result.update(text=text, encoding="utf-8", label="UTF-8（含替换符）",
                  confidence=0.2, newline=_newline(text))
    return result


def _newline(text: str) -> str:
    crlf = text.count("\r\n")
    lf = text.count("\n") - crlf
    cr = text.count("\r") - crlf
    if crlf >= lf and crlf >= cr and crlf > 0:
        return "CRLF"
    if cr > lf and cr > 0:
        return "CR"
    return "LF"


def read_text(path: str, encoding: str = "auto", max_bytes: int = 24 * 1024 * 1024) -> dict:
    size = os.path.getsize(path)
    with open(path, "rb") as f:
        data = f.read(max_bytes + 1)
    truncated = len(data) > max_bytes
    if truncated:
        data = data[:max_bytes]
    out = decode_bytes(data, encoding)
    out.update(size=size, truncated=truncated, path=path,
               ext=os.path.splitext(path)[1].lower().lstrip("."),
               lang=lang_for(os.path.splitext(path)[1].lower().lstrip(".")))
    return out


def human_size(n: int | float | None) -> str:
    if n is None:
        return "—"
    n = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"


def hexdump(path: str, offset: int = 0, length: int = 4096) -> dict:
    with open(path, "rb") as f:
        f.seek(offset)
        data = f.read(length)
    lines = []
    for i in range(0, len(data), 16):
        chunk = data[i:i + 16]
        hexpart = " ".join(f"{b:02X}" for b in chunk)
        hexpart = hexpart[:23] + " " + hexpart[23:] if len(chunk) > 8 else hexpart
        ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        lines.append({
            "offset": f"{offset + i:08X}",
            "hex": hexpart.ljust(48),
            "ascii": ascii_part,
        })
    return {"offset": offset, "length": length, "lines": lines,
            "size": os.path.getsize(path), "eof": offset + len(data) >= os.path.getsize(path)}


def strings(path: str, min_len: int = 4, limit: int = 2000) -> list[dict]:
    out = []
    with open(path, "rb") as f:
        data = f.read(8 * 1024 * 1024)
    for m in re.finditer(rb"[\x20-\x7e]{%d,}" % min_len, data):
        raw = m.group()
        try:
            s = raw.decode("ascii")
        except UnicodeDecodeError:
            continue
        out.append({"offset": m.start(), "text": s[:400]})
        if len(out) >= limit:
            break
    # UTF-16LE 字符串
    for m in re.finditer((rb"(?:[\x20-\x7e]\x00){%d,}" % min_len), data):
        try:
            s = m.group().decode("utf-16-le")
        except UnicodeDecodeError:
            continue
        out.append({"offset": m.start(), "text": s[:400], "wide": True})
        if len(out) >= limit:
            break
    out.sort(key=lambda x: x["offset"])
    return out[:limit]


def entropy(data: bytes) -> float:
    if not data:
        return 0.0
    counts = [0] * 256
    for b in data:
        counts[b] += 1
    n = len(data)
    ent = 0.0
    for c in counts:
        if c:
            p = c / n
            ent -= p * math.log2(p)
    return round(ent, 3)


def is_probably_text(path: str) -> bool:
    try:
        with open(path, "rb") as f:
            data = f.read(8192)
        if b"\x00" in data:
            return False
        ctrl = sum(1 for b in data if b < 9 or (13 < b < 32))
        return ctrl / max(len(data), 1) < 0.08
    except OSError:
        return False
