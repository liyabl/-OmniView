"""Native viewers for PDF, rich text, Markdown, code, spreadsheets, PPTX and EPUB."""
from __future__ import annotations

import html
import mmap
import os
import re
import shutil
import time

from PySide6.QtCore import Qt, QTimer, QUrl, QSize, Signal, QRectF
from PySide6.QtGui import (QColor, QFont, QFontDatabase, QImage, QPainter, QPalette, QPixmap,
                           QSyntaxHighlighter, QTextCharFormat, QTextCursor, QTextOption, QBrush,
                           QTextDocument)
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
                               QTextBrowser, QPlainTextEdit, QSplitter, QListWidget, QListWidgetItem,
                               QTableWidget, QTableWidgetItem, QTabWidget, QHeaderView, QMessageBox,
                               QFileDialog, QSizePolicy, QFrame, QScrollArea, QAbstractItemView, QTextEdit, QSlider)

from .. import office, paths, tables, textutil
from .common import ViewerBase, info_tree


# ---------------------------------------------------------------- PDF
class PdfViewer(ViewerBase):
    """CPU PDF page renderer via QPdfDocument.render -> QLabel.

    QPdfView's fractional zoom can introduce CJK glyph spacing on Windows;
    rendering pages to QImage at exact pixel sizes avoids that.
    """

    def __init__(self, path: str, parent=None):
        super().__init__(path, parent)
        from PySide6.QtPdf import QPdfDocument
        self.doc = QPdfDocument(self)
        err = self.doc.load(path)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea{background:#1a2233;border:none;}")
        self.container = QWidget()
        self.container.setStyleSheet("background:#1a2233;")
        self.vbox = QVBoxLayout(self.container)
        self.vbox.setContentsMargins(18, 18, 18, 18)
        self.vbox.setSpacing(16)
        self.scroll.setWidget(self.container)
        self.root.addWidget(self.scroll, 1)
        self.labels = []
        self.rendered = set()
        self._zoom = 1.0
        self._page_w = 595.0
        self._page_h = 842.0
        self._current = 0
        self.tool_button("上一页", lambda: self.go(-1))
        self.tool_button("下一页", lambda: self.go(1))
        self.page_label = self.label(f"1 / {self.doc.pageCount()}")
        self.spacer()
        self.tool_button("适合宽度", self.fit_width)
        self.tool_button("整页", self.fit_page)
        self.tool_button("放大", lambda: self.zoom(1.2))
        self.tool_button("缩小", lambda: self.zoom(1 / 1.2))
        self.info = {"格式": "PDF", "页数": self.doc.pageCount(),
                     "大小": paths.human_size(os.path.getsize(path))}
        if err != QPdfDocument.Error.None_:
            self.page_label.setText("PDF 载入失败")
        self.scroll.verticalScrollBar().valueChanged.connect(self._on_scroll)
        QTimer.singleShot(120, self.relayout)

    def _page_size(self):
        try:
            s = self.doc.pagePointSize(0)
            return max(1.0, s.width()), max(1.0, s.height())
        except Exception:
            return 595.0, 842.0

    def _build_labels(self):
        while self.vbox.count():
            item = self.vbox.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self.labels = []
        self.rendered = set()
        self._page_w, self._page_h = self._page_size()
        n = self.doc.pageCount()
        for i in range(n):
            lab = QLabel(f"正在渲染第 {i+1} 页…")
            lab.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lab.setStyleSheet("background:#ffffff;color:#64748b;border:1px solid #334155;")
            lab.setProperty("page", i)
            self.vbox.addWidget(lab, 0, Qt.AlignmentFlag.AlignHCenter)
            self.labels.append(lab)
        self.vbox.addStretch(1)

    def _width(self):
        avail = max(240, self.scroll.viewport().width() - 60)
        return max(200, int(avail * self._zoom))

    def relayout(self):
        if not self.labels:
            self._build_labels()
        w = self._width()
        h = int(w * self._page_h / self._page_w)
        for lab in self.labels:
            lab.setFixedSize(w, h)
            lab.clear()
            lab.setText("…")
        self.rendered.clear()
        try:
            self.vbox.activate()
            self.container.adjustSize()
        except Exception:
            pass
        QTimer.singleShot(0, self._render_visible)

    def _render_visible(self):
        if not self.labels:
            return
        w = self._width()
        h = self.labels[0].height()
        top = self.scroll.verticalScrollBar().value()
        bottom = top + self.scroll.viewport().height()
        for i, lab in enumerate(self.labels):
            y = lab.y()
            if y + h < top - 400 or y > bottom + 400:
                continue
            if i in self.rendered:
                continue
            try:
                img = self.doc.render(i, QSize(w, h))
                if not img.isNull():
                    lab.setPixmap(QPixmap.fromImage(img))
                    lab.setText("")
                    self.rendered.add(i)
            except Exception:
                lab.setText(f"第 {i+1} 页渲染失败")

    def _on_scroll(self, value):
        self._render_visible()
        if not self.labels:
            return
        mid = value + self.scroll.viewport().height() // 3
        cur = 0
        for i, lab in enumerate(self.labels):
            if lab.y() <= mid:
                cur = i
        if cur != self._current:
            self._current = cur
            self.page_label.setText(f"{cur + 1} / {len(self.labels)}")
            self.set_status(f"第 {cur + 1} / {len(self.labels)} 页 · {paths.human_size(os.path.getsize(self.path))}")

    def fit_width(self):
        self._zoom = 1.0
        self.relayout()

    def fit_page(self):
        w = self._width()
        h = int(w * self._page_h / self._page_w)
        avail = max(200, self.scroll.viewport().height() - 50)
        self._zoom = max(0.25, min(1.0, avail / max(1, h)))
        self.relayout()

    def zoom(self, factor):
        self._zoom = max(0.2, min(5.0, self._zoom * factor))
        self.relayout()

    def go(self, delta):
        if not self.labels:
            return
        idx = max(0, min(len(self.labels) - 1, self._current + delta))
        self.scroll.ensureWidgetVisible(self.labels[idx], 0, 0)
        self._current = idx
        self.page_label.setText(f"{idx + 1} / {len(self.labels)}")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.labels:
            QTimer.singleShot(80, self.relayout)


# ---------------------------------------------------------------- Chunked large text
class ChunkedTextViewer(ViewerBase):
    """Memory-mapped, windowed text viewer for 100MB+ files.

    Only one 2MB window is decoded into the QPlainTextEdit at a time.
    """
    WINDOW = 2 * 1024 * 1024

    def __init__(self, path: str, parent=None):
        super().__init__(path, parent)
        self._fh = open(path, "rb")
        self._mm = mmap.mmap(self._fh.fileno(), 0, access=mmap.ACCESS_READ)
        self.size = len(self._mm)
        sample = bytes(self._mm[: min(self.size, 256 * 1024)])
        info = textutil.decode_bytes(sample)
        self.encoding = info["encoding"]
        self.offset = 0
        self.editor = QPlainTextEdit()
        self.editor.setReadOnly(True)
        self.editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self.editor.setStyleSheet("QPlainTextEdit{font-family:'Cascadia Mono','Consolas','Microsoft YaHei UI';"
                                  "font-size:10pt;background:#0f172a;color:#dbe7f5;border:none;padding:14px;}")
        self.root.addWidget(self.editor, 1)
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, 1000)
        self.slider.setValue(0)
        self.slider.sliderReleased.connect(self._seek_slider)
        self.root.addWidget(self.slider)
        row = QHBoxLayout()
        self.pos = QLabel("")
        self.pos.setStyleSheet("color:#5f738e;font-size:8.5pt;")
        row.addWidget(self.pos, 1)
        self.prev = self.tool_button("上一段", lambda: self.move_window(-1))
        self.next = self.tool_button("下一段", lambda: self.move_window(1))
        self.goto = self.tool_button("跳到", self._seek_slider)
        self.enc = QComboBox()
        for code, label in textutil.ENCODING_CHOICES:
            self.enc.addItem(label, code)
        idx = self.enc.findData(self.encoding)
        if idx >= 0:
            self.enc.setCurrentIndex(idx)
        self.enc.currentIndexChanged.connect(self._encoding_changed)
        row.addWidget(self.enc)
        self.root.addLayout(row)
        self.info = {"格式": "TEXT (chunked)", "编码": info["label"],
                     "大小": paths.human_size(self.size), "模式": "2MB 窗口 · 按需加载"}
        self.load_window(0)

    def _decode(self, data: bytes) -> str:
        enc = self.enc.currentData() if hasattr(self, "enc") else self.encoding
        try:
            return data.decode(enc, errors="replace")
        except Exception:
            return data.decode("utf-8", errors="replace")

    def load_window(self, offset: int):
        offset = max(0, min(self.size, int(offset)))
        # align start to the next newline so we do not show half a line
        if offset > 0:
            probe = bytes(self._mm[offset: min(self.size, offset + 1024 * 1024)])
            nl = probe.find(b"\n")
            if nl >= 0:
                offset += nl + 1
        end = min(self.size, offset + self.WINDOW)
        if end < self.size:
            tail = bytes(self._mm[end: min(self.size, end + 512 * 1024)])
            nl = tail.find(b"\n")
            if nl >= 0:
                end += nl + 1
        data = bytes(self._mm[offset:end])
        self.offset = offset
        self.editor.setPlainText(self._decode(data))
        self.editor.moveCursor(QTextCursor.MoveOperation.Start)
        self.slider.blockSignals(True)
        self.slider.setValue(int(offset * 1000 / max(1, self.size)))
        self.slider.blockSignals(False)
        pct = offset * 100 / max(1, self.size)
        self.pos.setText(f"{paths.human_size(self.size)} · 窗口 {paths.human_size(len(data))} · "
                         f"偏移 {paths.human_size(offset)} ({pct:.1f}%)")
        self.set_status(f"TEXT · 分块只读 · {paths.human_size(self.size)} · 编码 {self.enc.currentText()}")
        self.prev.setEnabled(offset > 0)
        self.next.setEnabled(end < self.size)

    def move_window(self, delta):
        self.load_window(self.offset + delta * self.WINDOW)

    def _seek_slider(self):
        self.load_window(int(self.size * self.slider.value() / 1000))

    def _encoding_changed(self):
        self.encoding = self.enc.currentData()
        self.load_window(self.offset)

    def closeEvent(self, event):
        try:
            self._mm.close()
            self._fh.close()
        except Exception:
            pass
        super().closeEvent(event)


