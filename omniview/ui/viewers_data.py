"""Native archive, database, model, 3D, CAD, GIS, font, binary and mail viewers."""
from __future__ import annotations

import html
import math
import os
import numpy as np

from PySide6.QtCore import Qt, QPointF, QRectF, QSize, Signal
from PySide6.QtGui import (QColor, QFont, QFontDatabase, QImage, QPainter, QPainterPath, QPen,
                           QPolygonF, QBrush, QLinearGradient)
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
                               QTableWidget, QTableWidgetItem, QTabWidget, QTreeWidget, QTreeWidgetItem,
                               QListWidget, QSplitter, QTextBrowser, QPlainTextEdit, QFileDialog,
                               QMessageBox, QAbstractItemView, QHeaderView, QScrollArea, QFrame)

from .. import archives, binary, data, geo, mesh, office, paths, textutil
from .common import ViewerBase, info_tree


class ArchiveViewer(ViewerBase):
    def __init__(self, path: str, parent=None):
        super().__init__(path, parent)
        self.entries = []
        self.filter = QLineEdit()
        self.filter.setPlaceholderText("筛选文件名…")
        self.filter.setMaximumWidth(260)
        self.filter.textChanged.connect(self._fill)
        self.toolbar.addWidget(self.filter)
        self.spacer()
        self.label("双击条目预览", "muted")
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["名称", "大小", "压缩后", "修改时间"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.cellDoubleClicked.connect(self._open)
        self.root.addWidget(self.table, 1)
        self.load()

    def load(self):
        try:
            d = archives.listing(self.path)
            self.entries = d["entries"]
            self._fill()
            self.set_status(f"{d['format']} · {d['files']} 个文件 · {paths.human_size(d['total'])}")
        except Exception as e:
            self.table.setRowCount(1)
            self.table.setItem(0, 0, QTableWidgetItem(f"无法打开：{e}"))
            self.table.setSpan(0, 0, 1, 4)

    def _fill(self):
        q = self.filter.text().lower()
        items = [e for e in self.entries if q in e["path"].lower()]
        self.table.setRowCount(len(items))
        for i, e in enumerate(items):
            self.table.setItem(i, 0, QTableWidgetItem(("📁 " if e["dir"] else "") + e["path"]))
            self.table.setItem(i, 1, QTableWidgetItem("—" if e["dir"] else paths.human_size(e["size"])))
            self.table.setItem(i, 2, QTableWidgetItem("—" if e["dir"] else paths.human_size(e["packed"])))
            self.table.setItem(i, 3, QTableWidgetItem(e.get("mtime", "")))
            self.table.item(i, 0).setData(Qt.ItemDataRole.UserRole, e)
        self.table.resizeRowsToContents()

    def _open(self, row, col):
        item = self.table.item(row, 0)
        if not item:
            return
        e = item.data(Qt.ItemDataRole.UserRole)
        if not e or e.get("dir"):
            return
        try:
            self.set_status("正在解包…")
            out = archives.extract_entry(self.path, e["path"])
            self.open_requested.emit(out)
            self.set_status(f"已解包：{os.path.basename(out)}")
        except Exception as ex:
            QMessageBox.warning(self, "解包失败", str(ex))


class DatabaseViewer(ViewerBase):
    def __init__(self, path: str, parent=None):
        super().__init__(path, parent)
        self.kind = os.path.splitext(path)[1].lower().lstrip(".")
        self.tables = []
        self.split = QSplitter(Qt.Orientation.Horizontal)
        self.list = QListWidget()
        self.list.setMaximumWidth(250)
        self.grid = QTableWidget()
        self.grid.setAlternatingRowColors(True)
        self.grid.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.split.addWidget(self.list)
        self.split.addWidget(self.grid)
        self.split.setSizes([230, 900])
        self.root.addWidget(self.split, 1)
        self.list.currentRowChanged.connect(self._load_table)
        self.load()

    def load(self):
        try:
            if self.kind in ("db", "sqlite", "sqlite3"):
                d = data.sqlite_info(self.path)
            elif self.kind == "dbf":
                d = data.dbf_info(self.path)
            elif self.kind in ("mdb", "accdb"):
                d = data.access_info(self.path)
            else:
                d = {"tables": []}
            self.tables = d.get("tables", [])
            self.list.clear()
            for t in self.tables:
                self.list.addItem(f"{t['name']}  ({t.get('rows', '?')})")
            if self.tables:
                self.list.setCurrentRow(0)
            self.set_status(f"{self.kind.upper()} · {len(self.tables)} 张表")
        except Exception as e:
            self.grid.setRowCount(1); self.grid.setColumnCount(1)
            self.grid.setItem(0, 0, QTableWidgetItem(f"无法读取：{e}"))

    def _load_table(self, row):
        if row < 0 or row >= len(self.tables):
            return
        name = self.tables[row]["name"]
        try:
            if self.kind in ("db", "sqlite", "sqlite3"):
                d = data.sqlite_rows(self.path, name, limit=500)
            elif self.kind == "dbf":
                d = data.dbf_rows(self.path, limit=500)
            else:
                d = data.access_rows(self.path, name, limit=300)
            self._fill(d)
            self.set_status(f"{name} · {d.get('total', len(d['rows']))} 行")
        except Exception as e:
            self.grid.setRowCount(1); self.grid.setColumnCount(1)
            self.grid.setItem(0, 0, QTableWidgetItem(f"读取失败：{e}"))

    def _fill(self, d):
        cols, rows = d["columns"], d["rows"]
        self.grid.clear()
        self.grid.setColumnCount(len(cols))
        self.grid.setRowCount(len(rows))
        self.grid.setHorizontalHeaderLabels(cols)
        for r, row in enumerate(rows):
            for c, v in enumerate(row):
                self.grid.setItem(r, c, QTableWidgetItem("" if v is None else str(v)))
        self.grid.resizeColumnsToContents()


class Hdf5Viewer(ViewerBase):
    def __init__(self, path: str, parent=None):
        super().__init__(path, parent)
        self.split = QSplitter(Qt.Orientation.Horizontal)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["节点", "类型", "形状"])
        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        self.split.addWidget(self.tree)
        self.split.addWidget(self.table)
        self.split.setSizes([320, 850])
        self.root.addWidget(self.split, 1)
        self.tree.itemClicked.connect(self._node)
        self.load()

    def load(self):
        try:
            d = data.hdf5_info(self.path)
            for n in d["nodes"]:
                it = QTreeWidgetItem([n["name"], n["type"], " × ".join(map(str, n.get("shape", [])))])
                it.setData(0, Qt.ItemDataRole.UserRole, n["name"])
                self.tree.addTopLevelItem(it)
            self.set_status(f"HDF5 · {len(d['nodes'])} 个节点")
        except Exception as e:
            self.tree.addTopLevelItem(QTreeWidgetItem([f"无法读取：{e}"]))

    def _node(self, item, col):
        name = item.data(0, Qt.ItemDataRole.UserRole)
        if not name:
            return
        try:
            d = data.hdf5_values(self.path, name)
            vals = d["values"]
            self.table.clear()
            self.table.setColumnCount(2)
            self.table.setRowCount(len(vals))
            self.table.setHorizontalHeaderLabels(["#", "值"])
            for i, v in enumerate(vals):
                self.table.setItem(i, 0, QTableWidgetItem(str(i)))
                self.table.setItem(i, 1, QTableWidgetItem(str(v)))
            self.set_status(f"{name} · {d['dtype']} · {d['total']} 个值")
        except Exception as e:
            self.set_status(f"读取失败：{e}")


