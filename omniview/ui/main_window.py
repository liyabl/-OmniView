"""Native main window: sidebar, tabs, recent files, info dock, drag & drop."""
from __future__ import annotations

import os
import sys

from PySide6.QtCore import Qt, QSize, QSettings, QTimer, QUrl, QProcess
from PySide6.QtGui import QAction, QIcon, QKeySequence, QPixmap, QDesktopServices
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                               QListWidget, QListWidgetItem, QTabWidget, QSplitter, QFileDialog,
                               QMessageBox, QDockWidget, QTreeWidget, QTreeWidgetItem, QToolBar, QStatusBar, QFrame,
                               QSizePolicy, QMenu, QApplication, QDialog)

from .. import i18n, paths, plugin_manager, registry
from ..i18n import T
from .common import ViewerBase, info_tree
from .theme import ACCENT


CATEGORIES = [
    ("cat.all", None),
    ("cat.doc", {"pdf", "docx", "odt", "rtf", "md", "txt", "xlsx", "csv", "pptx", "odp", "epub", "mobi", "azw3", "tex"}),
    ("cat.image", {"jpg", "jpeg", "png", "gif", "svg", "webp", "tif", "tiff", "bmp", "ico", "psd", "ai", "raw", "cr2", "nef", "arw", "dng"}),
    ("cat.media", {"mp3", "aac", "m4a", "flac", "wav", "ogg", "opus", "aiff", "mid", "midi", "mp4", "mkv", "webm", "mov", "m4v", "avi", "wmv", "flv", "rmvb", "mpg", "mpeg", "ts"}),
    ("cat.archive", {"zip", "7z", "rar", "tar", "gz", "bz2", "xz", "tgz", "zst", "iso", "dmg", "cab", "jar"}),
    ("cat.code", {"c", "cpp", "h", "hpp", "cs", "java", "py", "js", "jsx", "ts", "tsx", "vue", "html", "htm", "css", "scss", "less", "php", "rb", "go", "rs", "kt", "swift", "lua", "r", "sql", "json", "xml", "yaml", "yml", "toml", "sh", "bash", "bat", "cmd", "ps1", "ipynb"}),
    ("cat.data", {"db", "sqlite", "sqlite3", "mdb", "accdb", "dbf", "h5", "hdf5", "onnx", "pt", "pth", "pkl", "tflite", "pb", "eml", "msg", "pst", "ost", "mbox"}),
    ("cat.pro", {"dwg", "dxf", "stl", "step", "stp", "obj", "fbx", "glb", "gltf", "usdz", "3mf", "blend", "skp", "shp", "shx", "prj", "kml", "kmz", "geojson", "gpx", "exe", "dll", "so", "dylib", "sys", "ttf", "otf", "woff", "woff2"}),
]


def _ext(path: str) -> str:
    low = path.lower()
    for m in ("tar.gz", "tar.bz2", "tar.xz", "tar.zst"):
        if low.endswith("." + m):
            return m
    return os.path.splitext(path)[1].lower().lstrip(".")


def _is_ts_video(path: str) -> bool:
    try:
        with open(path, "rb") as f:
            h = f.read(377)
        return len(h) > 2 and h[0] == 0x47 and ((len(h) > 188 and h[188] == 0x47) or len(h) < 188)
    except OSError:
        return False


