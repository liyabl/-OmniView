"""OmniView — native Windows all-format viewer (PySide6, CPU only)."""
from __future__ import annotations

import os
import sys

from PySide6.QtCore import Qt, QSettings
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

from omniview import i18n, paths, plugin_manager
from omniview.ui.main_window import MainWindow
from omniview.ui.theme import apply_theme


def main() -> int:
    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
    app = QApplication(sys.argv)
    app.setApplicationName("OmniView")
    app.setOrganizationName("OmniView")
    apply_theme(app)
    icon = paths.bundled("assets", "app.ico")
    if os.path.exists(icon):
        app.setWindowIcon(QIcon(icon))

    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    initial = args[0] if args else None
    if "--install-plugin" in sys.argv:
        try:
            p = sys.argv[sys.argv.index("--install-plugin") + 1]
        except Exception:
            p = ""
        if not p:
            QMessageBox.critical(None, "OmniView", "用法：OmniView.exe --install-plugin path\\to\\plugin.ovp")
            return 2
        try:
            meta = plugin_manager.install_zip(None, p)
            QMessageBox.information(None, "插件已安装",
                                    f"{meta.get('name')} ({meta.get('id')}) 已安装。")
            return 0
        except Exception as e:
            QMessageBox.critical(None, "插件安装失败", str(e))
            return 3
    settings = QSettings("OmniView", "OmniView")
    lang = settings.value("ui/language", "")
    if "--lang" in sys.argv:
        try:
            lang = sys.argv[sys.argv.index("--lang") + 1]
        except Exception:
            pass
    if not lang and "--self-test" not in sys.argv:
        from omniview.ui.language_dialog import LanguageDialog
        chosen = LanguageDialog.ask()
        if not chosen:
            return 0
        lang = chosen
        settings.setValue("ui/language", lang)
    i18n.set_language(lang or "en")
    app.setLayoutDirection(Qt.LayoutDirection.RightToLeft if i18n.rtl() else Qt.LayoutDirection.LeftToRight)
    plugin_manager.preload_installed()

    if "--self-test" in sys.argv:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        tests = [
            "验收文档.pdf", "sample.png", "sample.tiff", "测试音频.mp3", "演示视频.mkv",
            "素材归档.zip", "demo.py", "README.md", "示例数据库.sqlite", "说明.txt",
        ]
        try:
            from omniview import plugin_manager as _pm
            if _pm.installed("office"):
                tests += ["验收文档.docx", "销售数据.xlsx", "产品演示.pptx"]
            if _pm.installed("hello"):
                tests += ["sample.hello"]
        except Exception:
            pass
        base = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
        base = os.path.join(base, "samples")
        win = MainWindow()
        failures = []
        for name in tests:
            p = os.path.join(base, name) if name != "notepad.exe" else r"C:\Windows\System32\notepad.exe"
            if not os.path.exists(p):
                failures.append((name, "missing"))
                continue
            try:
                v = win.create_viewer(p)
                if v is None:
                    failures.append((name, "no viewer"))
                else:
                    v.deleteLater()
            except Exception as e:
                failures.append((name, repr(e)))
        print(f"OmniView self-test: {len(tests) - len(failures)}/{len(tests)} ok")
        try:
            from omniview import archives
            z = os.path.join(base, "素材归档.zip")
            entries = archives.listing(z)["entries"]
            out = archives.extract_entry(z, entries[0]["path"])
            print(f"archive extract: ok ({os.path.getsize(out)} bytes)")
        except Exception as e:
            print("archive extract: FAIL", repr(e))
            failures.append(("archive", repr(e)))
        for f in failures:
            print("FAIL", f)
        return 0 if not failures else 2

    win = MainWindow(initial)
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