class ModelViewer(ViewerBase):
    def __init__(self, path: str, parent=None):
        super().__init__(path, parent)
        self.kind = os.path.splitext(path)[1].lower().lstrip(".")
        self.tabs = QTabWidget()
        self.root.addWidget(self.tabs, 1)
        self.load()

    def load(self):
        try:
            if self.kind == "onnx":
                d = data.onnx_info(self.path)
                info = QWidget(); lay = QVBoxLayout(info)
                lay.addWidget(QLabel(f"ONNX · {d.get('graph','')} · IR {d.get('ir_version','')}"))
                t = QTableWidget(len(d["nodes"]), 4)
                t.setHorizontalHeaderLabels(["#", "算子", "名称", "层"])
                for i, n in enumerate(d["nodes"]):
                    for j, v in enumerate([n["id"], n["op"], n["name"], n["layer"]]):
                        t.setItem(i, j, QTableWidgetItem(str(v)))
                lay.addWidget(t, 1)
                self.tabs.addTab(info, "节点")
                ops = QTableWidget(len(d["op_hist"]), 2)
                ops.setHorizontalHeaderLabels(["算子", "数量"])
                for i, (k, v) in enumerate(d["op_hist"].items()):
                    ops.setItem(i, 0, QTableWidgetItem(k)); ops.setItem(i, 1, QTableWidgetItem(str(v)))
                self.tabs.addTab(ops, "算子")
                self.set_status(f"ONNX · {len(d['nodes'])} 节点 · {d['initializers']} 权重")
            elif self.kind in ("pt", "pth"):
                d = data.torch_info(self.path)
                t = QTableWidget(len(d["entries"]), 2)
                t.setHorizontalHeaderLabels(["归档条目", "大小"])
                for i, e in enumerate(d["entries"]):
                    t.setItem(i, 0, QTableWidgetItem(e["name"])); t.setItem(i, 1, QTableWidgetItem(paths.human_size(e["size"])))
                self.tabs.addTab(t, "权重条目")
                self._strings_tab(d.get("strings", []))
                self.set_status(f"PyTorch 权重 · {len(d['entries'])} 个归档条目")
            elif self.kind in ("pkl", "pickle"):
                d = data.pickle_info(self.path)
                t = QTableWidget(len(d["ops"]), 2)
                t.setHorizontalHeaderLabels(["指令", "参数"])
                for i, (n, a) in enumerate(d["ops"]):
                    t.setItem(i, 0, QTableWidgetItem(n)); t.setItem(i, 1, QTableWidgetItem(a))
                self.tabs.addTab(t, "字节码")
                self._strings_tab(d.get("strings", []))
                self.set_status("Pickle · 只反汇编，不执行")
            elif self.kind == "tflite":
                d = data.tflite_info(self.path)
                t = QTableWidget(len(d["tensors"]), 3)
                t.setHorizontalHeaderLabels(["张量", "形状", "类型"])
                for i, x in enumerate(d["tensors"]):
                    t.setItem(i, 0, QTableWidgetItem(x["name"])); t.setItem(i, 1, QTableWidgetItem(" × ".join(map(str, x["shape"]))))
                self.tabs.addTab(t, "张量")
                self.set_status(f"TFLite · {len(d['tensors'])} 张量 · {len(d['operators'])} 算子")
            elif self.kind == "pb":
                d = data.protobuf_info(self.path)
                t = QTableWidget(len(d["fields"]), 3)
                t.setHorizontalHeaderLabels(["字段", "wire", "值"])
                for i, f in enumerate(d["fields"]):
                    t.setItem(i, 0, QTableWidgetItem(str(f["field"])))
                    t.setItem(i, 1, QTableWidgetItem(str(f["wire"])))
                    t.setItem(i, 2, QTableWidgetItem(str(f.get("value", ""))))
                self.tabs.addTab(t, "字段")
                self.set_status("Protobuf · 通用 wire 解析")
        except Exception as e:
            self.tabs.addTab(QLabel(f"解析失败：{e}"), "错误")

    def _strings_tab(self, strings):
        w = QPlainTextEdit(); w.setReadOnly(True); w.setPlainText("\n".join(strings))
        self.tabs.addTab(w, "字符串")