# ---------------------------------------------------------------- Rich text
class RichTextViewer(ViewerBase):
    def __init__(self, path: str, parent=None):
        super().__init__(path, parent)
        self.browser = QTextBrowser()
        self.browser.setObjectName("docView")
        self.browser.setOpenExternalLinks(True)
        self.browser.setOpenLinks(True)
        self.root.addWidget(self.browser, 1)
        self._zoom_steps = 0
        self.tool_button("放大", lambda: self.zoom(1))
        self.tool_button("缩小", lambda: self.zoom(-1))
        self.tool_button("重置", lambda: self.zoom(0, reset=True))
        self.spacer()
        self.label("只读", "muted")
        self._loaded = False

    def showEvent(self, event):
        super().showEvent(event)
        if not self._loaded:
            self._loaded = True
            QTimer.singleShot(250, self.load)

    def zoom(self, step, reset=False):
        if reset:
            if self._zoom_steps:
                self.browser.zoomIn(-self._zoom_steps)
            self._zoom_steps = 0
        else:
            self.browser.zoomIn(step)
            self._zoom_steps += step

    def load(self):
        ext = os.path.splitext(self.path)[1].lower().lstrip(".")
        try:
            if ext == "docx":
                html_text = office.docx_to_html(self.path)
            elif ext == "odt":
                html_text = office.odt_to_html(self.path)
            elif ext == "rtf":
                html_text = office.rtf_to_html(self.path)
            elif ext == "md":
                html_text = office.markdown_to_html(self.path)
            elif ext in ("html", "htm"):
                self.browser.setSource(QUrl.fromLocalFile(self.path))
                QTimer.singleShot(0, self._to_top)
                self.set_status("HTML · 只读")
                return
            elif ext in ("ipynb",):
                html_text = office.notebook_to_html(self.path)
            elif ext in ("odp",):
                html_text = self._odp_text()
            else:
                html_text = office.docx_to_html(self.path)
            self.browser.setHtml(html_text)
            QTimer.singleShot(0, self._to_top)
            self.set_status(f"{ext.upper()} · 只读 · {paths.human_size(os.path.getsize(self.path))}")
        except Exception as e:
            self.browser.setHtml(f"<h3>无法解析</h3><pre>{html.escape(str(e))}</pre>")

    def _to_top(self):
        try:
            self.browser.moveCursor(QTextCursor.MoveOperation.Start)
            self.browser.verticalScrollBar().setValue(0)
        except Exception:
            pass

    def _odp_text(self) -> str:
        try:
            from odf.opendocument import load
            from odf import text as odftext, teletype
            doc = load(self.path)
            parts = []
            for p in doc.text.getElementsByType(odftext.P):
                t = teletype.extractText(p)
                if t.strip():
                    parts.append(f"<p>{html.escape(t)}</p>")
            return office._wrap("".join(parts) or "<p>没有可显示的幻灯片文本。</p>")
        except Exception as e:
            return office._wrap(f"<p>ODP 解析失败：{html.escape(str(e))}</p>")


