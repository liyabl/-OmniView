# OmniView 0.3 · 万象查看器

> 原生 Windows 查看器。核心很小，格式做成插件；打开巨大的文本/视频不会把内存撑死。

OmniView 0.3 从 0.2 的“单 exe 全家桶”重构成：

- **核心 Shell**：原生 Qt Widgets 窗口，只内置 PDF、文本、图片、音视频、压缩包、代码、SQLite。
- **`.ovp` 插件**：Office、电子书、数据/模型、3D/CAD/GIS、RAW/PSD 按需下载；用户点开对应文件时才提示安装。
- **自解压 SFX**：`OmniView-Setup.exe` 内含压缩后的核心，运行时解压到 `%LOCALAPPDATA%\OmniView\0.3` 再启动。
- **多语言**：首次启动选择语言；UN 6 种内置完整目录，其他 30M+ 语言列出并由社区 JSON 补齐。
- **大文件**：文本 2MB 窗口 + mmap；视频流式解码/拖动；PDF 只渲染可见页。

![Build](https://img.shields.io/badge/build-GitHub%20Actions-2088FF?logo=githubactions)
![Platform](https://img.shields.io/badge/platform-Windows%2010%2F11%20x64-0078D4)
![CPU](https://img.shields.io/badge/runtime-CPU%20only-4fd1c5)
![License](https://img.shields.io/badge/license-FSL--1.1--ALv2-7aa2ff)

![原生 PDF](docs/shot_native_pdf.png)

![原生 PPTX](docs/shot_pptx.png)

![CPU 三角面](docs/shot_native_球体_glb.png)

---

## 下载

- `OmniView-Setup.exe`（约 62 MB）：自解压核心，双击运行。
- `office.ovp`（约 7 MB）：DOCX / XLSX / PPTX / ODT / ODP / RTF。
- `ebook.ovp`（约 0.8 MB）：EPUB / MOBI / AZW3。
- `data.ovp`（约 25 MB）：Access / DBF / HDF5 / ONNX / PT / PKL / TFLite / 邮件库。
- `pro.ovp`（约 8 MB）：STL / OBJ / GLB / DXF / SHP / KML / GPX / EXE / ELF / 字体。
- `raw.ovp`（约 2 MB）：PSD / AI / 相机 RAW。
- `hello.ovp`：用户自制插件示例。
- `安装全部插件.cmd`：一次安装上面全部插件。

首次启动会要求选择界面语言；文件内容永远按原文显示。

---

## 为什么不是把全部库塞进一个 exe

0.1 的 105 MB 单文件能打开很多格式，但每个用户都为不用的格式付体积和启动成本。0.2 改成：

| 层 | 内容 | 体积 |
| --- | --- | --- |
| Core | Qt Widgets、QtPdf、QtMultimedia/FFmpeg、图片、压缩包、文本引擎、SQLite、插件管理器、i18n | 解压后约 186 MB，自解压包约 62 MB |
| Office 插件 | mammoth / python-docx / openpyxl / python-pptx / odfpy / lxml | 约 7 MB |
| E-book 插件 | mobi / loguru / imghdr | 约 0.8 MB |
| Data 插件 | h5py / onnx / tflite / dbf / access-parser / extract-msg | 约 25 MB |
| Pro 插件 | ezdxf / pyshp / fontTools / pefile / pyelftools / macholib | 约 8 MB |
| RAW 插件 | rawpy / psd-tools | 约 2 MB |

核心只加载实际用到的模块；第三方重依赖在插件目录的 `site-packages` 中，安装后才加入 `sys.path`。

---

## 大文件策略

### 文本：2MB 滑动窗口

- 用 `mmap` 打开文件，不把 500MB 读进 Python 字符串。
- 每次只解码 2MB，按换行对齐，`QPlainTextEdit` 只持有当前窗口。
- 上一段/下一段/百分比跳转；编码检测只读前 256KB。
- 8MB 以下仍使用普通可编辑文本查看器；超过则自动进入只读分块模式。

### 视频：流式解码

- `QMediaPlayer` + Qt 内置 FFmpeg，按需读取/拖动，不转码、不缓存整段。
- 几百小时的 MP4/MKV 可以直接打开和 seek；能否播放取决于容器索引和编码，不取决于时长。
- 不把视频帧一次性解码进内存。

### PDF：只渲染可见页

- `QPdfDocument.render` -> QImage -> QLabel，页面按视口宽度渲染。
- 只渲染视口附近的页，滚动时按需补渲染；不一次性渲染整本。

### 压缩包

- 列表由 7-Zip 流式输出；打开条目时才解压到缓存。

---

## 多语言

首次启动 `LanguageDialog` 列出：

- 联合国 6 种官方语言：阿拉伯语、中文、英语、法语、俄语、西班牙语；
- 使用人口 3000 万+ 的语言（共 58 项，含印地语、孟加拉语、葡萄牙语、印尼语、日语、德语、土耳其语、越南语、韩语、意大利语、波斯语、泰语、泰米尔语、乌尔都语等）。

目录是普通 JSON：`omniview/locales/<code>.json`。社区可以直接 PR，或放到：

```
%LOCALAPPDATA%\OmniView\locales\<code>.json
```

当前内置完整目录：`en / zh / fr / es / ru / ar`；其余语言在补齐前回退英文，选择器会标注 `English fallback`。内容不翻译，只翻译界面。

---

## 插件格式 `.ovp`

```
office.ovp (zip)
  plugin.json
  site-packages/
    mammoth/ ...
    docx/ ...
    openpyxl/ ...
    pptx/ ...
    lxml/ ...
```

`plugin.json`：

```json
{
  "id": "office",
  "name": "Office 文档",
  "version": "0.3.0",
  "formats": ["docx", "odt", "rtf", "xlsx", "pptx", "odp"],
  "entry": ""
}
```

安装后解压到 `%LOCALAPPDATA%\OmniView\plugins\<id>`，`site-packages` 加入 `sys.path`。打开对应扩展名时：

1. 未安装 -> `MissingPluginViewer`，显示插件大小和“安装插件”；
2. 已安装 -> 加载插件依赖，创建原生查看器；
3. 插件损坏/缺依赖 -> 明确报错，不影响核心。

---

## 构建

```powershell
# 0. 依赖 + 构建工具 + 全部插件依赖
pip install -r requirements.txt -r plugin_requirements.txt -r dev-requirements.txt

# 1. 核心 onedir
.\build_core.ps1

# 2. 自解压 Setup（PyInstaller 单文件引导器；需要 7-Zip）
.\build_setup.ps1

# 3. 全部插件（已安装依赖时）
python build_office_plugin.py
python build_plugins.py
```

产物：

- `release\OmniView-Setup.exe`：自解压核心；
- `plugins\office.ovp`、`ebook.ovp`、`data.ovp`、`pro.ovp`、`raw.ovp`、`hello.ovp`：独立插件；
- `dist\OmniView\OmniView.exe`：调试用核心目录。

核心构建会排除 Office/数据/3D/RAW 的重依赖，避免把未使用库打进主程序。

在线安装按钮需要设置环境变量 `OMNIVIEW_PLUGIN_BASE` 指向你的 Releases 插件目录；没设置时请用“从 .ovp 文件安装…”，不会因为空地址报 404。

## 插件管理（0.3 新增）

- 帮助 → 插件管理…：安装 `.ovp`、从 URL 安装、移除、打开插件目录。
- 缺插件页：`从 .ovp 文件安装…`。
- 把 `.ovp` 直接拖进窗口也可以安装。
- 命令行：`OmniView.exe --install-plugin path\to\plugin.ovp`
- 解析失败不会再弹一个框消失，而是打开红色“无法解析此文件”标签页，显示完整 traceback、复制错误、打开插件管理。

## 自制 OVP（0.3 新增）

`.ovp` 就是 zip：`plugin.json` + 可选 `plugin.py` + `site-packages/`。

```powershell
python build_ovp.py --template plugins/hello
python build_ovp.py --source plugins/hello --out plugins/hello.ovp
```

`plugin.py` 暴露：

```python
def create_viewer(path, parent=None):
    return MyViewer(path, parent)  # 必须返回 ViewerBase 子类
```

完整规范：[docs/PLUGIN_FORMAT.md](docs/PLUGIN_FORMAT.md)。示例插件：`plugins/hello/`。

## 卸载

运行 `packaging\Uninstall.cmd`，或手动删除：

```text
%LOCALAPPDATA%\OmniView\0.3
```

插件在 `%LOCALAPPDATA%\OmniView\plugins`，默认保留；要彻底删除也删这个目录。

## 已知边界

- DOCX/PPTX 是原生重排，不是 Word/PowerPoint 像素级分页。
- DWG 仍只展示文件头/字符串；DXF 完整渲染。完整 DWG 需要 LibreDWG 插件。
- STEP/BLEND/SKP/PST 是结构/元数据视图。
- 视频能否 seek 取决于文件索引；无索引的损坏流只能顺序播放。
- 超大文本是只读分块；不会把 500MB 一次性塞进编辑器。
- 插件签名/校验和、增量更新、崩溃上报是下一阶段。

---

## 许可

- **核心与自行编写的插件代码**：**FSL-1.1-ALv2**（Functional Source License 1.1，两年后转为 Apache-2.0）。完整文本见 [LICENSE](LICENSE)。
- **`ebook.ovp`**：包含 GPL-3.0 的 `mobi`/KindleUnpack、GPL-2.0 的 `unidecode`，**插件包整体按 GPL-3.0 兼容方式分发**。
- **`data.ovp`**：包含 GPL-3.0 的 `extract-msg`、`RTFDE`，**插件包整体按 GPL-3.0 兼容方式分发**。
- `office.ovp`、`pro.ovp`、`raw.ovp` 为 MIT/BSD/Apache 等宽松许可依赖；Qt/PySide6 为 LGPLv3；7-Zip 为 LGPL。
- 插件包内已收集依赖的 LICENSE 文件；完整清单见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

核心 FSL 与 GPL 插件是**相互独立的组件**；不要把 `ebook.ovp` / `data.ovp` 宣称为 FSL 或 MIT。