class Welcome(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window = window
        lay = QVBoxLayout(self)
        lay.setContentsMargins(56, 46, 56, 46)
        lay.setSpacing(12)
        title = QLabel(T("welcome.title"))
        title.setObjectName("title")
        sub = QLabel(T("welcome.sub"))
        sub.setObjectName("subtitle")
        sub.setWordWrap(True)
        lay.addWidget(title)
        lay.addWidget(sub)
        line = QFrame(); line.setFrameShape(QFrame.Shape.HLine); line.setStyleSheet("color:#24344f;")
        lay.addWidget(line)
        body = QLabel(T("welcome.body"))
        body.setWordWrap(True)
        body.setStyleSheet("color:#91a4bd;font-size:11pt;line-height:1.8;")
        lay.addWidget(body)
        row = QHBoxLayout()
        b1 = QPushButton(T("welcome.open"))
        b1.setObjectName("primary")
        b1.setFixedHeight(38)
        b1.clicked.connect(window.open_dialog)
        b2 = QPushButton(T("welcome.last"))
        b2.setFixedHeight(38)
        b2.clicked.connect(window.open_last_folder)
        row.addWidget(b1); row.addWidget(b2); row.addStretch(1)
        lay.addLayout(row)
        lay.addStretch(1)
        hint = QLabel(T("welcome.hint"))
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#5f738e;font-size:9pt;")
        lay.addWidget(hint)


class MainWindow(QMainWindow):
    def __init__(self, initial: str | None = None):
        super().__init__()
        self.setWindowTitle(T("app.title"))
        icon = paths.bundled("assets", "app.ico")
        if os.path.exists(icon):
            self.setWindowIcon(QIcon(icon))
        self.resize(1380, 900)
        self.setMinimumSize(1000, 680)
        self.setAcceptDrops(True)
        self.settings = QSettings("OmniView", "OmniView")
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.setDocumentMode(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self._tab_changed)
        self.sidebar = self._build_sidebar()
        self.split = QSplitter(Qt.Orientation.Horizontal)
        self.split.addWidget(self.sidebar)
        self.split.addWidget(self.tabs)
        self.split.setSizes([250, 1100])
        self.split.setStretchFactor(1, 1)
        self.setCentralWidget(self.split)
        self.dock = QDockWidget(T("action.info"), self)
        self.dock.setObjectName("infoDock")
        self.dock.setAllowedAreas(Qt.DockWidgetArea.RightDockWidgetArea | Qt.DockWidgetArea.LeftDockWidgetArea)
        self.info = QTreeWidget()
        self.info.setHeaderLabels([T("info.item"), T("info.value")])
        self.info.setRootIsDecorated(False)
        self.info.setColumnWidth(0, 120)
        self.dock.setWidget(self.info)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dock)
        self.dock.hide()
        self._build_toolbar()
        self._build_menu()
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status_label = QLabel(T("status.ready"))
        self.status.addWidget(self.status_label, 1)
        self.meta_label = QLabel("OmniView 0.3 · CPU")
        self.status.addPermanentWidget(self.meta_label)
        self.welcome = Welcome(self)
        self.tabs.addTab(self.welcome, T("app.title"))
        self.tabs.tabBar().setTabButton(0, self.tabs.tabBar().ButtonPosition.RightSide, None)
        self._load_recent()
        if initial:
            QTimer.singleShot(80, lambda: self.open_path(initial))

    # ---------------------------------------------------------------- UI
    def _build_sidebar(self):
        w = QWidget()
        w.setMinimumWidth(210); w.setMaximumWidth(320)
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 14, 12, 12)
        lay.setSpacing(8)
        logo = QLabel(T("app.title"))
        logo.setStyleSheet("font-size:14pt;font-weight:700;color:#e6edf7;padding:2px 4px 6px;")
        lay.addWidget(logo)
        sub = QLabel(T("app.subtitle"))
        sub.setStyleSheet("color:#5f738e;font-size:8.5pt;padding:0 4px 8px;")
        lay.addWidget(sub)
        open_btn = QPushButton(T("side.open"))
        open_btn.setObjectName("primary")
        open_btn.setFixedHeight(34)
        open_btn.clicked.connect(self.open_dialog)
        lay.addWidget(open_btn)
        self.cat_list = QListWidget()
        self.cat_list.setMinimumHeight(210)
        for key, _ in CATEGORIES:
            self.cat_list.addItem(T(key))
        self.cat_list.setCurrentRow(0)
        self.cat_list.itemClicked.connect(self._category_clicked)
        lay.addWidget(self.cat_list)
        lay.addWidget(QLabel(T("side.recent")))
        self.recent_list = QListWidget()
        self.recent_list.setMinimumHeight(180)
        self.recent_list.itemDoubleClicked.connect(self._recent_open)
        lay.addWidget(self.recent_list, 1)
        hint = QLabel(T("side.hint"))
        hint.setStyleSheet("color:#5f738e;font-size:8.5pt;line-height:1.7;padding:4px;")
        lay.addWidget(hint)
        return w

    def _build_toolbar(self):
        tb = QToolBar(T("menu.view"))
        tb.setMovable(False)
        tb.setIconSize(QSize(18, 18))
        self.addToolBar(tb)
        act = QAction(T("action.open"), self); act.setShortcut(QKeySequence.StandardKey.Open); act.triggered.connect(self.open_dialog); tb.addAction(act)
        act = QAction(T("action.refresh"), self); act.setShortcut(QKeySequence.StandardKey.Refresh); act.triggered.connect(self.reload_current); tb.addAction(act)
        tb.addSeparator()
        act = QAction(T("action.info"), self); act.setCheckable(True); act.toggled.connect(self.dock.setVisible); tb.addAction(act)
        self.info_action = act
        act = QAction(T("action.folder"), self); act.triggered.connect(lambda: paths.open_folder(self.current_path() or paths.DATA)); tb.addAction(act)
        tb.addSeparator()
        act = QAction(T("action.about"), self); act.triggered.connect(self._about); tb.addAction(act)

    def _build_menu(self):
        m = self.menuBar()
        fm = m.addMenu(T("menu.file"))
        a = QAction(T("action.open") + "…", self); a.setShortcut(QKeySequence.StandardKey.Open); a.triggered.connect(self.open_dialog); fm.addAction(a)
        a = QAction(T("action.close_tab"), self); a.setShortcut(QKeySequence.StandardKey.Close); a.triggered.connect(lambda: self.close_tab(self.tabs.currentIndex())); fm.addAction(a)
        fm.addSeparator()
        a = QAction(T("action.clear_recent"), self); a.triggered.connect(self.clear_recent); fm.addAction(a)
        a = QAction(T("action.quit"), self); a.setShortcut(QKeySequence.StandardKey.Quit); a.triggered.connect(self.close); fm.addAction(a)
        vm = m.addMenu(T("menu.view"))
        a = QAction(T("action.info"), self); a.setCheckable(True); a.toggled.connect(self.dock.setVisible); vm.addAction(a)
        a = QAction(T("action.zoom_in"), self); a.setShortcut(QKeySequence.StandardKey.ZoomIn); a.triggered.connect(lambda: self._zoom(1.15)); vm.addAction(a)
        a = QAction(T("action.zoom_out"), self); a.setShortcut(QKeySequence.StandardKey.ZoomOut); a.triggered.connect(lambda: self._zoom(1/1.15)); vm.addAction(a)
        hm = m.addMenu(T("menu.help"))
        a = QAction(T("action.about"), self); a.triggered.connect(self._about); hm.addAction(a)
        a = QAction("插件管理…", self); a.triggered.connect(self.open_plugin_manager); hm.addAction(a)
        a = QAction(T("lang.title"), self); a.triggered.connect(self.change_language); hm.addAction(a)
        a = QAction(T("action.clear_recent"), self); a.triggered.connect(lambda: (paths.clear_cache(), self.status_label.setText(T("status.ready")))); hm.addAction(a)

    def open_plugin_manager(self):
        from .plugin_manager_dialog import PluginManagerDialog
        PluginManagerDialog(self).exec()
        if self.current():
            self.reload_current()

    def _about(self):
        QMessageBox.about(self, T("app.title"),
                          f"<b>{T('app.title')} 0.2</b><br>"
                          f"{T('app.subtitle')}<br><br>"
                          "核心只内置 PDF / 文本 / 图片 / 音视频 / 压缩包；Office 等格式按需安装插件。")

    def change_language(self):
        from .language_dialog import LanguageDialog
        d = LanguageDialog(self, first_run=False)
        if d.exec() == QDialog.DialogCode.Accepted:
            i18n.set_language(d.selected)
            # app.py reads ui/language; keep the key in sync and restart so
            # every widget (including RTL layout) is rebuilt consistently.
            self.settings.setValue("ui/language", d.selected)
            self.settings.sync()
            QMessageBox.information(self, T("app.title"), T("lang.changed"))
            args = list(sys.argv[1:])
            if not getattr(sys, "frozen", False):
                args = [sys.argv[0]] + args
            if not QProcess.startDetached(sys.executable, args):
                QMessageBox.warning(self, T("app.title"), "无法自动重启，请手动关闭并重新打开 OmniView。")
            QApplication.quit()

    # ---------------------------------------------------------------- open
    def open_dialog(self):
        exts = set()
        row = self.cat_list.currentRow()
        if 0 <= row < len(CATEGORIES):
            exts = CATEGORIES[row][1] or set()
        if exts:
            filters = "支持的文件 (" + " ".join("*." + e for e in sorted(exts)) + ");;所有文件 (*.*)"
        else:
            filters = "所有支持的文件 (*.*)"
        path, _ = QFileDialog.getOpenFileName(self, T("action.open"), self._last_dir(), filters)
        if path:
            self.open_path(path)

    def open_last_folder(self):
        d = self._last_dir()
        path, _ = QFileDialog.getOpenFileName(self, T("action.open"), d, "All files (*.*)")
        if path:
            self.open_path(path)

    def _last_dir(self) -> str:
        last = self.settings.value("lastDir", "")
        return last if last and os.path.isdir(last) else os.path.expanduser("~")

    def open_path(self, path: str):
        path = os.path.abspath(path)
        if os.path.isdir(path):
            self.status_label.setText(T("status.ready"))
            self.settings.setValue("lastDir", path)
            return
        if not os.path.isfile(path):
            QMessageBox.warning(self, T("app.title"), f"{path}")
            return
        if path.lower().endswith(".ovp"):
            self._install_ovp(path)
            return
        self.settings.setValue("lastDir", os.path.dirname(path))
        # existing tab?
        for i in range(self.tabs.count()):
            w = self.tabs.widget(i)
            if isinstance(w, ViewerBase) and os.path.normcase(w.path) == os.path.normcase(path):
                self.tabs.setCurrentIndex(i)
                return
        try:
            viewer = self.create_viewer(path)
        except Exception as e:
            from .error_view import ErrorViewer
            viewer = ErrorViewer(path, e)
        if viewer is None:
            from .error_view import ErrorViewer
            viewer = ErrorViewer(path, "没有可用的解析器，也没有安装对应插件。")
        viewer.status_changed.connect(self.set_status)
        viewer.open_requested.connect(self.open_path)
        viewer.plugin_installed.connect(self.reload_current)
        idx = self.tabs.addTab(viewer, os.path.basename(path))
        self.tabs.setTabToolTip(idx, path)
        self.tabs.setCurrentIndex(idx)
        self.add_recent(path)
        self.set_status(f"{T('status.opened')} · {os.path.basename(path)}")

    def _install_ovp(self, path: str):
        try:
            meta = plugin_manager.install_zip(None, path)
            QMessageBox.information(self, "插件已安装",
                                    f"{meta.get('name')} ({meta.get('id')}) 已安装。\n"
                                    "现在可以打开对应格式的文件。")
        except Exception as e:
            QMessageBox.critical(self, "插件安装失败", str(e))

    def create_viewer(self, path: str) -> ViewerBase | None:
        from .viewers_doc import PdfViewer, RichTextViewer, TextViewer, MarkdownViewer, SheetViewer, PptxViewer, EpubViewer, ChunkedTextViewer
        from .viewers_media import ImageViewer, MediaViewer
        from .viewers_data import (ArchiveViewer, DatabaseViewer, Hdf5Viewer, ModelViewer, MailViewer,
                                   MeshViewer, CadViewer, GeoViewer, FontViewer, BinaryViewer)
        from .plugin_view import MissingPluginViewer
        from .error_view import ErrorViewer
        ext = _ext(path)
        app_id, kind = registry.resolve(os.path.basename(path))
        if ext == "ts" and _is_ts_video(path):
            app_id, kind = "media", "video"
        pid = plugin_manager.plugin_for(ext)
        if pid and not plugin_manager.installed(pid):
            return MissingPluginViewer(path, pid)
        if pid:
            plugin_manager.activate(pid)
            try:
                factory = plugin_manager.factory(pid)
            except Exception as e:
                return ErrorViewer(path, e, pid)
            if factory is not None:
                try:
                    viewer = factory(path, None)
                except Exception as e:
                    return ErrorViewer(path, e, pid)
                if not isinstance(viewer, ViewerBase):
                    return ErrorViewer(path, TypeError("插件的 create_viewer() 必须返回 ViewerBase 子类。"), pid)
                return viewer
        if kind == "unknown":
            return ErrorViewer(path, "没有注册该扩展名的解析器；可以安装插件或把 .ovp 拖入窗口。")
        text_like = kind in ("text", "tex", "code", "config", "log", "markdown") or ext in ("txt", "log", "md", "py", "js", "ts", "json", "csv", "sql", "yaml", "yml", "toml", "ini", "cfg")
        if text_like and os.path.getsize(path) > 8 * 1024 * 1024:
            return ChunkedTextViewer(path)
        if kind == "pdf":
            return PdfViewer(path)
        if kind in ("word", "slides") or ext == "odp":
            return PptxViewer(path) if kind == "slides" and ext == "pptx" else RichTextViewer(path)
        if kind == "markdown":
            return MarkdownViewer(path)
        if kind in ("text", "tex", "code", "html", "json", "xml", "yaml", "toml", "config", "log", "sql"):
            return RichTextViewer(path) if ext in ("html", "htm") else TextViewer(path)
        if kind == "notebook":
            return RichTextViewer(path)
        if kind == "sheet" or kind == "csv":
            return SheetViewer(path)
        if kind == "epub" or kind == "mobi":
            return EpubViewer(path)
        if app_id == "image":
            return ImageViewer(path)
        if kind in ("audio", "video"):
            return MediaViewer(path)
        if kind == "archive" or kind == "package":
            return ArchiveViewer(path)
        if kind in ("sqlite", "access", "dbf"):
            return DatabaseViewer(path)
        if kind == "hdf5":
            return Hdf5Viewer(path)
        if kind in ("onnx", "torch", "pickle", "tflite", "protobuf"):
            return ModelViewer(path)
        if kind in ("email", "msg", "mbox"):
            return MailViewer(path)
        if kind in ("dwg", "dxf"):
            return CadViewer(path)
        if kind == "model3d":
            return MeshViewer(path)
        if kind in ("shp", "shx", "kml", "geojson", "gpx"):
            return GeoViewer(path)
        if kind == "font":
            return FontViewer(path)
        return BinaryViewer(path)

    # ---------------------------------------------------------------- tabs
    def current(self):
        w = self.tabs.currentWidget()
        return w if isinstance(w, ViewerBase) else None

    def current_path(self):
        w = self.current()
        return w.path if w else None

    def close_tab(self, index):
        w = self.tabs.widget(index)
        if isinstance(w, ViewerBase):
            if not w.can_close():
                return
        self.tabs.removeTab(index)
        if w is not None:
            w.deleteLater()
        if self.tabs.count() == 0:
            self.tabs.addTab(self.welcome, T("app.title"))
            self.tabs.tabBar().setTabButton(0, self.tabs.tabBar().ButtonPosition.RightSide, None)

    def _tab_changed(self, index):
        w = self.current()
        if not w:
            self.info.clear()
            self.dock.setWindowTitle(T("action.info"))
            return
        self.dock.setWindowTitle(T("action.info") + " · " + os.path.basename(w.path))
        self._fill_info(w)
        self.set_status(f"{os.path.basename(w.path)} · {paths.human_size(os.path.getsize(w.path))}")

    def _fill_info(self, w):
        self.info.clear()
        base = {T("info.name"): os.path.basename(w.path), T("info.path"): w.path,
                T("info.size"): paths.human_size(os.path.getsize(w.path)),
                T("info.modified"): paths.human_time(os.path.getmtime(w.path))}
        for k, v in base.items():
            self.info.addTopLevelItem(QTreeWidgetItem([k, str(v)]))
        info = getattr(w, "info", None) or {}
        if isinstance(info, dict):
            for k, v in info.items():
                if isinstance(v, (dict, list)):
                    it = QTreeWidgetItem([str(k), ""])
                    self._fill_tree(it, v)
                    self.info.addTopLevelItem(it)
                    it.setExpanded(True)
                else:
                    self.info.addTopLevelItem(QTreeWidgetItem([str(k), str(v)]))

    def _fill_tree(self, item, value):
        if isinstance(value, dict):
            for k, v in value.items():
                ch = QTreeWidgetItem([str(k), "" if isinstance(v, (dict, list)) else str(v)])
                item.addChild(ch)
                if isinstance(v, (dict, list)):
                    self._fill_tree(ch, v)
        elif isinstance(value, list):
            for i, v in enumerate(value[:200]):
                ch = QTreeWidgetItem([f"[{i}]", "" if isinstance(v, (dict, list)) else str(v)])
                item.addChild(ch)
                if isinstance(v, (dict, list)):
                    self._fill_tree(ch, v)

    def reload_current(self):
        w = self.current()
        if w:
            path = w.path
            idx = self.tabs.currentIndex()
            self.close_tab(idx)
            self.open_path(path)

    def _zoom(self, factor):
        w = self.current()
        if w and hasattr(w, "zoom"):
            w.zoom(factor)

    def set_status(self, text: str):
        self.status_label.setText(text)

    # ---------------------------------------------------------------- recent
    def _load_recent(self):
        self.recent = self.settings.value("recent", [], type=list) or []
        self._refresh_recent()

    def _refresh_recent(self):
        self.recent_list.clear()
        for p in self.recent[:20]:
            if os.path.exists(p):
                it = QListWidgetItem(os.path.basename(p))
                it.setToolTip(p)
                it.setData(Qt.ItemDataRole.UserRole, p)
                self.recent_list.addItem(it)

    def add_recent(self, path: str):
        self.recent = [path] + [p for p in self.recent if os.path.normcase(p) != os.path.normcase(path)]
        self.recent = self.recent[:30]
        self.settings.setValue("recent", self.recent)
        self._refresh_recent()

    def clear_recent(self):
        self.recent = []
        self.settings.setValue("recent", [])
        self._refresh_recent()

    def _recent_open(self, item):
        p = item.data(Qt.ItemDataRole.UserRole)
        if p:
            self.open_path(p)

    def _category_clicked(self, item):
        self.status_label.setText(f'{T("status.filter")}: {item.text()}')

    # ---------------------------------------------------------------- drag/drop
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            p = url.toLocalFile()
            if p and os.path.isfile(p):
                self.open_path(p)
            elif p and os.path.isdir(p):
                self.settings.setValue("lastDir", p)
        event.acceptProposedAction()

    def closeEvent(self, event):
        for i in range(self.tabs.count()):
            w = self.tabs.widget(i)
            if isinstance(w, ViewerBase) and not w.can_close():
                event.ignore()
                return
        super().closeEvent(event)