class MailViewer(ViewerBase):
    def __init__(self, path: str, parent=None):
        super().__init__(path, parent)
        self.kind = os.path.splitext(path)[1].lower().lstrip(".")
        self.split = QSplitter(Qt.Orientation.Horizontal)
        self.list = QListWidget()
        self.list.setMaximumWidth(300)
        self.browser = QTextBrowser()
        self.browser.setObjectName("docView")
        self.split.addWidget(self.list)
        self.split.addWidget(self.browser)
        self.split.setSizes([280, 900])
        self.root.addWidget(self.split, 1)
        self.list.currentRowChanged.connect(self._open)
        self.messages = []
        self.load()

    def load(self):
        try:
            if self.kind in ("mbox", "mbx"):
                d = data.mbox_list(self.path)
                self.messages = d["messages"]
                self.list.clear()
                for m in self.messages:
                    self.list.addItem(f"{m['subject']}\n{m['from']}")
                if self.messages:
                    self.list.setCurrentRow(0)
                self.set_status(f"MBOX · {len(self.messages)} 封邮件")
            else:
                d = data.email_info(self.path)
                self.browser.setHtml(d["html"])
                self.set_status(f"{self.kind.upper()} · {d.get('subject','')}")
                self._attachments = d.get("attachments", [])
        except Exception as e:
            self.browser.setHtml(f"<h3>无法读取邮件</h3><pre>{html.escape(str(e))}</pre>")

    def _open(self, row):
        if row < 0 or row >= len(self.messages):
            return
        try:
            d = data.mbox_message(self.path, self.messages[row]["index"])
            self.browser.setHtml(d["html"])
        except Exception as e:
            self.browser.setHtml(f"<pre>{html.escape(str(e))}</pre>")