# ---------------------------------------------------------------- Code editor
class _LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self):
        return QSize(self.editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.editor.line_number_area_paint_event(event)


class CodeEditor(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("codeView")
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.setTabStopDistance(32)
        self.line_number_area = _LineNumberArea(self)
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self.highlight_current_line)
        self.update_line_number_area_width(0)
        self.highlight_current_line()

    def line_number_area_width(self):
        digits = max(2, len(str(max(1, self.blockCount()))))
        return 12 + self.fontMetrics().horizontalAdvance("9") * digits

    def update_line_number_area_width(self, _):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect, dy):
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(cr.left(), cr.top(), self.line_number_area_width(), cr.height())

    def line_number_area_paint_event(self, event):
        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), QColor("#080e19"))
        block = self.firstVisibleBlock()
        num = block.blockNumber()
        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()
        painter.setFont(self.font())
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                painter.setPen(QColor("#3f5570"))
                painter.drawText(0, int(top), self.line_number_area.width() - 8,
                                 self.fontMetrics().height(), Qt.AlignmentFlag.AlignRight, str(num + 1))
            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()
            num += 1

    def highlight_current_line(self):
        sel = QTextEdit.ExtraSelection()
        sel.format.setBackground(QColor("#0e1a2c"))
        sel.format.setProperty(QTextCharFormat.Property.FullWidthSelection, True)
        sel.cursor = self.textCursor()
        sel.cursor.clearSelection()
        self.setExtraSelections([sel])


