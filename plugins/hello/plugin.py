"""Example OmniView plugin. Must return a ViewerBase subclass."""
from __future__ import annotations

import os

from PySide6.QtWidgets import QLabel, QVBoxLayout

from omniview.ui.common import ViewerBase


class HelloViewer(ViewerBase):
    def __init__(self, path, parent=None):
        super().__init__(path, parent)
        text = open(path, "r", encoding="utf-8", errors="replace").read()
        label = QLabel(text)
        label.setWordWrap(True)
        label.setStyleSheet("font-size:15pt;color:#e6edf7;padding:32px;")
        self.root.addWidget(label, 1)
        self.info = {"格式": "HELLO", "插件": "hello", "大小": os.path.getsize(path)}


def create_viewer(path, parent=None):
    return HelloViewer(path, parent)
