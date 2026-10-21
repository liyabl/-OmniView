"""Plugin manager UI: install .ovp files, URLs, remove, developer info."""
from __future__ import annotations

import os
import tempfile
import urllib.request

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget,
                               QTableWidgetItem, QFileDialog, QInputDialog, QMessageBox, QHeaderView,
                               QApplication)

from .. import plugin_manager, paths


class PluginManagerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("OmniView · 插件管理")
        self.resize(820, 540)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 16, 18, 14)
        title = QLabel("插件管理")
        title.setStyleSheet("font-size:15pt;font-weight:700;color:#e6edf7;")
        lay.addWidget(title)
        sub = QLabel("安装 `.ovp`、从 URL 安装、移除插件，或查看如何制作自己的插件。"
                     "解析失败时会在标签页里直接显示错误，不会静默退出。")
        sub.setWordWrap(True)
        sub.setStyleSheet("color:#91a4bd;font-size:9.5pt;")
        lay.addWidget(sub)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["插件", "ID", "格式", "状态", "版本"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        lay.addWidget(self.table, 1)
        row = QHBoxLayout()
        for text, slot in [
            ("安装 .ovp…", self.install_file),
            ("从 URL 安装…", self.install_url),
            ("移除", self.remove_selected),
            ("打开插件目录", lambda: os.startfile(plugin_manager.plugin_root())),
            ("制作 OVP…", self.developer_info),
        ]:
            b = QPushButton(text)
            b.clicked.connect(slot)
            row.addWidget(b)
        row.addStretch(1)
        close = QPushButton("关闭")
        close.clicked.connect(self.accept)
        row.addWidget(close)
        lay.addLayout(row)
        self.refresh()

    def refresh(self):
        ids = list(plugin_manager.CATALOG.keys())
        for pid in plugin_manager.installed_ids():
            if pid not in ids:
                ids.append(pid)
        self.table.setRowCount(0)
        for pid in ids:
            e = plugin_manager.catalog_entry(pid)
            r = self.table.rowCount()
            self.table.insertRow(r)
            formats = ", ".join(sorted(e.get("formats") or []))
            if len(formats) > 90:
                formats = formats[:87] + "…"
            vals = [e["name"], pid, formats, "已安装" if e["installed"] else "未安装", e.get("version", "")]
            for c, v in enumerate(vals):
                item = QTableWidgetItem(str(v))
                item.setData(Qt.ItemDataRole.UserRole, pid)
                self.table.setItem(r, c, item)
        self.table.resizeRowsToContents()

    def selected_pid(self):
        r = self.table.currentRow()
        if r < 0:
            return None
        item = self.table.item(r, 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def install_file(self):
        p, _ = QFileDialog.getOpenFileName(self, "选择插件包", "", "OmniView 插件 (*.ovp);;所有文件 (*.*)")
        if not p:
            return
        try:
            meta = plugin_manager.install_zip(None, p)
            QMessageBox.information(self, "插件已安装",
                                    f"{meta.get('name')} ({meta.get('id')}) 已安装。\n"
                                    "如果当前标签页仍提示缺插件，请按“刷新”。")
        except Exception as e:
            QMessageBox.critical(self, "插件安装失败", str(e))
        self.refresh()

    def install_url(self):
        url, ok = QInputDialog.getText(self, "从 URL 安装插件", "插件 .ovp 的下载地址：")
        if not ok or not url.strip():
            return
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        tmp = None
        try:
            fd, tmp = tempfile.mkstemp(suffix=".ovp")
            os.close(fd)
            urllib.request.urlretrieve(url.strip(), tmp)
            meta = plugin_manager.install_zip(None, tmp)
            QMessageBox.information(self, "插件已安装", f"{meta.get('name')} ({meta.get('id')}) 已安装。")
        except Exception as e:
            QMessageBox.critical(self, "插件安装失败", str(e))
        finally:
            QApplication.restoreOverrideCursor()
            if tmp:
                try:
                    os.remove(tmp)
                except Exception:
                    pass
        self.refresh()

    def remove_selected(self):
        pid = self.selected_pid()
        if not pid:
            return
        if pid in plugin_manager.CATALOG:
            QMessageBox.information(self, "内置插件", "内置插件的目录由构建脚本管理，请在插件目录中手动处理。")
            return
        if QMessageBox.question(self, "移除插件", f"确定移除插件 {pid}？") != QMessageBox.StandardButton.Yes:
            return
        plugin_manager.remove(pid)
        self.refresh()

    def developer_info(self):
        doc = paths.bundled("docs", "PLUGIN_FORMAT.md")
        if not os.path.exists(doc):
            doc = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "docs", "PLUGIN_FORMAT.md")
        QMessageBox.information(
            self, "制作自己的 OVP",
            "一个 .ovp 就是 zip：\n\n"
            "plugin.json\n"
            "plugin.py          # 可选，自定义查看器\n"
            "site-packages/     # 可选，依赖\n\n"
            "plugin.json 示例：\n"
            '{"id":"hello","name":"Hello","version":"1.0","formats":["hello"],'
            '"entry":"plugin.py","factory":"create_viewer"}\n\n'
            "plugin.py 里实现：\n"
            "def create_viewer(path, parent=None):\n"
            "    ... 返回 QWidget/ViewerBase ...\n\n"
            f"完整文档：\n{doc}\n\n"
            "仓库里还有 build_ovp.py 和 plugins/template/ 模板。")
        if os.path.exists(doc):
            os.startfile(doc)