class MeshCanvas(QWidget):
    def __init__(self, data: dict, parent=None):
        super().__init__(parent)
        self.data = data
        self.rot_x = -0.35
        self.rot_y = 0.65
        self.zoom = 1.0
        self.last = None
        self.setMinimumSize(480, 360)
        self.setMouseTracking(True)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        g = QLinearGradient(0, 0, 0, self.height())
        g.setColorAt(0, QColor("#0d1526")); g.setColorAt(1, QColor("#05080f"))
        p.fillRect(self.rect(), g)
        v = self.data.get("vertices")
        f = self.data.get("faces")
        if v is None or len(v) == 0 or f is None or len(f) == 0:
            p.setPen(QColor("#91a4bd")); p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.data.get("error", "没有可显示的网格"))
            return
        cx, cy, cz = self.data["center"]
        size = max(float(self.data["size"][0]), float(self.data["size"][1]), float(self.data["size"][2]), 0.001)
        scale = min(self.width(), self.height()) * 0.8 / size * self.zoom
        cosx, sinx = math.cos(self.rot_x), math.sin(self.rot_x)
        cosy, siny = math.cos(self.rot_y), math.sin(self.rot_y)
        pts = v - np.array([cx, cy, cz], dtype=np.float32)
        x1 = pts[:, 0] * cosy + pts[:, 2] * siny
        z1 = -pts[:, 0] * siny + pts[:, 2] * cosy
        y1 = pts[:, 1] * cosx - z1 * sinx
        z2 = pts[:, 1] * sinx + z1 * cosx
        sx = self.width() / 2 + x1 * scale
        sy = self.height() / 2 - y1 * scale
        order = np.argsort(z2[f].mean(axis=1))
        light = np.array([0.4, 0.8, 0.5], dtype=np.float32)
        light = light / np.linalg.norm(light)
        for fi in order:
            tri = f[fi]
            try:
                a, b, c = v[tri[0]], v[tri[1]], v[tri[2]]
                n = np.cross(b - a, c - a)
                ln = np.linalg.norm(n)
                if ln == 0:
                    continue
                n = n / ln
                shade = 0.25 + 0.75 * abs(float(np.dot(n, light)))
                col = QColor(int(90 * shade + 30), int(130 * shade + 30), int(190 * shade + 30))
                poly = QPolygonF([QPointF(float(sx[tri[0]]), float(sy[tri[0]])),
                                  QPointF(float(sx[tri[1]]), float(sy[tri[1]])),
                                  QPointF(float(sx[tri[2]]), float(sy[tri[2]]))])
                p.setBrush(QBrush(col))
                p.setPen(QPen(QColor(10, 18, 32, 80), 0.5))
                p.drawPolygon(poly)
            except Exception:
                continue
        p.setPen(QColor("#5f738e"))
        p.drawText(12, self.height() - 12, f"{len(f):,} 三角面 · {len(v):,} 顶点 · 拖动旋转 · 滚轮缩放")

    def mousePressEvent(self, e):
        self.last = e.position()

    def mouseMoveEvent(self, e):
        if self.last is not None and e.buttons() & Qt.MouseButton.LeftButton:
            d = e.position() - self.last
            self.rot_y += d.x() * 0.008
            self.rot_x += d.y() * 0.008
            self.last = e.position()
            self.update()

    def mouseReleaseEvent(self, e):
        self.last = None

    def wheelEvent(self, e):
        self.zoom = max(0.1, min(8.0, self.zoom * (1.12 if e.angleDelta().y() > 0 else 0.89)))
        self.update()


