# Reddit post drafts

## Read this first: r/software rule 3

r/software only allows self-promotion for open-source software, **or** on Wednesdays with the correct flair and a post that gives the community something beyond a download link.

OmniView is **not OSI open source**. The core is FSL-1.1-ALv2 (source-available, converts to Apache-2.0 after two years), and the e-book/data plugins contain GPL components. Do **not** call it open source to qualify for the exception.

That means:

- Do **not** post the normal launch post to r/software on a Friday, or any non-Wednesday.
- On Wednesday, use the exact self-promotion flair required by the current sidebar, and write a technical/value post, not an ad.
- If the flair or rules are unclear, send the draft to the mods first. A permanent ban is not worth guessing.
- Today is Friday. Wait until Wednesday and check the subreddit's own clock; do not assume China time equals the mods' time.

If you want the open-source exception, the clean route is to dual-license the core under an OSI license (for example Apache-2.0). FSL cannot be presented as open source.

---

## A. r/software — Wednesday technical post

Use this only on Wednesday, with the exact self-promotion flair from the sidebar, after checking the current rules. Send it to modmail first if possible.

### Title

**How I made a Windows viewer open a 500 MB text file without loading it, and render PDF pages only when needed**

Alternative:

**What I learned building a native Windows viewer with a small core and per-format plugins**

Do not put “download my app” in the title. The technical hook is the value.

### Body

I'm the developer of OmniView, a native Windows file viewer. This post is about the engineering tradeoffs, not just a download link.

The original version was a 105 MB single executable with every parser inside. It worked, but every user paid for formats they never opened, and one dependency change meant shipping the whole thing again.

The current version is a small Qt core plus optional `.ovp` plugins. The parts I found interesting:

**Large text without a giant string**

Files over 8 MB are opened with `mmap`. The viewer decodes a window of about 2 MB at a time, aligned to newlines, and only that window lives in the editor widget.

A 30 MB log might hold 1–2 MB of characters in the widget. A 500 MB file does not become one Python string. Previous/next chunk and percentage jumps are handled by moving the window, not by building a full line index.

**PDF without rasterizing the whole document**

Pages are rendered with `QPdfDocument.render` into a `QImage`, but only pages near the current viewport. Scrolling triggers rendering for the pages that are about to become visible.

The tradeoff: no text selection/search layer in the current viewer. It is a display-first implementation.

**Video without transcoding**

`QMediaPlayer` streams the file through Qt's bundled FFmpeg. Nothing is transcoded and the whole video is not cached. Whether seeking works well depends on the container index, not just the duration.

**Plugins as zip files**

An `.ovp` is a zip with `plugin.json`, an optional `plugin.py`, and optional `site-packages`. The core adds the plugin's `site-packages` to `sys.path` only when the plugin is installed.

A custom viewer implements:

```python
def create_viewer(path, parent=None):
    return MyViewer(path, parent)
```

If the factory raises, OmniView opens a visible error tab with the full traceback. It does not silently fail.

**What I would do differently**

- I would design the plugin manifest and error boundary before building the first viewer.
- I would not call a source-available license “open source”; it causes avoidable arguments.
- I would test the self-extractor while the previous version is still running much earlier. Windows file locks are a real source of installer bugs.

The app is free to download. The core is source-available under FSL-1.1-ALv2; the e-book and data plugins contain GPL components and are distributed separately.

Download: https://github.com/liyabl/-OmniView/releases/latest

Source: https://github.com/liyabl/-OmniView

I'm the developer. If this post is not appropriate for the community, the mods should remove it; I would rather ask first than treat the subreddit as an ad channel.

### r/software checklist

- [ ] It is Wednesday in the subreddit's timezone.
- [ ] I read the current sidebar rules, not an old copy.
- [ ] I used the exact self-promotion flair.
- [ ] I disclosed that I am the developer.
- [ ] The post has technical content beyond the download link.
- [ ] I sent the draft to modmail if anything is ambiguous.
- [ ] I am not crossposting the same text to five subreddits at once.

