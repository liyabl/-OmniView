"""Placeholder shown when a format needs an on-demand plugin."""
from __future__ import annotations

import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from .. import plugin_manager
from .common import ViewerBase


class MissingPluginViewer(ViewerBase):
    def __init__(self, path: str, pid: str, parent=None):
        super().__init__(path, parent)
        self.pid = pid
        info = plugin_manager.CATALOG.get(pid, {})
        name = info.get("name", pid)
        lay = QVBoxLayout()
        lay.setContentsMargins(52, 44, 52, 44)
        title = QLabel(f"需要插件：{name}")
        title.setStyleSheet("font-size:17pt;font-weight:700;color:#e6edf7;")
        lay.addWidget(title)
        desc = QLabel(info.get("desc", ""))
        desc.setWordWrap(True)
        desc.setStyleSheet("color:#91a4bd;font-size:11pt;")
        lay.addWidget(desc)
        size = QLabel(f"插件大小：{info.get('size', '未知')}  ·  只安装你需要的格式，不把整个程序塞满。")
        size.setStyleSheet("color:#5f738e;font-size:9.5pt;")
        lay.addWidget(size)
        row = QHBoxLayout()
        btn = QPushButton("安装插件")
        btn.setObjectName("primary")
        btn.setFixedHeight(36)
        btn.clicked.connect(self._install)
        row.addWidget(btn)
        btn2 = QPushButton("从 .ovp 文件安装…")
        btn2.setFixedHeight(36)
        btn2.clicked.connect(self._install_file)
        row.addWidget(btn2)
        row.addStretch(1)
        lay.addLayout(row)
        self.msg = QLabel("")
        self.msg.setStyleSheet("color:#fbbf24;font-size:9.5pt;")
        self.msg.setWordWrap(True)
        lay.addWidget(self.msg)
        lay.addStretch(1)
        self.root.addLayout(lay)
        self.info = {"格式": os.path.splitext(path)[1].lstrip(".").upper(),
                     "插件": name, "状态": "未安装"}

    def _install(self):
        dlg = plugin_manager.InstallDialog(self.pid, self)
        if dlg.exec():
            self.msg.setText("插件已安装。正在重新打开此文件…")
            self.msg.setStyleSheet("color:#4ade80;font-size:9.5pt;")
            self.plugin_installed.emit()
        else:
            self.msg.setText("插件未安装；也可以点“从 .ovp 文件安装…”选择本地插件包。")

    def _install_file(self):
        from PySide6.QtWidgets import QMessageBox
        p, _ = QFileDialog.getOpenFileName(self, "选择 .ovp 插件包", "", "OmniView 插件 (*.ovp);;所有文件 (*.*)")
        if not p:
            return
        try:
            meta = plugin_manager.install_zip(self.pid, p)
            self.msg.setText(f"插件 {meta.get('name', self.pid)} 已安装。正在重新打开此文件…")
            self.msg.setStyleSheet("color:#4ade80;font-size:9.5pt;")
            self.plugin_installed.emit()
        except Exception as e:
            QMessageBox.critical(self, "插件安装失败", str(e))
            self.msg.setText("安装失败：" + str(e))
            self.msg.setStyleSheet("color:#f87171;font-size:9.5pt;")
