# OmniView `.ovp` 插件格式（0.3）

`.ovp` 本质是 **zip**，不需要编译。用户可以自己制作、手动安装、拖进窗口安装。

## 目录结构

```
myplugin.ovp
  plugin.json          # 必须
  plugin.py            # 可选：自定义 Viewer
  site-packages/       # 可选：Python 依赖
  assets/              # 可选：插件自己的资源
```

## plugin.json

```json
{
  "id": "hello",
  "name": "Hello Viewer",
  "version": "1.0.0",
  "api": 1,
  "formats": ["hello"],
  "entry": "plugin.py",
  "factory": "create_viewer"
}
```

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `id` | 是 | 字母/数字/`_ . -`，1–64 字符；安装目录名 |
| `name` | 是 | 显示名 |
| `version` | 否 | 默认 `0.0.0` |
| `formats` | 是 | 小写扩展名数组，不带点 |
| `entry` | 否 | `plugin.py` 或包名；没有则为纯依赖包 |
| `factory` | 否 | 默认 `create_viewer` |
| `api` | 否 | 当前为 1 |

## 自定义 Viewer

`plugin.py`：

```python
from PySide6.QtWidgets import QLabel
from omniview.ui.common import ViewerBase


class HelloViewer(ViewerBase):
    def __init__(self, path, parent=None):
        super().__init__(path, parent)
        text = open(path, "r", encoding="utf-8", errors="replace").read()
        label = QLabel(text)
        label.setWordWrap(True)
        self.root.addWidget(label, 1)
        self.info = {"格式": "HELLO", "插件": "hello"}


def create_viewer(path, parent=None):
    return HelloViewer(path, parent)
```

约束：

- `create_viewer(path, parent=None)` 必须返回 `ViewerBase` 子类；
- 可以直接 `from omniview...` 使用核心 API；
- 插件目录与 `site-packages` 会加入 `sys.path`；
- 异常不会被吞掉：OmniView 会打开一个红色的 **“无法解析此文件”** 标签页，显示完整 traceback。

## 纯依赖包

Office 插件就是纯依赖包：`plugin.json` 里不写 `entry`，只提供 `site-packages`，由核心已有的 DOCX/XLSX/PPTX 查看器调用。

```json
{
  "id": "office",
  "name": "Office 文档",
  "version": "0.3.0",
  "formats": ["docx", "xlsx", "pptx", "odt", "odp", "rtf"]
}
```

## 制作与构建

```powershell
# 生成模板
python build_ovp.py --template plugins/hello

# 修改 plugins/hello/plugin.json 和 plugin.py 后打包
python build_ovp.py --source plugins/hello --out plugins/hello.ovp
```

## 安装方式

1. **界面**：帮助 → 插件管理… → 安装 `.ovp…`
2. **缺插件页**：打开文件 → “从 .ovp 文件安装…”
3. **拖拽**：把 `.ovp` 直接拖进 OmniView 窗口
4. **命令行**：`OmniView.exe --install-plugin path\to\my.ovp`
5. **手动**：解压到 `%LOCALAPPDATA%\OmniView\plugins\<id>\`

## 校验与错误

安装前会验证：

- 必须是 zip；
- 根目录必须有 `plugin.json`；
- `id` 合法；
- `formats` 非空；
- `entry` 指向的文件必须在包内；
- 不允许 `..` 路径穿越。

验证失败会直接提示原因，例如：

```
不是有效的 .ovp：根目录缺少 plugin.json
plugin.json 解析失败：Expecting value: line 1 column 1
entry 指向的文件不在包内：plugin.py
```

## 安全提示

`.ovp` 会执行 Python 代码。只安装你信任的插件。0.3 还没有签名/沙箱；后续会加 SHA-256、签名和权限声明。