---

## B. General English post for communities that allow self-promotion

Check each community's rules first. This version is more direct, but still does not call the project open source.

### Title

**OmniView – a native Windows file viewer with optional plugins (PDF, Office, PSD, 3D, archives)**

### Body

Hi everyone,

I built **OmniView**, a native Windows file viewer. The motivation was simple: I kept running into files where looking at them meant installing another full application first — a DOCX, a PSD, a 7z archive, a random 3D model.

It is not a replacement for Office, Photoshop, or AutoCAD. It is a viewer: open the file, inspect it, and move on.

- Native Qt window, CPU only. No Electron or browser shell.
- A small core handles PDF, text/code, images, audio/video, archives, and SQLite.
- Office, e-books, data/models, 3D/CAD/GIS, and RAW/PSD are separate `.ovp` plugins.
- Does not require Office, WPS, Photoshop, AutoCAD, 7-Zip, or FFmpeg to be installed.
- Large text is opened with `mmap` and decoded in ~2 MB windows. Video is streamed. PDF pages render near the viewport.
- If parsing fails, you get a red error tab with the full traceback instead of a silent exit.

Honest limitations: DOCX/PPTX are reflowed natively, not pixel-identical to Office; DWG is currently metadata/header view; STEP/BLEND/SKP/PST are structural views; the exe is unsigned, so SmartScreen may warn.

Download: https://github.com/liyabl/-OmniView/releases/latest  
Source: https://github.com/liyabl/-OmniView  
Chinese README: https://github.com/liyabl/-OmniView/blob/main/README.zh-CN.md

Windows 10/11 x64. Core is FSL-1.1-ALv2 (source-available, converts to Apache-2.0 after two years); the e-book/data plugins contain GPL components and are distributed separately.

I would especially appreciate feedback on formats that fail to open, large-file behavior, and the plugin installation flow.

---

## C. Short version for a comment

I built **OmniView**, a native Windows viewer with a small core and optional per-format plugins. It opens PDF, Office docs, images, audio/video, archives, SQLite, and more without requiring Office/Photoshop/AutoCAD/7-Zip/FFmpeg. Large text is read in 2 MB chunks via `mmap`; video is streamed; PDF pages render on demand. Free download: https://github.com/liyabl/-OmniView/releases/latest

Windows 10/11 x64. Source is FSL-1.1-ALv2; the Office/e-book/data/3D/RAW plugins are separate packages. Not a replacement for the original editors — just a viewer.

---

## D. Where not to post

- **r/opensource**: FSL is not an OSI license. Do not post it there as open source.
- **r/software on a non-Wednesday**: the rule explicitly says permanent ban for self-promotion; do not risk it.
- **r/programming**: self-promotion is heavily restricted; a technical post may still be removed.
- **Multiple subreddits at once**: read each sidebar and post where the tool actually fits.

Possible places to check, not guarantees:

- r/Windows11
- r/Windows10
- r/coolgithubprojects
- a weekly “what are you working on” thread in a relevant community

Every one of those has its own self-promotion rules. Read them before posting.

---

## E. Posting notes

- Upload 3–4 screenshots directly to Reddit. The repo has PDF, PPTX, and 3D screenshots under `docs/`.
- Put the download link in the body once; do not repeat it in every comment.
- Mention that the build is unsigned and SmartScreen may warn. It saves a lot of “is this a virus” comments.
- If GitHub is slow for your audience, add a mirror link, but keep the GitHub release as the canonical source.
- Answer technical questions honestly; “it does not do that yet” is better than overclaiming.
- Do not ask for upvotes or use alternate accounts.

---

## F. 中文备注

如果你坚持只发英文社区，用上面的英文稿。

中文说明保留在：

https://github.com/liyabl/-OmniView/blob/main/README.zh-CN.md

不要在英文帖里把项目称为 “open source”；准确说法是 **source-available under FSL-1.1-ALv2**。这不是文字游戏，r/software 的规则就是按许可证判断的。
