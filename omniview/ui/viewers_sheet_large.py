"""Memory-bounded viewer for very large XLSX workbooks."""
from __future__ import annotations

import os

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (QComboBox, QHBoxLayout, QLabel, QLineEdit, QPushButton,
                               QTableWidget, QTableWidgetItem, QAbstractItemView, QHeaderView)

from .. import paths, xlsx_stream
from .common import ViewerBase


def _col_name(n: int) -> str:
    s = ""
    while n > 0:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


class _IndexWorker(QThread):
    progress = Signal(int)
    ready = Signal(str)
    failed = Signal(str)

    def __init__(self, path, shared_target, db_path):
        super().__init__()
        self.path = path
        self.shared_target = shared_target
        self.db_path = db_path

    def run(self):
        try:
            xlsx_stream.build_shared_index(
                self.path, self.shared_target, self.db_path,
                progress=lambda n, _total: self.progress.emit(n),
                stop=self.isInterruptionRequested,
            )
            self.ready.emit(self.db_path)
        except InterruptedError:
            self.failed.emit("索引已取消")
        except Exception as e:
            self.failed.emit(str(e))


class _ChunkWorker(QThread):
    ready = Signal(dict)
    failed = Signal(str)

    def __init__(self, path, target, start, shared_db):
        super().__init__()
        self.path = path
        self.target = target
        self.start_row = start
        self.shared_db = shared_db

    def run(self):
        try:
            data = xlsx_stream.read_chunk(
                self.path, self.target, start_row=self.start_row,
                rows=300, max_cols=128, shared_db=self.shared_db,
                stop=self.isInterruptionRequested,
            )
            self.ready.emit(data)
        except InterruptedError:
            pass
        except Exception as e:
            self.failed.emit(str(e))


class LargeSheetViewer(ViewerBase):
    """A row-window viewer; never loads the full workbook."""

    CHUNK = 300
    MAX_COLS = 128

    def __init__(self, path: str, parent=None):
        super().__init__(path, parent)
        self.meta = xlsx_stream.read_workbook(path)
        sheets = self.meta.get("sheets") or []
        if not sheets:
            raise RuntimeError("工作簿里没有工作表")
        self.sheet_index = self.meta.get("active", 0)
        self.shared_db = xlsx_stream.shared_cache_path(path)
        self.start = 1
        self.total_rows, self.total_cols = xlsx_stream.dimension(path, sheets[self.sheet_index]["target"])
        self._index_worker = None
        self._chunk_worker = None
        self._busy = False

        self.sheet_box = QComboBox()
        for s in sheets:
            self.sheet_box.addItem(s["name"])
        self.sheet_box.setCurrentIndex(self.sheet_index)
        self.sheet_box.currentIndexChanged.connect(self._sheet_changed)
        self.toolbar.addWidget(self.sheet_box)
        self.prev = self.tool_button("上一块", lambda: self._move(-1))
        self.next = self.tool_button("下一块", lambda: self._move(1))
        self.row_edit = QLineEdit()
        self.row_edit.setPlaceholderText("跳到行")
        self.row_edit.setFixedWidth(90)
        self.toolbar.addWidget(self.row_edit)
        self.tool_button("跳转", self._jump)
        self.spacer()
        self.mode_label = self.label("大表格流式模式 · 值视图", "muted")

        self.table = QTableWidget(0, 0)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setDefaultSectionSize(96)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setDefaultSectionSize(24)
        self.root.addWidget(self.table, 1)
        self.info = {"格式": "XLSX (streaming)", "工作表": len(sheets),
                     "大小": paths.human_size(os.path.getsize(path)),
                     "模式": "按行窗口 · sharedStrings SQLite 索引"}
        self._start_index()

    def _start_index(self):
        shared = self.meta.get("shared")
        if shared and not os.path.exists(self.shared_db):
            self._busy = True
            self._set_buttons(False)
            self.set_status("正在建立 sharedStrings 磁盘索引…")
            w = _IndexWorker(self.path, shared, self.shared_db)
            w.progress.connect(lambda n: self.set_status(f"正在建立 sharedStrings 索引… {n:,} 条"))
            w.ready.connect(self._index_ready)
            w.failed.connect(self._failed)
            w.finished.connect(w.deleteLater)
            self._index_worker = w
            w.start()
        else:
            self._load(1)

    def _index_ready(self, db_path):
        self._busy = False
        self._set_buttons(True)
        self.set_status("索引完成，正在读取第一块…")
        self._load(1)

    def _set_buttons(self, enabled):
        self.sheet_box.setEnabled(enabled)
        self.prev.setEnabled(enabled)
        self.next.setEnabled(enabled)
        self.row_edit.setEnabled(enabled)

    def _sheet_changed(self, idx):
        if idx < 0 or idx >= len(self.meta["sheets"]):
            return
        self.sheet_index = idx
        self.start = 1
        self.total_rows, self.total_cols = xlsx_stream.dimension(self.path, self.meta["sheets"][idx]["target"])
        self._load(1)

    def _load(self, start):
        if self._busy:
            return
        self._busy = True
        self._set_buttons(False)
        self.start = max(1, int(start))
        self.set_status(f"正在读取第 {self.start:,} 行附近…")
        target = self.meta["sheets"][self.sheet_index]["target"]
        w = _ChunkWorker(self.path, target, self.start, self.shared_db)
        w.ready.connect(self._chunk_ready)
        w.failed.connect(self._failed)
        w.finished.connect(w.deleteLater)
        self._chunk_worker = w
        w.start()

    def _chunk_ready(self, d):
        self._busy = False
        self._set_buttons(True)
        rows = d.get("rows") or []
        cols = max(1, min(self.MAX_COLS, max(d.get("cols") or 0, self.total_cols or 0, 1)))
        self.table.setRowCount(len(rows))
        self.table.setColumnCount(cols)
        self.table.setHorizontalHeaderLabels([_col_name(i + 1) for i in range(cols)])
        self.table.setVerticalHeaderLabels([str(r["n"]) for r in rows])
        for ri, r in enumerate(rows):
            vals = r.get("cells") or []
            for ci in range(cols):
                text = str(vals[ci]) if ci < len(vals) else ""
                item = QTableWidgetItem(text)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(ri, ci, item)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        if rows:
            last = rows[-1]["n"]
            self.set_status(
                f"大表格流式模式 · 第 {rows[0]['n']:,}–{last:,} 行"
                + (f" / 约 {self.total_rows:,} 行" if self.total_rows else "")
                + f" · {cols} 列 · 当前窗口 {len(rows)} 行"
            )
        else:
            self.set_status("没有更多行了")

    def _move(self, delta):
        if self._busy:
            return
        self._load(max(1, self.start + delta * self.CHUNK))

    def _jump(self):
        try:
            n = int(self.row_edit.text().replace(",", "").strip())
        except Exception:
            self.set_status("请输入行号")
            return
        self._load(n)

    def _failed(self, msg):
        self._busy = False
        self._set_buttons(True)
        self.set_status("大表格读取失败：" + msg)

    def closeEvent(self, event):
        for w in (self._index_worker, self._chunk_worker):
            try:
                if w is not None and w.isRunning():
                    w.requestInterruption()
                    w.wait(1500)
            except RuntimeError:
                pass
        super().closeEvent(event)

