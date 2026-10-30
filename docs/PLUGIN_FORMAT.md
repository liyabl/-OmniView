# OmniView `.ovp` plugin format (0.3)

**English** | [简体中文](PLUGIN_FORMAT.zh-CN.md)

An `.ovp` file is a **zip archive**. Nothing is compiled. You can make one yourself, install it manually, or drag it into OmniView.

## Layout

```
myplugin.ovp
  plugin.json          # required
  plugin.py            # optional: custom viewer
  site-packages/       # optional: Python dependencies
  licenses/            # recommended: dependency licenses
```

## `plugin.json`

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

| Field | Required | Notes |
| --- | --- | --- |
| `id` | yes | letters, digits, `_ . -`; 1–64 chars; used as the install directory |
| `name` | yes | display name |
| `version` | no | defaults to `0.0.0` |
| `formats` | yes | lowercase extensions without dots |
| `entry` | no | `plugin.py` or a module/package name; omit for a dependency-only pack |
| `factory` | no | defaults to `create_viewer` |
| `api` | no | currently `1` |

## Custom viewer

`plugin.py`:

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
        self.info = {"format": "HELLO", "plugin": "hello"}


def create_viewer(path, parent=None):
    return HelloViewer(path, parent)
```

Rules:

- `create_viewer(path, parent=None)` must return a `ViewerBase` subclass.
- The plugin directory and its `site-packages` are added to `sys.path`.
- Exceptions are not swallowed: OmniView opens a red **Unable to parse this file** tab with the full traceback.

## Dependency-only packs

The Office plugin is a dependency-only pack: no `entry`, just `site-packages`; the core viewers use those dependencies.

```json
{
  "id": "office",
  "name": "Office Documents",
  "version": "0.3.0",
  "formats": ["docx", "xlsx", "pptx", "odt", "odp", "rtf"]
}
```

## Build

```powershell
# create a starter template
python build_ovp.py --template plugins/hello

# edit plugins/hello/plugin.json and plugin.py, then package
python build_ovp.py --source plugins/hello --out plugins/hello.ovp
```

`build_ovp.py` runs `py_compile` on the entry file before packaging, so a syntax error is caught at build time.

## Install

1. **Plugin Manager**: Help → Plugin Manager… → Install `.ovp…`
2. **Missing-plugin page**: “Install from .ovp file…”
3. **Drag and drop**: drop the `.ovp` into the OmniView window
4. **Command line**: `OmniView.exe --install-plugin path\to\my.ovp`
5. **Manual**: extract to `%LOCALAPPDATA%\OmniView\plugins\<id>\`

## Validation and errors

Before installation OmniView checks:

- the file is a valid zip;
- `plugin.json` exists at the root;
- `id` is valid;
- `formats` is a non-empty array;
- `entry` points to a file inside the archive;
- paths do not contain `..` traversal.

Failures are reported directly, for example:

```text
Not a valid .ovp: plugin.json is missing from the archive root
plugin.json parse failed: Expecting value: line 1 column 1
entry does not exist in the archive: plugin.py
```

## Security

An `.ovp` executes Python code. Only install plugins you trust. 0.3 has no signature or sandbox yet; SHA-256 checks, signing, and permission declarations are future work.
