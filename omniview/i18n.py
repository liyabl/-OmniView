"""Internationalization: UN languages + languages with 30M+ speakers.

Catalogs are plain JSON so the community can replace or extend them.
Missing catalogs fall back to English; the language picker marks them.
"""
from __future__ import annotations

import json
import os

from . import paths

_LANG = "en"
_REQUESTED = "en"
_CATALOG: dict = {}
_LANGS: list[dict] = []


def _load_languages() -> list[dict]:
    global _LANGS
    if _LANGS:
        return _LANGS
    p = os.path.join(os.path.dirname(__file__), "locales", "languages.json")
    try:
        _LANGS = json.load(open(p, "r", encoding="utf-8"))
    except Exception:
        _LANGS = [{"code": "en", "native": "English", "english": "English", "rtl": False, "un": True}]
    return _LANGS


def languages() -> list[dict]:
    return list(_load_languages())


def language(code: str) -> dict:
    for l in _load_languages():
        if l["code"] == code:
            return l
    return _load_languages()[0]


def catalog_exists(code: str) -> bool:
    for base in (os.path.join(paths.DATA, "locales"), os.path.join(os.path.dirname(__file__), "locales")):
        if os.path.exists(os.path.join(base, code + ".json")):
            return True
    return False


def set_language(code: str) -> None:
    global _LANG, _REQUESTED, _CATALOG
    _REQUESTED = code
    _LANG = code if catalog_exists(code) else "en"
    data = {}
    for base in (os.path.join(os.path.dirname(__file__), "locales"), os.path.join(paths.DATA, "locales")):
        p = os.path.join(base, _LANG + ".json")
        if os.path.exists(p):
            try:
                data.update(json.load(open(p, "r", encoding="utf-8")))
            except Exception:
                pass
    _CATALOG = data
    if _LANG != code:
        # English fallback for a language that has no catalog yet
        try:
            _CATALOG.update(json.load(open(os.path.join(os.path.dirname(__file__), "locales", "en.json"), "r", encoding="utf-8")))
        except Exception:
            pass


def current() -> str:
    return _REQUESTED


def rtl() -> bool:
    return bool(language(_REQUESTED).get("rtl"))


def T(key: str, **kwargs) -> str:
    s = _CATALOG.get(key)
    if s is None:
        try:
            en = json.load(open(os.path.join(os.path.dirname(__file__), "locales", "en.json"), "r", encoding="utf-8"))
            s = en.get(key, key)
        except Exception:
            s = key
    try:
        return s.format(**kwargs)
    except Exception:
        return s
