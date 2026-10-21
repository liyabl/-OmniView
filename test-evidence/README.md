# OmniView 0.3 test evidence

All images are real captures from the native Qt app (not mockups).

Contact sheet: `00_contact_sheet.png`.

| # | File | What it proves |
| --- | --- | --- |
| 01 | `01_pdf.png` | Native QtPdf page rendering, CJK + tables |
| 02 | `02_pptx.png` | Native PPTX slide canvas |
| 03 | `03_xlsx.png` | XLSX table + formula values + cell styling |
| 04 | `04_glb_3d.png` | CPU triangle rasterizer (no GPU) |
| 05 | `05_shp_gis.png` | SHP geometry rendering, local grid |
| 06 | `06_dxf.png` | DXF entity rendering |
| 07 | `07_language_picker.png` | First-run language picker, UN 6 + 30M+ list |
| 08 | `08_large_text_2mb_window.png` | 31.2MB text, only a 2MB window in memory |
| 09 | `09_docx_office_plugin.png` | DOCX through the separate `office.ovp` plugin |
| 10 | `10_missing_plugin.png` | Missing-plugin page (no crash; install on demand) |
| 11 | `11_french_ui.png` | French UI after changing `ui/language` (full shell translation) |
| 12 | `12_error_page.png` | Unknown format shows a visible error page with copy/plugin-manager actions |
| 13 | `13_plugin_manager.png` | Plugin manager: install .ovp from file/URL, remove, developer info; custom `hello` plugin listed |
| 14 | `14_plugin_parse_error.png` | A user plugin that raises shows full traceback, copy/plugin-manager actions |
| 15 | `15_all_plugins.png` | Office, e-book, data, 3D/CAD/GIS, RAW/PSD all installed and enabled |

## Large text measurement

- File: 31.2 MB, 400,000 lines
- Editor buffer: ~1.6 MB characters
- Byte window: 2 MB
- Mode: read-only mmap + previous/next/jump
- Screenshot footer: `31.2 MB · 窗口 2.0 MB · 偏移 0 B (0.0%)`

## Plugin path

`09_docx_office_plugin.png` is rendered after installing `office.ovp` from the release folder.
`10_missing_plugin.png` is the same DOCX with the plugin directory renamed away: the core shows
the plugin page instead of crashing.

## Language picker

`07_language_picker.png` lists 58 entries. The six UN languages have complete catalogs
(`en/zh/fr/es/ru/ar`); other languages are marked `English fallback` until community JSON is
contributed. File content is never translated.