class PygmentsHighlighter(QSyntaxHighlighter):
    def __init__(self, document, filename: str):
        super().__init__(document)
        self.formats = {}
        try:
            from pygments.lexers import get_lexer_for_filename
            self.lexer = get_lexer_for_filename(filename, stripnl=False)
        except Exception:
            self.lexer = None
        self.colors = {
            "k": "#c792ea", "kc": "#c792ea", "kd": "#c792ea", "kn": "#c792ea", "kp": "#c792ea", "kr": "#c792ea", "kt": "#c792ea",
            "s": "#a7f3d0", "s1": "#a7f3d0", "s2": "#a7f3d0", "sb": "#a7f3d0", "sc": "#a7f3d0", "sd": "#a7f3d0", "se": "#a7f3d0",
            "c": "#5f738e", "c1": "#5f738e", "cm": "#5f738e", "cs": "#5f738e", "cp": "#5f738e",
            "m": "#f6ad55", "mf": "#f6ad55", "mi": "#f6ad55", "mh": "#f6ad55", "mo": "#f6ad55",
            "nb": "#63b3ed", "nf": "#7aa2ff", "nc": "#f687b3", "nn": "#f687b3", "nd": "#f6ad55",
            "o": "#cbd5e1", "ow": "#c792ea", "p": "#94a3b8",
        }

    def _fmt(self, token_type: str) -> QTextCharFormat:
        key = token_type.split(".")[0]
        if key == "Token":
            key = "."
        color = self.colors.get(key) or self.colors.get(token_type)
        fmt = QTextCharFormat()
        if color:
            fmt.setForeground(QColor(color))
        if key in ("c", "cm", "c1"):
            fmt.setFontItalic(True)
        if key in ("k", "kc", "kd", "kn", "kr", "kt"):
            fmt.setFontWeight(QFont.Weight.Bold)
        return fmt

    def highlightBlock(self, text: str):
        if not self.lexer:
            return
        try:
            pos = 0
            for ttype, value in self.lexer.get_tokens(text):
                ln = len(value)
                if ln:
                    self.setFormat(pos, ln, self._fmt(str(ttype)))
                pos += ln
                if pos > len(text):
                    break
        except Exception:
            pass


