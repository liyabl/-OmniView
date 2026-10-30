# Third-party notices — OmniView 0.3

**English** | [简体中文](THIRD_PARTY_NOTICES.zh-CN.md)

OmniView's core and original plugin code are licensed under **FSL-1.1-ALv2** (Functional Source License, converting to Apache-2.0 after two years), not MIT. Third-party components are listed below.

## Core

| Component | License |
| --- | --- |
| Qt 6 / PySide6 (QtCore/Gui/Widgets/Pdf/Multimedia) | LGPL v3 |
| 7-Zip (`assets/7z/7z.exe`, `7z.dll`) | LGPL + unRAR restriction |
| Pillow | HPND |
| numpy | BSD-3-Clause |
| Python-Markdown | BSD-3-Clause |
| Pygments | BSD-2-Clause |
| PyInstaller bootloader | GPL-2.0 with exception |

Qt LGPL compliance: the project source is public and the build scripts are reproducible; Qt is loaded as shared libraries. The full 7-Zip license is in `assets/7z/License.txt`.

## Office plugin (`office.ovp`)

mammoth (BSD-2-Clause), python-docx (MIT), openpyxl (MIT), python-pptx (MIT), odfpy (Apache-2.0), lxml (BSD-3-Clause), cobble (BSD-2-Clause), et_xmlfile (MIT).

## E-book plugin (`ebook.ovp`)

| Component | License |
| --- | --- |
| mobi / KindleUnpack | GPL-3.0 |
| loguru | MIT |
| imghdr (standard-imghdr) | PSF |
| unidecode | GPL-2.0 |

**Note:** this package contains GPL-3.0/GPL-2.0 components. The plugin package as a whole is distributed under GPL-3.0-compatible terms.

## Data plugin (`data.ovp`)

| Component | License |
| --- | --- |
| h5py | BSD-3-Clause |
| ONNX | Apache-2.0 |
| protobuf (google) | BSD-3-Clause |
| ml_dtypes | Apache-2.0 |
| tflite | Apache-2.0 |
| flatbuffers | Apache-2.0 |
| dbf | BSD-3-Clause |
| aenum | BSD-3-Clause |
| access-parser | MIT |
| construct | MIT |
| tabulate | MIT |
| extract-msg | GPL-3.0 |
| olefile | BSD-2-Clause |
| tzlocal | MIT |
| compressed-rtf | MIT |
| ebcdic | MIT |
| beautifulsoup4 (bs4) | MIT |
| RTFDE | GPL-3.0 |
| red-black-tree-mod | MIT |
| chardet | MIT |

**Note:** `extract-msg` and `RTFDE` are GPL-3.0. The plugin package as a whole is distributed under GPL-3.0-compatible terms.

## Pro plugin (`pro.ovp`)

| Component | License |
| --- | --- |
| ezdxf | MIT |
| pyparsing | MIT |
| pyshp / shapefile | MIT |
| fontTools | MIT |
| pefile | MIT |
| pyelftools | public domain |
| macholib | MIT |
| altgraph | MIT |
| rpmfile | BSD-2-Clause |
| zstandard | BSD-3-Clause |

## RAW plugin (`raw.ovp`)

| Component | License |
| --- | --- |
| rawpy | MIT |
| LibRaw (bundled by rawpy) | LGPL-2.1 / CDDL |
| psd-tools | MIT |
| attrs | MIT |

## Fonts

No commercial fonts are bundled. The UI uses Windows system fonts; file content uses system or document-embedded fonts.

Plugin dependencies are collected by `build_office_plugin.py` / `build_plugins.py` from the current Python environment. Plugin packages include their dependency LICENSE files.
