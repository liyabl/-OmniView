"""Native image and media viewers (Qt painting + QtMultimedia, CPU decode)."""
from __future__ import annotations

import os

from PySide6.QtCore import Qt, QUrl, QSize, QTimer
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPixmap, QMovie
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput, QMediaMetaData
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSlider,
                               QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QSizePolicy,
                               QScrollArea, QFrame, QMessageBox)

from .. import images, paths
from .common import ViewerBase


class ImageViewer(ViewerBase):
    def __init__(self, path: str, parent=None):
        super().__init__(path, parent)
        self._zoom = 1.0
        self._rot = 0
        self._fit = True
        self.pix = None
        self.movie = None
        self.canvas = QGraphicsView()
        self.canvas.setScene(QGraphicsScene(self))
        self.canvas.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.canvas.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.canvas.setStyleSheet("background:#141a26;border:none;")
        self.item = None
        self.root.addWidget(self.canvas, 1)
        self.tool_button("适合窗口", self.fit)
        self.tool_button("1:1", self.actual)
        self.tool_button("放大", lambda: self.zoom(1.2))
        self.tool_button("缩小", lambda: self.zoom(1 / 1.2))
        self.tool_button("旋转", self.rotate)
        self.spacer()
        self.info_label = self.label("", "muted")
        self.load()

    def load(self):
        ext = os.path.splitext(self.path)[1].lower().lstrip(".")
        try:
            if ext == "gif":
                self.movie = QMovie(self.path)
                self.movie.setCacheMode(QMovie.CacheMode.CacheAll)
                self.movie.frameChanged.connect(self._movie_frame)
                self.movie.start()
                self.pix = self.movie.currentPixmap()
                self._set_pixmap(self.pix)
            else:
                img = images.load_image(self.path)
                if img.isNull():
                    raise RuntimeError("无法解码图像")
                self.pix = QPixmap.fromImage(img)
                self._set_pixmap(self.pix)
            self.info = images.image_info(self.path)
            self.info_label.setText(f"{self.info.get('format','')} · {self.pix.width()}×{self.pix.height()}")
            self.set_status(f"{self.info.get('format','')} · {self.pix.width()}×{self.pix.height()} · {paths.human_size(os.path.getsize(self.path))}")
            QTimer.singleShot(30, self.fit)
        except Exception as e:
            self.canvas.scene().clear()
            item = self.canvas.scene().addText(f"无法显示图像\n{e}")
            item.setDefaultTextColor(QColor("#fca5a5"))
            self.canvas.setSceneRect(item.boundingRect())

    def _set_pixmap(self, pix):
        scene = self.canvas.scene()
        scene.clear()
        self.item = QGraphicsPixmapItem(pix)
        self.item.setTransformationMode(Qt.TransformationMode.SmoothTransformation)
        scene.addItem(self.item)
        scene.setSceneRect(self.item.boundingRect())

    def _movie_frame(self, _):
        if self.movie:
            self.pix = self.movie.currentPixmap()
            self._set_pixmap(self.pix)
            self._apply()

    def showEvent(self, event):
        super().showEvent(event)
        if self._fit:
            QTimer.singleShot(30, self.fit)

    def fit(self):
        self._fit = True
        self.canvas.resetTransform()
        self.canvas.fitInView(self.canvas.scene().sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def actual(self):
        self._fit = False
        self._zoom = 1.0
        self._apply()

    def zoom(self, factor):
        self._fit = False
        self._zoom = max(0.05, min(12, self._zoom * factor))
        self._apply()

    def rotate(self):
        self._rot = (self._rot + 90) % 360
        self._apply()

    def _apply(self):
        if self._fit:
            self.canvas.fitInView(self.canvas.scene().sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        else:
            self.canvas.resetTransform()
            self.canvas.rotate(self._rot)
            self.canvas.scale(self._zoom, self._zoom)

    def wheelEvent(self, event):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.zoom(1.15 if event.angleDelta().y() > 0 else 1 / 1.15)
            return
        super().wheelEvent(event)


class MediaViewer(ViewerBase):
    def __init__(self, path: str, parent=None):
        super().__init__(path, parent)
        self.player = QMediaPlayer(self)
        self.audio = QAudioOutput(self)
        self.player.setAudioOutput(self.audio)
        self.video = QVideoWidget()
        self.video.setStyleSheet("background:#000;")
        self.player.setVideoOutput(self.video)
        self.root.addWidget(self.video, 1)
        self.poster = QLabel("音频")
        self.poster.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.poster.setStyleSheet("background:#080e19;color:#f6ad55;font-size:26px;")
        self.root.addWidget(self.poster, 1)
        self.poster.hide()
        self.play_btn = self.tool_button("播放", self.toggle, "空格")
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, 0)
        self.slider.sliderMoved.connect(self.seek)
        self.toolbar.addWidget(self.slider, 1)
        self.time_label = self.label("0:00 / 0:00")
        self.vol = QSlider(Qt.Orientation.Horizontal)
        self.vol.setRange(0, 100); self.vol.setValue(80); self.vol.setFixedWidth(90)
        self.vol.valueChanged.connect(lambda v: self.audio.setVolume(v / 100))
        self.toolbar.addWidget(self.vol)
        self.player.positionChanged.connect(self._pos)
        self.player.durationChanged.connect(self._dur)
        self.player.playbackStateChanged.connect(self._state)
        self.player.errorOccurred.connect(self._err)
        self.player.setSource(QUrl.fromLocalFile(path))
        if self._is_audio():
            self.video.hide()
            self.poster.show()
        else:
            self.poster.hide()
            self.video.show()
        self.player.pause()
        self.set_status(f"{os.path.splitext(path)[1].upper().lstrip('.')} · {paths.human_size(os.path.getsize(path))}")

    def _is_audio(self):
        ext = os.path.splitext(self.path)[1].lower()
        return ext in (".mp3", ".aac", ".m4a", ".flac", ".wav", ".ogg", ".opus", ".aiff", ".wma")

    def toggle(self):
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    def seek(self, ms):
        self.player.setPosition(ms)

    def _fmt(self, ms):
        s = max(0, int(ms / 1000))
        return f"{s//60}:{s%60:02d}"

    def _pos(self, ms):
        self.slider.setValue(ms)
        self.time_label.setText(f"{self._fmt(ms)} / {self._fmt(self.player.duration())}")

    def _dur(self, ms):
        self.slider.setRange(0, max(0, ms))

    def _state(self, state):
        self.play_btn.setText("暂停" if state == QMediaPlayer.PlaybackState.PlayingState else "播放")

    def _err(self, err, string):
        if err != QMediaPlayer.Error.NoError:
            self.set_status(f"播放失败：{string}")