class TextViewer(ViewerBase):
    def __init__(self, path: str, parent=None):
        super().__init__(path, parent)
        self.data = None
        self.encoding = "auto"
        self.editor = CodeEditor()
        self.highlighter = None
        self.root.addWidget(self.editor, 1)
        self.enc = QComboBox()
        for v, label in textutil.ENCODING_CHOICES:
            self.enc.addItem(label, v)
        self.toolbar.addWidget(self.enc)
        self.enc.currentIndexChanged.connect(self.reload_encoding)
        self.btn_save = self.tool_button("保存", self.save, "Ctrl+S")
        self.tool_button("查找", self.find)
        self.spacer()
        self.label("可编辑", "muted")
        self.load()

    def load(self):
        try:
            self.data = textutil.read_text(self.path, self.encoding)
        except Exception as e:
            self.editor.setPlainText(f"无法读取：{e}")
            return
        self.editor.setPlainText(self.data.get("text", ""))
        self.highlighter = PygmentsHighlighter(self.editor.document(), self.path)
        self.enc.blockSignals(True)
        idx = self.enc.findData(self.data.get("encoding", "utf-8"))
        if idx >= 0:
            self.enc.setCurrentIndex(idx)
        self.enc.blockSignals(False)
        self.editor.document().modificationChanged.connect(self._dirty_changed)
        self.editor.document().setModified(False)
        self._update_status()

    def _update_status(self):
        txt = self.editor.toPlainText()
        self.set_status(f"{self.data.get('label','')} · {txt.count(chr(10))+1} 行 · {paths.human_size(len(txt.encode('utf-8')))}")

    def _dirty_changed(self, dirty):
        self._dirty = dirty
        self.btn_save.setText("保存 *" if dirty else "保存")

    def reload_encoding(self):
        if self._dirty and QMessageBox.question(self, "切换编码", "当前修改未保存，切换编码会丢失修改。继续？") != QMessageBox.StandardButton.Yes:
            return
        self.encoding = self.enc.currentData()
        self.load()

    def find(self):
        from PySide6.QtWidgets import QInputDialog
        text, ok = QInputDialog.getText(self, "查找", "查找内容：")
        if ok and text:
            if not self.editor.find(text):
                cur = self.editor.textCursor()
                cur.movePosition(QTextCursor.MoveOperation.Start)
                self.editor.setTextCursor(cur)
                self.editor.find(text)

    def save(self):
        if not self.editor.document().isModified():
            return
        enc = self.enc.currentData()
        if enc == "auto":
            enc = self.data.get("encoding", "utf-8")
        try:
            os.makedirs(paths.BACKUPS, exist_ok=True)
            bak = os.path.join(paths.BACKUPS, os.path.basename(self.path) + "." + time.strftime("%Y%m%d-%H%M%S") + ".bak")
            shutil.copy2(self.path, bak)
            content = self.editor.toPlainText()
            data = content.encode(enc, errors="strict")
            if enc == "utf-8-sig" and not data.startswith(b"\xef\xbb\xbf"):
                data = b"\xef\xbb\xbf" + data
            tmp = self.path + ".ovtmp"
            open(tmp, "wb").write(data)
            os.replace(tmp, self.path)
            self.editor.document().setModified(False)
            self.set_status(f"已保存 · {enc} · 备份 {os.path.basename(bak)}")
        except Exception as e:
            QMessageBox.critical(self, "保存失败", str(e))

    def keyPressEvent(self, event):
        if event.modifiers() & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.MetaModifier) and event.key() == Qt.Key.Key_S:
            self.save()
            return
        super().keyPressEvent(event)

    def can_close(self) -> bool:
        if not self.editor.document().isModified():
            return True
        r = QMessageBox.question(self, "未保存", "文本有未保存的修改，是否保存？",
                                 QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel)
        if r == QMessageBox.StandardButton.Cancel:
            return False
        if r == QMessageBox.StandardButton.Save:
            self.save()
            return not self.editor.document().isModified()
        return True


