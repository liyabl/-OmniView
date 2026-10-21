"""Visible parse-failure page (never a silent failure)."""
from __future__ import annotations

import os
import traceback

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QLabel, QPlainTextEdit, QPushButton,
                               QVBoxLayout)

from .common import ViewerBase


class ErrorViewer(ViewerBase):
    def __init__(self, path: str, error: BaseException | str, plugin_id: str = "", parent=None):
        super().__init__(path, parent)
        self.error_text = str(error)
        if isinstance(error, BaseException):
            self.error_text = "".join(traceback.format_exception(type(error), error, error.__traceback__))
        self.plugin_id = plugin_id
        lay = QVBoxLayout()
        lay.setContentsMargins(44, 36, 44, 26)
        title = QLabel("无法解析此文件")
        title.setStyleSheet("font-size:18pt;font-weight:700;color:#f87171;")
        lay.addWidget(title)
        sub = QLabel(os.path.basename(path))
        sub.setStyleSheet("color:#e6edf7;font-size:11pt;font-weight:600;")
        lay.addWidget(sub)
        hint = QLabel("下面是完整错误信息。不是静默失败，也不会把异常吞掉。")
        hint.setStyleSheet("color:#91a4bd;font-size:9.5pt;")
        lay.addWidget(hint)
        self.detail = QPlainTextEdit(self.error_text)
        self.detail.setReadOnly(True)
        self.detail.setStyleSheet("QPlainTextEdit{background:#0f172a;color:#fecaca;border:1px solid #7f1d1d;"
                                  "font-family:'Cascadia Mono','Consolas';font-size:9.5pt;padding:12px;}")
        lay.addWidget(self.detail, 1)
        row = QHBoxLayout()
        b = QPushButton("复制错误")
        b.clicked.connect(lambda: QApplication.clipboard().setText(self.error_text))
        row.addWidget(b)
        b = QPushButton("插件管理…")
        b.clicked.connect(self._plugins)
        row.addWidget(b)
        b = QPushButton("打开文件位置")
        b.clicked.connect(lambda: os.startfile(os.path.dirname(path)))
        row.addWidget(b)
        row.addStretch(1)
        lay.addLayout(row)
        self.root.addLayout(lay)
        self.info = {"格式": os.path.splitext(path)[1].lstrip(".").upper(),
                     "插件": plugin_id or "无", "状态": "解析失败",
                     "错误": self.error_text.splitlines()[0][:200] if self.error_text else "未知错误"}

    def _plugins(self):
        from .plugin_manager_dialog import PluginManagerDialog
        PluginManagerDialog(self).exec()
