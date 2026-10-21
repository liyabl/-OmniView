# Third-party notices — OmniView 0.3

OmniView 源代码采用 MIT License。构建产物包含以下第三方组件：

## Core

| 组件 | 许可 |
| --- | --- |
| Qt 6 / PySide6（QtCore/Gui/Widgets/Pdf/Multimedia） | LGPL v3 |
| 7-Zip（`assets/7z/7z.exe`, `7z.dll`） | LGPL + unRAR restriction |
| Pillow | HPND |
| numpy | BSD-3-Clause |
| Python-Markdown | BSD-3-Clause |
| Pygments | BSD-2-Clause |
| PyInstaller bootloader | GPL-2.0 with exception |

Qt LGPL 合规：项目源码公开，构建脚本可复现；以动态库方式加载 Qt。7-Zip 完整许可见 `assets/7z/License.txt`。

## Office 插件（`office.ovp`）

mammoth (BSD-2-Clause), python-docx (MIT), openpyxl (MIT), python-pptx (MIT), odfpy (Apache-2.0), lxml (BSD-3-Clause), cobble (BSD-2-Clause), et_xmlfile (MIT).

## E-book 插件（`ebook.ovp`）

| 组件 | 许可 |
| --- | --- |
| mobi / KindleUnpack | GPL-3.0 |
| loguru | MIT |
| imghdr (standard-imghdr) | PSF |
| unidecode | GPL-2.0 |

**注意：** 包含 GPL-3.0/GPL-2.0 组件。若分发此插件，请遵守 GPL；闭源商业发行请移除或替换该插件。

## Data 插件（`data.ovp`）

| 组件 | 许可 |
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
| chardet | LGPL-2.1 |

**注意：** `extract-msg`、`RTFDE` 为 GPL-3.0。若分发此插件，请遵守 GPL。

## Pro 插件（`pro.ovp`）

| 组件 | 许可 |
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

## RAW 插件（`raw.ovp`）

| 组件 | 许可 |
| --- | --- |
| rawpy | MIT |
| LibRaw (bundled by rawpy) | LGPL-2.1 / CDDL |
| psd-tools | MIT |
| attrs | MIT |

## Fonts

不附带商业字体；界面使用 Windows 系统字体，文件内容使用系统/文档内字体。

插件依赖由 `build_office_plugin.py` / `build_plugins.py` 从当前 Python 环境收集；发布插件包时请保留各依赖的 LICENSE 文件。