class MarkdownViewer(ViewerBase):
    def __init__(self, path: str, parent=None):
        super().__init__(path, parent)
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.preview = QTextBrowser()
        self.preview.setObjectName("docView")
        self.preview.setOpenExternalLinks(True)
        self.source = QPlainTextEdit()
        self.source.setObjectName("codeView")
        self.splitter.addWidget(self.preview)
        self.splitter.addWidget(self.source)
        self.splitter.setSizes([620, 520])
        self.root.addWidget(self.splitter, 1)
        self.tool_button("预览", lambda: self.set_mode(0))
        self.tool_button("分栏", lambda: self.set_mode(1))
        self.tool_button("源码", lambda: self.set_mode(2))
        self.tool_button("保存", self.save)
        self.spacer()
        self.label("可编辑", "muted")
        self.data = textutil.read_text(path)
        self.source.setPlainText(self.data.get("text", ""))
        self.highlighter = PygmentsHighlighter(self.source.document(), path)
        self.source.document().modificationChanged.connect(lambda d: setattr(self, "_dirty", d))
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(180)
        self.timer.timeout.connect(self.update_preview)
        self.source.textChanged.connect(self.timer.start)
        self.update_preview()
        self.set_mode(1)

    def set_mode(self, mode):
        if mode == 0:
            self.preview.show(); self.source.hide()
        elif mode == 2:
            self.preview.hide(); self.source.show()
        else:
            self.preview.show(); self.source.show()

    def update_preview(self):
        import markdown
        html_text = markdown.markdown(self.source.toPlainText(), extensions=["tables", "fenced_code", "sane_lists"])
        base = QUrl.fromLocalFile(os.path.dirname(self.path) + os.sep).toString()
        html_text = re.sub(r'(<img[^>]+src=")([^"]+)"', lambda m: m.group(1) + (m.group(2) if "://" in m.group(2) else base + m.group(2)) + '"', html_text)
        self.preview.setHtml(f"<html><head><style>body{{font-family:'Microsoft YaHei';font-size:15px;line-height:1.9;color:#1f2937;padding:32px 40px;}}h1,h2,h3{{color:#0f172a;}}pre{{background:#f6f8fa;padding:12px;}}code{{background:#f1f5f9;}}table{{border-collapse:collapse}}td,th{{border:1px solid #cbd5e1;padding:5px 8px}}blockquote{{border-left:3px solid #93c5fd;background:#f8fafc;padding:4px 14px}}</style></head><body>{html_text}</body></html>")
        self.set_status(f"Markdown · {self.source.blockCount()} 行")

    def save(self):
        if not self.source.document().isModified():
            return
        try:
            enc = self.data.get("encoding", "utf-8")
            bak = os.path.join(paths.BACKUPS, os.path.basename(self.path) + "." + time.strftime("%Y%m%d-%H%M%S") + ".bak")
            shutil.copy2(self.path, bak)
            data = self.source.toPlainText().encode(enc, errors="strict")
            tmp = self.path + ".ovtmp"
            open(tmp, "wb").write(data)
            os.replace(tmp, self.path)
            self.source.document().setModified(False)
            self.set_status("已保存 · 备份 " + os.path.basename(bak))
        except Exception as e:
            QMessageBox.critical(self, "保存失败", str(e))

    def can_close(self) -> bool:
        if not self.source.document().isModified():
            return True
        r = QMessageBox.question(self, "未保存", "Markdown 有未保存的修改，是否保存？",
                                 QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel)
        if r == QMessageBox.StandardButton.Cancel:
            return False
        if r == QMessageBox.StandardButton.Save:
            self.save()
            return not self.source.document().isModified()
        return True


# ---------------------------------------------------------------- Spreadsheet
class SheetViewer(ViewerBase):
    def __init__(self, path: str, parent=None):
        super().__init__(path, parent)
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.root.addWidget(self.tabs, 1)
        self.data = None
        self.spacer()
        self.label("只读", "muted")
        self.load()

    def load(self):
        ext = os.path.splitext(self.path)[1].lower().lstrip(".")
        try:
            if ext in ("csv", "tsv"):
                d = tables.csv_data(self.path)
                self._add_sheet(d)
                self.set_status(f"CSV · {d['encoding']} · {d['rows']} 行 × {d['cols']} 列")
                return
            d = tables.xlsx_data(self.path)
            for name in d["sheets"]:
                sd = d if name == d["sheet"] else tables.xlsx_data(self.path, name)
                self._add_sheet(sd)
            self.set_status(f"XLSX · {len(d['sheets'])} 个工作表 · {d['rows']} 行")
        except Exception as e:
            self.tabs.addTab(QLabel(f"无法解析表格：{e}"), "错误")

    def _add_sheet(self, d):
        rows, cols = d["rows"], d["cols"]
        table = QTableWidget(rows, cols)
        table.setAlternatingRowColors(True)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.horizontalHeader().setDefaultSectionSize(96)
        table.horizontalHeader().setStretchLastSection(True)
        table.verticalHeader().setDefaultSectionSize(24)
        for c in range(cols):
            table.setHorizontalHeaderItem(c, QTableWidgetItem(_col_name(c + 1)))
        for r in range(rows):
            for c in range(cols):
                cell = d["grid"][r][c]
                item = QTableWidgetItem(str(cell.get("d", "")))
                st = d["styles"][cell.get("s", 0)] if d.get("styles") else {}
                if st.get("b"):
                    f = item.font(); f.setBold(True); item.setFont(f)
                if st.get("i"):
                    f = item.font(); f.setItalic(True); item.setFont(f)
                if st.get("fc"):
                    item.setForeground(QColor(st["fc"]))
                if st.get("bg"):
                    item.setBackground(QColor(st["bg"]))
                if st.get("ha") == "center":
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                elif st.get("ha") == "right":
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                if cell.get("f"):
                    item.setToolTip(cell["f"])
                table.setItem(r, c, item)
        for m in d.get("merges", []):
            mm = re.match(r"([A-Z]+)(\d+):([A-Z]+)(\d+)", m)
            if mm:
                r1, c1 = int(mm.group(2)) - 1, _col_num(mm.group(1)) - 1
                r2, c2 = int(mm.group(4)) - 1, _col_num(mm.group(3)) - 1
                if r2 < rows and c2 < cols:
                    table.setSpan(r1, c1, r2 - r1 + 1, c2 - c1 + 1)
        for k, w in (d.get("widths") or {}).items():
            idx = _col_num(k) - 1
            if 0 <= idx < cols:
                table.setColumnWidth(idx, max(50, min(420, int(w * 7.6))))
        self.tabs.addTab(table, d["sheet"])


