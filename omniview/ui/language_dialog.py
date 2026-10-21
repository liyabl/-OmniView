"""First-run language picker."""
from __future__ import annotations

from PySide6.QtCore import Qt, QLocale
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                               QListWidget, QListWidgetItem, QPushButton)

from .. import i18n


class LanguageDialog(QDialog):
    def __init__(self, parent=None, first_run=True):
        super().__init__(parent)
        self.setWindowTitle("OmniView · Language / 语言")
        self.resize(560, 520)
        self.selected = self._system_default()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 20, 24, 18)
        title = QLabel("Choose your language / 选择界面语言")
        title.setStyleSheet("font-size:16pt;font-weight:700;")
        lay.addWidget(title)
        sub = QLabel("UN official languages and languages with 30M+ speakers.\n"
                     "File content is always shown in its original language.")
        sub.setStyleSheet("color:#91a4bd;font-size:9.5pt;")
        lay.addWidget(sub)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search languages…")
        self.search.textChanged.connect(self._filter)
        lay.addWidget(self.search)
        self.list = QListWidget()
        self.list.setAlternatingRowColors(True)
        lay.addWidget(self.list, 1)
        self.info = QLabel("")
        self.info.setStyleSheet("color:#5f738e;font-size:9pt;")
        lay.addWidget(self.info)
        row = QHBoxLayout()
        row.addStretch(1)
        self.ok = QPushButton("Continue")
        self.ok.setObjectName("primary")
        self.ok.setFixedHeight(34)
        self.ok.clicked.connect(self._accept)
        row.addWidget(self.ok)
        lay.addLayout(row)
        self._populate()
        self.list.currentItemChanged.connect(self._changed)
        self.list.itemDoubleClicked.connect(lambda _: self._accept())

    def _system_default(self):
        code = QLocale.system().name().split("_")[0].lower()
        return code if any(l["code"] == code for l in i18n.languages()) else "en"

    def _populate(self):
        self.list.clear()
        for l in i18n.languages():
            has = i18n.catalog_exists(l["code"])
            label = f'{l["native"]}  ·  {l["english"]}'
            if l.get("un"):
                label += "  ·  UN"
            if not has:
                label += "  ·  English fallback"
            it = QListWidgetItem(label)
            it.setData(Qt.ItemDataRole.UserRole, l["code"])
            if l["code"] == self.selected:
                self.list.setCurrentItem(it)
            self.list.addItem(it)

    def _filter(self, text):
        q = text.strip().lower()
        for i in range(self.list.count()):
            it = self.list.item(i)
            it.setHidden(bool(q) and q not in it.text().lower())

    def _changed(self, cur, _prev):
        if not cur:
            return
        code = cur.data(Qt.ItemDataRole.UserRole)
        self.selected = code
        l = i18n.language(code)
        if i18n.catalog_exists(code):
            self.info.setText(f'{l["native"]} — translation included')
        else:
            self.info.setText(f'{l["native"]} — catalog not yet contributed; English UI will be used. '
                              f'You can add {code}.json under %LOCALAPPDATA%\\\\OmniView\\\\locales.')

    def _accept(self):
        self.accept()

    @staticmethod
    def ask(parent=None) -> str | None:
        d = LanguageDialog(parent)
        if d.exec() == QDialog.DialogCode.Accepted:
            return d.selected
        return None
