"""Shared native viewer widgets."""
from __future__ import annotations

import os

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                               QToolButton, QFrame, QTreeWidget, QTreeWidgetItem, QSizePolicy)

from .. import paths


class ViewerBase(QWidget):
    """Base class for a native viewer tab."""
    title_changed = Signal(str)
    status_changed = Signal(str)
    open_requested = Signal(str)
    plugin_installed = Signal()

    def __init__(self, path: str, parent=None):
        super().__init__(parent)
        self.path = path
        self.info: dict = {}
        self._dirty = False
        self.root = QVBoxLayout(self)
        self.root.setContentsMargins(0, 0, 0, 0)
        self.root.setSpacing(0)
        self.toolbar = QHBoxLayout()
        self.toolbar.setContentsMargins(10, 6, 10, 6)
        self.toolbar.setSpacing(6)
        self.root.addLayout(self.toolbar)

    def tool_button(self, text: str, slot, tip: str = "", checkable=False) -> QPushButton:
        b = QPushButton(text)
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        b.setToolTip(tip or text)
        b.setCheckable(checkable)
        b.clicked.connect(slot)
        self.toolbar.addWidget(b)
        return b

    def icon_button(self, standard, slot, tip: str = "") -> QToolButton:
        b = QToolButton()
        b.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        b.setIcon(self.style().standardIcon(standard))
        b.setToolTip(tip)
        b.clicked.connect(slot)
        self.toolbar.addWidget(b)
        return b

    def spacer(self):
        w = QWidget()
        w.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.toolbar.addWidget(w)
        return w

    def label(self, text: str = "", name: str = "muted") -> QLabel:
        l = QLabel(text)
        l.setObjectName(name)
        self.toolbar.addWidget(l)
        return l

    def set_status(self, text: str):
        self.status_changed.emit(text)

    def title(self) -> str:
        return os.path.basename(self.path)

    def can_close(self) -> bool:
        return True


def info_tree(info: dict, parent=None) -> QTreeWidget:
    tree = QTreeWidget(parent)
    tree.setHeaderLabels(["项目", "值"])
    tree.setRootIsDecorated(False)
    tree.setAlternatingRowColors(True)
    tree.setColumnWidth(0, 130)
    for k, v in (info or {}).items():
        if isinstance(v, (dict, list)):
            item = QTreeWidgetItem([str(k), ""])
            _fill(item, v)
            tree.addTopLevelItem(item)
            item.setExpanded(True)
        else:
            tree.addTopLevelItem(QTreeWidgetItem([str(k), str(v)]))
    return tree


def _fill(item: QTreeWidgetItem, value):
    if isinstance(value, dict):
        for k, v in value.items():
            ch = QTreeWidgetItem([str(k), "" if isinstance(v, (dict, list)) else str(v)])
            item.addChild(ch)
            if isinstance(v, (dict, list)):
                _fill(ch, v)
    elif isinstance(value, list):
        for i, v in enumerate(value[:200]):
            ch = QTreeWidgetItem([f"[{i}]", "" if isinstance(v, (dict, list)) else str(v)])
            item.addChild(ch)
            if isinstance(v, (dict, list)):
                _fill(ch, v)