def _col_name(n):
    s = ""
    while n > 0:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def _col_num(s):
    n = 0
    for ch in s:
        n = n * 26 + ord(ch) - 64
    return n


# ---------------------------------------------------------------- PPTX
class SlideCanvas(QWidget):
    def __init__(self, slides, parent=None):
        super().__init__(parent)
        self.slides = slides
        self.index = 0
        self.setMinimumSize(480, 270)
        self.setStyleSheet("background:#05080f;")

    def set_index(self, i):
        self.index = max(0, min(i, len(self.slides) - 1))
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor("#05080f"))
        if not self.slides:
            p.setPen(QColor("#91a4bd")); p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "没有幻灯片")
            return
        s = self.slides[self.index]
        sw, sh = self.slides_wh()
        scale = min((self.width() - 32) / sw, (self.height() - 32) / sh)
        ox = (self.width() - sw * scale) / 2
        oy = (self.height() - sh * scale) / 2
        p.fillRect(QRectF(ox, oy, sw * scale, sh * scale), QColor("#ffffff"))
        for shp in s["shapes"]:
            self._shape(p, shp, scale, ox, oy)

    def slides_wh(self):
        return getattr(self, "_w", 12192000), getattr(self, "_h", 6858000)

    def _shape(self, p, sh, scale, ox, oy):
        from PySide6.QtCore import QRectF
        x, y, w, h = sh.get("x", 0), sh.get("y", 0), sh.get("w", 0), sh.get("h", 0)
        if w <= 0 or h <= 0:
            return
        X, Y, W, H = ox + x * scale, oy + y * scale, w * scale, h * scale
        kind = sh.get("kind")
        if kind == "image":
            img = QImage(sh.get("path", ""))
            if not img.isNull():
                p.drawImage(QRectF(X, Y, W, H), img)
            return
        fill = sh.get("fill")
        if fill:
            p.setBrush(QColor(fill)); p.setPen(Qt.PenStyle.NoPen)
            p.drawRect(QRectF(X, Y, W, H))
        if kind == "text":
            # Use QTextDocument so multi-paragraph text wraps like a real text frame.
            html_parts = []
            for para in sh.get("paras", []):
                text = "".join(r.get("text", "") for r in para.get("runs", []))
                if not text.strip():
                    continue
                fs = 18
                color = "#111827"
                bold = False
                italic = False
                for r in para.get("runs", []):
                    if r.get("size"):
                        fs = r["size"]
                    if r.get("color"):
                        color = r["color"]
                    bold = bold or r.get("bold")
                    italic = italic or r.get("italic")
                align = "left"
                if "CENTER" in (para.get("align") or ""):
                    align = "center"
                elif "RIGHT" in (para.get("align") or ""):
                    align = "right"
                px = max(6, int(fs * 12700 * scale))
                html_parts.append(
                    f"<p style='margin:0;padding:0;text-align:{align};color:{color};"
                    f"font-size:{px}px;font-weight:{'700' if bold else '400'};"
                    f"font-style:{'italic' if italic else 'normal'};'>{html.escape(text)}</p>")
            if html_parts:
                doc = QTextDocument()
                doc.setDocumentMargin(0)
                doc.setDefaultFont(QFont("Microsoft YaHei"))
                doc.setHtml("".join(html_parts))
                doc.setTextWidth(max(1, W))
                p.save()
                p.translate(X, Y)
                p.setClipRect(QRectF(0, 0, max(1, W), max(1, H)))
                doc.drawContents(p, QRectF(0, 0, max(1, W), max(1, H)))
                p.restore()