class MeshViewer(ViewerBase):
    def __init__(self, path: str, parent=None):
        super().__init__(path, parent)
        self.data = mesh.load_mesh(path)
        self.canvas = MeshCanvas(self.data)
        self.root.addWidget(self.canvas, 1)
        self.tool_button("重置视角", self.reset)
        self.spacer()
        if self.data.get("error"):
            self.label(self.data["error"], "muted")
        self.set_status(f"{len(self.data.get('faces', [])):,} 三角面 · {paths.human_size(os.path.getsize(path))}")

    def reset(self):
        self.canvas.rot_x, self.canvas.rot_y, self.canvas.zoom = -0.35, 0.65, 1.0
        self.canvas.update()


class CadCanvas(QWidget):
    def __init__(self, info: dict, parent=None):
        super().__init__(parent)
        self.info = info
        self.zoom = 1.0
        self.pan = QPointF(0, 0)
        self.last = None
        self.bounds = self._bounds()
        self.setMinimumSize(480, 360)
        self.setMouseTracking(True)

    def _bounds(self):
        xs, ys = [], []
        for e in self.info.get("entities", []):
            if e["type"] == "line":
                xs += [e["a"][0], e["b"][0]]; ys += [e["a"][1], e["b"][1]]
            elif e["type"] in ("circle", "arc"):
                xs += [e["c"][0] - e["r"], e["c"][0] + e["r"]]; ys += [e["c"][1] - e["r"], e["c"][1] + e["r"]]
            elif e["type"] == "poly":
                xs += [p[0] for p in e["pts"]]; ys += [p[1] for p in e["pts"]]
            elif e["type"] == "text":
                xs.append(e["p"][0]); ys.append(e["p"][1])
        if not xs:
            return QRectF(-10, -10, 20, 20)
        return QRectF(min(xs), min(ys), max(1, max(xs) - min(xs)), max(1, max(ys) - min(ys)))

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor("#070c16"))
        b = self.bounds
        s = min(self.width() / b.width(), self.height() / b.height()) * 0.86 * self.zoom
        ox = self.width() / 2 - (b.center().x()) * s + self.pan.x()
        oy = self.height() / 2 + (b.center().y()) * s + self.pan.y()

        def T(x, y):
            return QPointF(x * s + ox, -y * s + oy)

        p.setPen(QPen(QColor("#24344f"), 1))
        for i in range(0, 11):
            x = b.left() + b.width() * i / 10
            p.drawLine(T(x, b.top()), T(x, b.bottom()))
            y = b.top() + b.height() * i / 10
            p.drawLine(T(b.left(), y), T(b.right(), y))
        for e in self.info.get("entities", []):
            p.setPen(QPen(QColor("#e2e8f0"), 1.2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            try:
                if e["type"] == "line":
                    p.drawLine(T(*e["a"]), T(*e["b"]))
                elif e["type"] == "circle":
                    c = T(*e["c"]); r = e["r"] * s
                    p.drawEllipse(c, r, r)
                elif e["type"] == "arc":
                    c = T(*e["c"]); r = e["r"] * s
                    rect = QRectF(c.x() - r, c.y() - r, 2 * r, 2 * r)
                    p.drawArc(rect, int(e["start"] * 16), int((e["end"] - e["start"]) * 16))
                elif e["type"] == "poly":
                    poly = QPolygonF([T(*pt) for pt in e["pts"]])
                    p.drawPolyline(poly)
                elif e["type"] == "text":
                    pt = T(*e["p"])
                    f = QFont("Microsoft YaHei", max(6, int(e.get("h", 3) * s * 0.7)))
                    p.setFont(f); p.setPen(QColor("#7aa2ff"))
                    p.save(); p.translate(pt); p.rotate(-e.get("rot", 0)); p.drawText(QPointF(0, 0), e.get("text", "")); p.restore()
            except Exception:
                continue
        p.setPen(QColor("#5f738e"))
        p.drawText(12, self.height() - 12, f"{self.info.get('version','DXF')} · {len(self.info.get('entities', []))} 个实体 · 滚轮缩放 · 拖动平移")

    def mousePressEvent(self, e):
        self.last = e.position()

    def mouseMoveEvent(self, e):
        if self.last is not None and e.buttons() & Qt.MouseButton.LeftButton:
            d = e.position() - self.last
            self.pan += d
            self.last = e.position()
            self.update()

    def mouseReleaseEvent(self, e):
        self.last = None

    def wheelEvent(self, e):
        self.zoom = max(0.1, min(20, self.zoom * (1.15 if e.angleDelta().y() > 0 else 0.87)))
        self.update()


class CadViewer(ViewerBase):
    def __init__(self, path: str, parent=None):
        super().__init__(path, parent)
        ext = os.path.splitext(path)[1].lower().lstrip(".")
        if ext == "dwg":
            self.info = binary.dwg_info(path)
            self.canvas = None
            self.root.addWidget(self._dwg_widget(), 1)
            self.set_status("DWG · 结构只读")
        else:
            self.info = binary.dxf_info(path)
            self.canvas = CadCanvas(self.info)
            self.root.addWidget(self.canvas, 1)
            self.tool_button("重置", self.reset)
            self.spacer()
            self.label(f"{len(self.info.get('entities', []))} 个实体", "muted")
            self.set_status(f"DXF · {len(self.info.get('entities', []))} 个实体 · {self.info.get('version','')}")

    def _dwg_widget(self):
        w = QWidget(); lay = QVBoxLayout(w)
        lbl = QLabel("DWG 是 AutoCAD 私有格式。\n本程序不依赖 AutoCAD，因此这里展示文件结构；DXF 可完整渲染。")
        lbl.setWordWrap(True)
        lbl.setStyleSheet("color:#fcd34d;padding:20px;font-size:12pt;")
        lay.addWidget(lbl)
        lay.addWidget(info_tree({k: v for k, v in self.info.items() if k not in ("header", "strings")}), 1)
        return w

    def reset(self):
        if self.canvas:
            self.canvas.zoom = 1.0; self.canvas.pan = QPointF(0, 0); self.canvas.update()


class GeoCanvas(QWidget):
    def __init__(self, info: dict, parent=None):
        super().__init__(parent)
        self.info = info
        self.zoom = 1.0
        self.pan = QPointF(0, 0)
        self.last = None
        self.bounds = self._bounds()
        self.setMinimumSize(480, 360)

    def _iter_points(self, coords):
        if isinstance(coords, (list, tuple)):
            if len(coords) >= 2 and all(isinstance(x, (int, float)) for x in coords[:2]):
                yield float(coords[0]), float(coords[1])
            else:
                for c in coords:
                    yield from self._iter_points(c)

    def _bounds(self):
        xs, ys = [], []
        for f in self.info.get("features", []):
            for x, y in self._iter_points(f.get("coordinates")):
                xs.append(x); ys.append(y)
        if not xs:
            return (0, 0, 1, 1)
        return (min(xs), min(ys), max(xs), max(ys))

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor("#070c16"))
        x0, y0, x1, y1 = self.bounds
        w = max(1e-9, x1 - x0); h = max(1e-9, y1 - y0)
        s = min(self.width() / w, self.height() / h) * 0.84 * self.zoom
        ox = self.width() / 2 - (x0 + x1) / 2 * s + self.pan.x()
        oy = self.height() / 2 + (y0 + y1) / 2 * s + self.pan.y()

        def T(pt):
            return QPointF(pt[0] * s + ox, -pt[1] * s + oy)

        p.setPen(QPen(QColor("#1e2b42"), 1))
        for i in range(0, 9):
            x = x0 + w * i / 8
            p.drawLine(T((x, y0)), T((x, y1)))
            y = y0 + h * i / 8
            p.drawLine(T((x0, y)), T((x1, y)))
        colors = ["#63b3ed", "#68d391", "#f6ad55", "#f687b3", "#b794f4", "#4fd1c5"]
        for i, f in enumerate(self.info.get("features", [])):
            col = QColor(colors[i % len(colors)])
            p.setPen(QPen(col, 1.6))
            t = f.get("type")
            c = f.get("coordinates")
            try:
                if t == "Point":
                    pt = T(c); p.setBrush(col); p.drawEllipse(pt, 4, 4)
                elif t == "LineString":
                    p.drawPolyline(QPolygonF([T(pt) for pt in c]))
                elif t == "Polygon":
                    for ring in c:
                        p.drawPolygon(QPolygonF([T(pt) for pt in ring]))
                elif t == "MultiPolygon":
                    for poly in c:
                        for ring in poly:
                            p.drawPolygon(QPolygonF([T(pt) for pt in ring]))
                elif t == "MultiLineString":
                    for line in c:
                        p.drawPolyline(QPolygonF([T(pt) for pt in line]))
            except Exception:
                continue
        p.setPen(QColor("#5f738e"))
        p.drawText(12, self.height() - 12, f"{self.info.get('crs','WGS84')} · {len(self.info.get('features', []))} 个要素 · 拖动平移 · 滚轮缩放")

    def mousePressEvent(self, e):
        self.last = e.position()

    def mouseMoveEvent(self, e):
        if self.last is not None and e.buttons() & Qt.MouseButton.LeftButton:
            self.pan += e.position() - self.last
            self.last = e.position()
            self.update()

    def mouseReleaseEvent(self, e):
        self.last = None

    def wheelEvent(self, e):
        self.zoom = max(0.1, min(30, self.zoom * (1.15 if e.angleDelta().y() > 0 else 0.87)))
        self.update()


class GeoViewer(ViewerBase):
    def __init__(self, path: str, parent=None):
        super().__init__(path, parent)
        self.info = geo.load_geo(path)
        self.canvas = GeoCanvas(self.info)
        self.root.addWidget(self.canvas, 1)
        self.tool_button("重置", self.reset)
        self.spacer()
        self.label(f"{len(self.info.get('features', []))} 个要素", "muted")
        self.set_status(f"{os.path.splitext(path)[1].upper().lstrip('.')} · {len(self.info.get('features', []))} 个要素 · {self.info.get('crs','')}")

    def reset(self):
        self.canvas.zoom = 1.0; self.canvas.pan = QPointF(0, 0); self.canvas.update()


class FontViewer(ViewerBase):
    def __init__(self, path: str, parent=None):
        super().__init__(path, parent)
        self.font_id = QFontDatabase.addApplicationFont(path)
        families = QFontDatabase.applicationFontFamilies(self.font_id) if self.font_id >= 0 else []
        self.family = families[0] if families else "Microsoft YaHei"
        self.browser = QTextBrowser()
        self.browser.setObjectName("docView")
        self.browser.setHtml(f"""<html><head><style>
        body{{font-family:'{self.family}';padding:34px 46px;color:#1f2937;background:#fff}}
        .big{{font-size:54px;line-height:1.25}} .mid{{font-size:28px}} .small{{font-size:15px;line-height:1.9}}
        </style></head><body>
        <div class='big'>万象查看器 OmniView</div>
        <div class='mid'>The quick brown fox jumps over the lazy dog.</div>
        <div class='small'>中文排版验收：汉字、标点，。；：“”‘’（）【】《》、生僻字 龘 𠮷<br>
        数字 0123456789 · English ABCdef · © ® ™ ← ↑ → ↓ ✓ ✗ ★ ☆</div>
        <hr><div class='small'>字体：{html.escape(self.family)}</div></body></html>""")
        self.root.addWidget(self.browser, 1)
        try:
            self.info = binary.font_info(path)
        except Exception as e:
            self.info = {"error": str(e)}
        self.spacer(); self.label(self.family, "muted")
        self.set_status(f"字体 · {self.family} · {paths.human_size(os.path.getsize(path))}")


class BinaryViewer(ViewerBase):
    def __init__(self, path: str, parent=None):
        super().__init__(path, parent)
        self.kind = os.path.splitext(path)[1].lower().lstrip(".")
        self.info = self._load()
        self.tabs = QTabWidget()
        self.tabs.addTab(info_tree(self.info), "信息")
        hexw = QPlainTextEdit(); hexw.setReadOnly(True); hexw.setObjectName("codeView")
        try:
            h = textutil.hexdump(path, 0, 16384)
            hexw.setPlainText("\n".join(f"{l['offset']}  {l['hex']}  {l['ascii']}" for l in h["lines"]))
        except Exception as e:
            hexw.setPlainText(str(e))
        self.tabs.addTab(hexw, "十六进制")
        sw = QPlainTextEdit(); sw.setReadOnly(True); sw.setObjectName("codeView")
        try:
            sw.setPlainText("\n".join(s["text"] for s in textutil.strings(path, 4, 1000)))
        except Exception:
            pass
        self.tabs.addTab(sw, "字符串")
        self.root.addWidget(self.tabs, 1)
        self.spacer(); self.label(self.kind.upper(), "muted")
        self.set_status(f"{self.kind.upper()} · {paths.human_size(os.path.getsize(path))}")

    def _load(self):
        try:
            if self.kind in ("exe", "dll", "sys", "scr", "cpl", "ocx"):
                return binary.pe_info(self.path)
            if self.kind == "so":
                return binary.elf_info(self.path)
            if self.kind == "dylib":
                return binary.macho_info(self.path)
            if self.kind in ("step", "stp", "iges", "igs"):
                return binary.step_info(self.path)
            if self.kind == "blend":
                return binary.blend_info(self.path)
            if self.kind == "skp":
                return binary.skp_info(self.path)
            if self.kind == "apk":
                return binary.apk_info(self.path)
            if self.kind == "deb":
                return binary.deb_info(self.path)
            if self.kind == "rpm":
                return binary.rpm_info(self.path)
            if self.kind in ("pst", "ost"):
                return data.pst_info(self.path)
            return {"信息": "不支持的结构", "大小": os.path.getsize(self.path)}
        except Exception as e:
            return {"error": str(e), "大小": os.path.getsize(self.path)}
