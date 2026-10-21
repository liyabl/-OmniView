# Third-party notices — OmniView 0.2

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

| 组件 | 许可 |
| --- | --- |
| mammoth | BSD-2-Clause |
| python-docx | MIT |
| openpyxl | MIT |
| python-pptx | MIT |
| odfpy | Apache-2.0 |
| lxml | BSD-3-Clause |
| cobble | BSD-2-Clause |
| et_xmlfile | MIT |

插件依赖由 `build_office_plugin.py` 从当前 Python 环境收集；发布插件包时请保留各依赖的 LICENSE 文件。

## Fonts

不附带商业字体；界面使用 Windows 系统字体，文件内容使用系统/文档内字体。