class PptxViewer(ViewerBase):
    def __init__(self, path: str, parent=None):
        super().__init__(path, parent)
        self.data = None
        split = QSplitter(Qt.Orientation.Horizontal)
        self.list = QListWidget()
        self.list.setMaximumWidth(170)
        self.canvas = SlideCanvas([])
        split.addWidget(self.list)
        split.addWidget(self.canvas)
        split.setSizes([160, 900])
        self.root.addWidget(split, 1)
        self.tool_button("上一页", lambda: self.go(-1))
        self.tool_button("下一页", lambda: self.go(1))
        self.spacer()
        self.label("只读", "muted")
        self.load()

    def load(self):
        try:
            d = office.pptx_slides(self.path)
            self.data = d
            self.canvas._w = d["width"]; self.canvas._h = d["height"]
            self.canvas.slides = d["slides"]
            self.list.clear()
            for i in range(len(d["slides"])):
                self.list.addItem(f"第 {i+1} 页")
            self.list.currentRowChanged.connect(self._row)
            if self.list.count():
                self.list.setCurrentRow(0)
            self.set_status(f"PPTX · {len(d['slides'])} 页")
        except Exception as e:
            self.canvas.slides = []
            self.label(f"无法解析：{e}")

    def _row(self, i):
        self.canvas.set_index(i)
        self.set_status(f"第 {i+1} / {len(self.canvas.slides)} 页")

    def go(self, delta):
        i = self.list.currentRow()
        self.list.setCurrentRow(max(0, min(self.list.count() - 1, i + delta)))


# ---------------------------------------------------------------- EPUB / MOBI
class EpubViewer(ViewerBase):
    def __init__(self, path: str, parent=None):
        super().__init__(path, parent)
        self.meta = None
        split = QSplitter(Qt.Orientation.Horizontal)
        self.toc = QListWidget()
        self.toc.setMaximumWidth(230)
        self.browser = QTextBrowser()
        self.browser.setObjectName("docView")
        self.browser.setOpenExternalLinks(True)
        split.addWidget(self.toc)
        split.addWidget(self.browser)
        split.setSizes([210, 850])
        self.root.addWidget(split, 1)
        self.tool_button("上一节", lambda: self.go(-1))
        self.tool_button("下一节", lambda: self.go(1))
        self.spacer()
        self.label("只读", "muted")
        self.load()

    def load(self):
        try:
            ext = os.path.splitext(self.path)[1].lower().lstrip(".")
            if ext in ("mobi", "azw3"):
                self.path = office.mobi_to_epub(self.path)
            self.meta = office.epub_extract(self.path)
            self.toc.clear()
            items = self.meta.get("toc") or [{"label": s.get("title", s["href"]), "href": s["href"]} for s in self.meta["spine"]]
            for it in items:
                li = QListWidgetItem(it.get("label", ""))
                li.setData(Qt.ItemDataRole.UserRole, it.get("href", ""))
                self.toc.addItem(li)
            self.toc.currentRowChanged.connect(self._open_toc)
            if self.toc.count():
                self.toc.setCurrentRow(0)
            self.set_status(f"{ext.upper()} · {self.meta.get('title','')} · {len(self.meta['spine'])} 节")
        except Exception as e:
            self.browser.setHtml(f"<h3>无法打开电子书</h3><pre>{html.escape(str(e))}</pre>")

    def _open_toc(self, row):
        if row < 0 or row >= self.toc.count():
            return
        href = self.toc.item(row).data(Qt.ItemDataRole.UserRole)
        base = self.meta.get("root", "")
        relbase = self.meta.get("base", "")
        path = os.path.join(base, *relbase.replace("/", os.sep).split(os.sep), *href.replace("/", os.sep).split(os.sep))
        if not os.path.exists(path):
            path = os.path.join(base, *href.replace("/", os.sep).split(os.sep))
        if os.path.exists(path):
            try:
                raw = open(path, "r", encoding="utf-8", errors="replace").read()
                self.browser.document().setBaseUrl(QUrl.fromLocalFile(os.path.dirname(path) + os.sep))
                self.browser.setHtml(raw)
            except Exception as e:
                self.browser.setHtml(f"<p>无法读取章节：{html.escape(str(e))}</p>")

    def go(self, delta):
        self.toc.setCurrentRow(max(0, min(self.toc.count() - 1, self.toc.currentRow() + delta)))
