# OmniView · 万象查看器

一个 Windows 上的文件查看器。

起因很普通：电脑里总会躺着一些 PDF、Word、Excel、PSD、压缩包、视频和不知道用什么打开的文件。为了看其中一个，去装一整套 Office、Photoshop 或者转换工具，实在有点烦。

OmniView 想做的，就是把这件事变简单一点：一个原生窗口，能直接看常见的、不太常见的格式；需要额外解析的格式再装插件，不用为用不到的东西付体积。

它不是 Office、Photoshop、AutoCAD 的替代品，也不是什么“万能神器”。它更像一个顺手的小工具：能看、能翻、能确认内容，复杂编辑请交给专业软件。

![PDF](docs/shot_native_pdf.png)

![PPTX](docs/shot_pptx.png)

![CPU 三角面渲染](docs/shot_native_球体_glb.png)

![Build](https://img.shields.io/badge/build-GitHub%20Actions-2088FF?logo=githubactions)
![Platform](https://img.shields.io/badge/platform-Windows%2010%2F11%20x64-0078D4)
![CPU](https://img.shields.io/badge/runtime-CPU%20only-4fd1c5)
![License](https://img.shields.io/badge/license-FSL--1.1--ALv2-7aa2ff)

---

## 下载和安装

最新版本在 [Releases](https://github.com/liyabl/-OmniView/releases/latest)。

先下载 `OmniView-Setup.exe`，双击运行。它会解压到：

```text
%LOCALAPPDATA%\OmniView\0.3
```

然后自动启动。

第一次打开会问界面语言。选完以后，文件内容仍然按原文显示，不会自动翻译。

### 只装核心也可以

核心自带 PDF、文本、代码、图片、音视频、压缩包和 SQLite。平时只是看 PDF、图片、ZIP，到这里就够了。

### 需要 Office/PSD/3D 时再装插件

Release 里还有几个 `.ovp`：

```text
office.ovp   DOCX / XLSX / PPTX / ODT / ODP / RTF
ebook.ovp    EPUB / MOBI / AZW3
data.ovp     Access / DBF / HDF5 / ONNX / PT / PKL / TFLite / 邮件库
pro.ovp      STL / OBJ / GLB / DXF / SHP / KML / GPX / EXE / ELF / 字体
raw.ovp      PSD / AI / 相机 RAW
hello.ovp    一个用户自制插件示例
```

最省事的是双击 `Install-All-Plugins.cmd`。它会关掉正在运行的 OmniView，把同目录的插件装到：

```text
%LOCALAPPDATA%\OmniView\plugins\
```

然后重新启动 OmniView。

也可以只装一个：

- 打开对应文件，缺插件页面点“从 .ovp 文件安装…”
- 或者帮助 → 插件管理… → 安装 `.ovp…`
- 或者直接把 `.ovp` 拖进窗口

几个说明：

- 安装/覆盖时会关闭正在运行的 OmniView，未保存的文本请先保存。
- 未做代码签名，Windows SmartScreen 可能提示“未知发布者”；选择“更多信息 → 仍要运行”。
- 插件不是越多越好，不用就不装。

---

## 它现在能做什么

核心不依赖本机的 Office、WPS、Photoshop、AutoCAD、7-Zip 或 FFmpeg。

- PDF：原生 PDFium 渲染，支持翻页、缩放、适合宽度
- 文本/代码：常见编码识别、语法高亮、文本可编辑
- 图片：PNG/JPEG/GIF/WebP/TIFF/BMP/ICO/SVG 等
- 音视频：Qt 内置 FFmpeg 解码
- 压缩包：ZIP/7Z/RAR/TAR/ISO 等，内置 7-Zip
- SQLite：直接打开数据库看表和记录

插件补上：

- Office 文档：DOCX/ODT/RTF/XLSX/PPTX/ODP
- 电子书：EPUB/MOBI/AZW3
- 数据与模型：Access/DBF/HDF5/ONNX/PT/PKL/TFLite
- 3D/CAD/GIS：STL/OBJ/GLB/DXF/SHP/KML/GPX
- RAW/PSD：相机 RAW、Photoshop PSD、AI

**但要说清楚：**

- DOCX/PPTX 是原生重排，不是 Word/PowerPoint 的像素级分页。
- DWG 目前只读文件头/版本/字符串；DXF 能正常画。
- STEP/BLEND/SKP/PST 是结构或元数据视图，不是完整专业内核。
- 视频能不能拖动，取决于文件本身有没有索引；没有索引的流只能按顺序看。

---

## 为什么不是一个巨大的 exe

最早的确做过一个 105 MB 的单文件版本，所有东西都塞在里面。

能用，但有两个问题：

1. 每个用户都要为不用的格式付体积；
2. 想换一个依赖，就得重新发整个包。

现在拆成三层：

- **核心**：原生窗口、PDF、文本、图片、音视频、压缩包、SQLite
- **插件**：Office、电子书、数据、3D、RAW 各自独立
- **Setup**：自解压，第一次运行时解压核心

核心解压后大约 186 MB，Setup 约 62 MB。插件从 1 MB 到 25 MB 不等，装不装由你决定。

---

## 大文件是怎么处理的

这块是实际做过取舍的。

### 文本

超过 8 MB 的文本不再整个读进编辑器，而是用 `mmap` 打开，每次只解码 2 MB 左右的窗口。

上一段、下一段、百分比跳转都在；当前窗口之外的内容不占编辑器内存。

一个 30 MB 的日志，编辑器里可能只持有 1–2 MB 字符；500 MB 的文件也不会一次性塞进 Python 字符串。

### 视频

用 Qt 的 `QMediaPlayer` 流式读取，不转码、不把整段视频缓存到内存。

几百小时的视频能不能打开，主要看容器和索引，不是看时长。没有索引的损坏文件就只能顺序播。

### PDF

只渲染当前视口附近的页面，滚动时再补。不会一打开就把整本 PDF 全部渲染成图片。

### 压缩包

列表由 7-Zip 输出，打开某个条目时才解压到缓存。

---

## 多语言

第一次启动会让你选语言。

列表里包括联合国 6 种官方语言，以及使用人口 3000 万以上的语言，总共 58 项。

但翻译进度要说实话：

- 完整目录：`en / zh / fr / es / ru / ar`
- 其余语言目前是 `English fallback`，选择器里会标出来

语言文件就是普通 JSON：

```text
omniview/locales/<code>.json
```

社区可以直接 PR，也可以放到：

```text
%LOCALAPPDATA%\OmniView\locales\<code>.json
```

只翻译界面，不翻译文件内容。

---

## 插件和自己做插件

`.ovp` 就是一个 zip：

```text
myplugin.ovp
  plugin.json
  plugin.py          # 可选，自定义查看器
  site-packages/     # 可选，依赖
```

`plugin.json`：

```json
{
  "id": "hello",
  "name": "Hello Viewer",
  "version": "1.0.0",
  "formats": ["hello"],
  "entry": "plugin.py",
  "factory": "create_viewer"
}
```

`plugin.py` 里返回一个 `ViewerBase`：

```python
from omniview.ui.common import ViewerBase


class HelloViewer(ViewerBase):
    ...


def create_viewer(path, parent=None):
    return HelloViewer(path, parent)
```

仓库里已经有现成模板：

```powershell
python build_ovp.py --template plugins/hello
python build_ovp.py --source plugins/hello --out plugins/hello.ovp
```

把 `hello.ovp` 装进去，再打开一个 `.hello` 文件，就能看到效果。

完整规范在 [docs/PLUGIN_FORMAT.md](docs/PLUGIN_FORMAT.md)。

### 解析失败会怎样

不会静默退出，也不会只弹一个框就结束。

会打开一个红色的“无法解析此文件”页面，显示：

- 文件路径
- 插件 id
- 完整 traceback
- 复制错误
- 打开插件管理
- 打开文件位置

插件没装时是另一套页面：显示插件大小、安装按钮，以及“从 .ovp 文件安装…”。

---

## 从源码运行

```powershell
pip install -r requirements.txt
python app.py
```

如果只是跑核心，不需要装插件依赖。

### 构建完整版本

```powershell
pip install -r requirements.txt -r plugin_requirements.txt -r dev-requirements.txt

python build_office_plugin.py
python build_plugins.py
.\build_core.ps1
.\build_setup.ps1
```

会生成：

```text
release\OmniView-Setup.exe
plugins\*.ovp
```

构建 Setup 需要本机有 7-Zip，或者设置：

```powershell
$env:SEVENZIP = "C:\path\to\7z.exe"
```

推 `v*` tag 后，GitHub Actions 会自动构建并发布 Release。

---

## 卸载

运行 `packaging\Uninstall.cmd`，或手动删除：

```text
%LOCALAPPDATA%\OmniView\0.3
```

插件默认保留在：

```text
%LOCALAPPDATA%\OmniView\plugins
```

要彻底删除，把 plugins 目录也删掉。

---

## 已知问题

- DOCX/PPTX 做不到 Office 的逐页像素级一致。
- DWG 仍是元数据视图；完整 DWG 要等 LibreDWG 插件。
- STEP/BLEND/SKP/PST 只展示结构。
- 视频 seek 依赖文件索引。
- 超大文本是只读分块，不能在原文件上直接编辑。
- 插件没有签名/沙箱，`.ovp` 会执行 Python 代码，只安装信任的包。
- 插件校验和、增量更新、崩溃上报还没做。

---

## 许可

- 核心和自行编写的插件代码：**FSL-1.1-ALv2**，两年后转为 Apache-2.0。完整文本见 [LICENSE](LICENSE)。
- `ebook.ovp` 含 GPL-3.0 的 `mobi`/KindleUnpack、GPL-2.0 的 `unidecode`，插件包整体按 GPL-3.0 兼容方式分发。
- `data.ovp` 含 GPL-3.0 的 `extract-msg`、`RTFDE`，插件包整体按 GPL-3.0 兼容方式分发。
- `office.ovp`、`pro.ovp`、`raw.ovp` 的依赖以 MIT/BSD/Apache 为主；Qt/PySide6 是 LGPLv3；7-Zip 是 LGPL。
- 第三方组件和插件内 LICENSE 见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

FSL 核心和 GPL 插件是分开的组件，不要把整个 Release 说成 FSL 或 MIT。
