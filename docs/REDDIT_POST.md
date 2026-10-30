# Reddit post draft

## Title options

1. **OmniView – a native Windows file viewer with optional plugins (PDF, Office, PSD, 3D, archives)**
2. **I built a Windows viewer that doesn't make you install Office, Photoshop, or 7-Zip just to look at a file**
3. **OmniView 0.3.2 – small core, per-format plugins, native Qt, CPU only**

The first one is the safest for r/software.

---

## Body

Hi everyone,

I built **OmniView**, a native Windows file viewer. The motivation was simple: I kept running into files where looking at them meant installing another full application first — a DOCX, a PSD, a 7z archive, a random 3D model.

OmniView is not a replacement for Office, Photoshop, or AutoCAD. It is a viewer: open the file, inspect it, and get on with your day. Editing still belongs in the real tools.

**How it works**

- Native Qt window, CPU only. No Electron, no browser shell.
- A small core handles PDF, text/code, images, audio/video, archives, and SQLite.
- Formats that need heavier dependencies are separate `.ovp` plugins: Office, e-books, data/models, 3D/CAD/GIS, RAW/PSD.
- The core does not require Office, WPS, Photoshop, AutoCAD, 7-Zip, or FFmpeg to be installed.
- The setup is a self-extracting launcher. Core is about 62 MB compressed, plugins are installed only if you want them.

**Large files**

This was the part I cared about most:

- Text over 8 MB is opened with `mmap` and decoded in ~2 MB windows instead of being loaded into the editor as one string.
- Video is streamed through Qt's bundled FFmpeg, not transcoded or fully cached.
- PDF pages are rendered near the viewport, not the whole document at once.
- Archives are listed through bundled 7-Zip; entries are extracted only when opened.

**Interface**

- First launch asks for a language.
- 58 languages are listed (UN official languages + languages with 30M+ speakers).
- Complete catalogs right now: English, Chinese, French, Spanish, Russian, Arabic. The rest fall back to English and are marked in the picker.
- File contents are never translated.

**Plugins and errors**

- You can install an `.ovp` from the plugin manager, from the missing-plugin page, by drag and drop, or with `OmniView.exe --install-plugin path\to\file.ovp`.
- Users can build their own `.ovp`; it is just a zip with `plugin.json` and an optional `plugin.py` returning a `ViewerBase`.
- If parsing fails, you get a red error tab with the full traceback, not a silent exit or a modal that disappears.

**What it does not do**

- DOCX/PPTX are reflowed natively, not pixel-identical to Office.
- DWG is currently metadata/header/string view. DXF renders properly.
- STEP/BLEND/SKP/PST are structural views.
- Very large text is read-only chunked mode.
- The executable is unsigned, so SmartScreen may warn.
- `.ovp` plugins execute Python code; only install ones you trust.

**Download / source**

- Releases: https://github.com/liyabl/-OmniView/releases/latest
- Source: https://github.com/liyabl/-OmniView
- Chinese README: https://github.com/liyabl/-OmniView/blob/main/README.zh-CN.md
- License: core is FSL-1.1-ALv2 (source-available, converts to Apache-2.0 after two years). The e-book and data plugins include GPL components and are distributed separately under GPL-compatible terms. Details are in THIRD_PARTY_NOTICES.md.

Windows 10/11 x64.

I would especially appreciate feedback on:

- formats that fail to open
- large-file behavior
- plugin installation UX
- whether the Office/PDF rendering is good enough for a viewer

If you try it, thanks. If it is not for you, that is fine too — I would rather hear what is broken than have it silently fail.

---

## Shorter version for a comment / crosspost

I built **OmniView**, a native Windows viewer with a small core and optional per-format plugins. It opens PDF, Office docs, images, audio/video, archives, SQLite, and more without requiring Office/Photoshop/AutoCAD/7-Zip/FFmpeg. Large text is read in 2 MB chunks via `mmap`; video is streamed; PDF pages render on demand. Free download: https://github.com/liyabl/-OmniView/releases/latest

Windows 10/11 x64. Source is FSL-1.1-ALv2; the Office/e-book/data/3D/RAW plugins are separate packages. Not a replacement for the original editors — just a viewer.

---

## Posting notes

- Check the subreddit's self-promotion rules before posting. r/software, r/Windows10, and r/Windows11 are more appropriate than r/opensource, because FSL is source-available but not OSI open source.
- Do not post the same text to five subreddits in one hour. Pick one, answer comments, then crosspost later if it is welcome.
- Upload 3–4 screenshots directly to Reddit. The repo has PDF, PPTX, and 3D screenshots under `docs/`.
- Put the download link in the body once; do not repeat it in every comment.
- Mention that SmartScreen may warn because the build is unsigned. It saves a lot of “is this a virus” comments.
- If GitHub is slow for your audience, add a mirror link, but keep the GitHub release as the canonical source.
