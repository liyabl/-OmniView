"""Dark native theme (QSS) for OmniView."""
from __future__ import annotations

from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import QApplication

BASE = "#0b1220"
PANEL = "#0f172a"
PANEL2 = "#111c31"
LINE = "#24344f"
TEXT = "#e6edf7"
MUTED = "#91a4bd"
ACCENT = "#7aa2ff"
ACCENT2 = "#5b7cfa"


def apply_theme(app: QApplication) -> None:
    app.setStyle("Fusion")
    pal = QPalette()
    pal.setColor(QPalette.ColorRole.Window, QColor(BASE))
    pal.setColor(QPalette.ColorRole.WindowText, QColor(TEXT))
    pal.setColor(QPalette.ColorRole.Base, QColor("#080e19"))
    pal.setColor(QPalette.ColorRole.AlternateBase, QColor(PANEL))
    pal.setColor(QPalette.ColorRole.Text, QColor(TEXT))
    pal.setColor(QPalette.ColorRole.Button, QColor(PANEL2))
    pal.setColor(QPalette.ColorRole.ButtonText, QColor(TEXT))
    pal.setColor(QPalette.ColorRole.Highlight, QColor(ACCENT2))
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#07111f"))
    pal.setColor(QPalette.ColorRole.ToolTipBase, QColor(PANEL2))
    pal.setColor(QPalette.ColorRole.ToolTipText, QColor(TEXT))
    app.setPalette(pal)
    app.setFont(QFont("Microsoft YaHei UI", 9))
    app.setStyleSheet(STYLE)


STYLE = f"""
QMainWindow, QDialog {{ background:{BASE}; color:{TEXT}; }}
QWidget {{ color:{TEXT}; font-family:'Microsoft YaHei UI','Microsoft YaHei','Segoe UI'; font-size:9pt; }}
QToolBar {{ background:{PANEL}; border:none; border-bottom:1px solid {LINE}; spacing:4px; padding:4px 8px; }}
QToolBar QToolButton {{ background:transparent; border:1px solid transparent; border-radius:6px; padding:5px 8px; color:{MUTED}; }}
QToolBar QToolButton:hover {{ background:#17253e; color:{TEXT}; }}
QToolBar QToolButton:pressed {{ background:#1d2e4a; }}
QToolBar QToolButton:disabled {{ color:#44546a; }}
QStatusBar {{ background:#080e19; color:{MUTED}; border-top:1px solid {LINE}; font-size:8pt; }}
QStatusBar::item {{ border:none; }}
QTabWidget::pane {{ border:none; background:{BASE}; }}
QTabBar {{ background:{PANEL}; }}
QTabBar::tab {{ background:{PANEL}; color:{MUTED}; border:1px solid {LINE}; border-bottom:none;
  padding:7px 14px; margin-right:2px; border-top-left-radius:7px; border-top-right-radius:7px; min-width:80px; }}
QTabBar::tab:selected {{ background:{BASE}; color:{TEXT}; border-color:{LINE}; }}
QTabBar::tab:hover {{ background:#17253e; color:{TEXT}; }}
QTabBar::close-button {{ image:none; subcontrol-position:right; }}
QListWidget, QTreeWidget, QTableWidget, QTableView {{ background:#080e19; alternate-background-color:#0c1526;
  border:1px solid {LINE}; border-radius:6px; gridline-color:#1b2a42; selection-background-color:#1e3a5f;
  selection-color:{TEXT}; outline:none; }}
QListWidget::item, QTreeWidget::item {{ padding:5px 7px; border-radius:4px; }}
QListWidget::item:selected, QTreeWidget::item:selected {{ background:#1e3a5f; color:{TEXT}; }}
QHeaderView::section {{ background:{PANEL2}; color:{MUTED}; border:none; border-right:1px solid {LINE};
  border-bottom:1px solid {LINE}; padding:5px 7px; font-weight:600; font-size:8pt; }}
QTableWidget::item {{ padding:3px 6px; }}
QPushButton {{ background:{PANEL2}; color:{TEXT}; border:1px solid {LINE}; border-radius:6px; padding:5px 12px; }}
QPushButton:hover {{ background:#17253e; border-color:#334a6b; }}
QPushButton:pressed {{ background:#1d2e4a; }}
QPushButton#primary {{ background:{ACCENT2}; color:#07111f; border:none; font-weight:700; }}
QPushButton#primary:hover {{ background:#6d8cff; }}
QLineEdit, QComboBox, QSpinBox {{ background:#080e19; border:1px solid {LINE}; border-radius:5px; padding:4px 7px; color:{TEXT}; }}
QLineEdit:focus, QComboBox:focus {{ border-color:{ACCENT}; }}
QComboBox::drop-down {{ border:none; width:18px; }}
QComboBox QAbstractItemView {{ background:{PANEL2}; border:1px solid {LINE}; selection-background-color:#1e3a5f; }}
QSlider::groove:horizontal {{ height:4px; background:#1b2a42; border-radius:2px; }}
QSlider::sub-page:horizontal {{ background:{ACCENT}; border-radius:2px; }}
QSlider::handle:horizontal {{ width:12px; margin:-5px 0; border-radius:6px; background:{ACCENT}; }}
QScrollBar:vertical {{ background:transparent; width:10px; margin:0; }}
QScrollBar::handle:vertical {{ background:#24344f; min-height:28px; border-radius:5px; }}
QScrollBar::handle:vertical:hover {{ background:#334a6b; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height:0; }}
QScrollBar:horizontal {{ background:transparent; height:10px; }}
QScrollBar::handle:horizontal {{ background:#24344f; min-width:28px; border-radius:5px; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width:0; }}
QMenu {{ background:{PANEL2}; border:1px solid {LINE}; padding:4px; }}
QMenu::item {{ padding:6px 24px 6px 12px; border-radius:4px; }}
QMenu::item:selected {{ background:#1e3a5f; }}
QMenu::separator {{ height:1px; background:{LINE}; margin:4px 6px; }}
QDockWidget {{ titlebar-close-icon:none; titlebar-normal-icon:none; color:{MUTED}; }}
QDockWidget::title {{ background:{PANEL}; padding:6px; border-bottom:1px solid {LINE}; }}
QSplitter::handle {{ background:{LINE}; width:1px; height:1px; }}
QLabel#muted {{ color:{MUTED}; }}
QLabel#title {{ font-size:15pt; font-weight:700; }}
QLabel#subtitle {{ color:{MUTED}; font-size:9pt; }}
QTextBrowser#docView {{ background:#ffffff; color:#1f2937; border:1px solid #1e293b; border-radius:4px;
  selection-background-color:#bfdbfe; selection-color:#111827; }}
QPlainTextEdit#codeView {{ background:#080e19; color:#dbe7f5; border:1px solid {LINE}; border-radius:5px;
  font-family:'Cascadia Code','Consolas',monospace; font-size:9.5pt; selection-background-color:#1e3a5f; }}
QToolButton#flat {{ background:transparent; border:none; color:{MUTED}; padding:4px 6px; border-radius:4px; }}
QToolButton#flat:hover {{ background:#17253e; color:{TEXT}; }}
QFrame#card {{ background:{PANEL}; border:1px solid {LINE}; border-radius:10px; }}
QProgressBar {{ border:1px solid {LINE}; border-radius:4px; background:#080e19; text-align:center; height:6px; }}
QProgressBar::chunk {{ background:{ACCENT}; border-radius:3px; }}
"""
