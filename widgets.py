"""
The YiJing — Navigating Change
widgets.py — Shared widget classes

Imported by both yijing_main.py and journal.py.
No circular dependencies.

Version 2.8.0
GNU GPL v3
"""

from PySide6.QtWidgets import QWidget
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineSettings
from PySide6.QtCore import Qt


# ══════════════════════════════════════════════════════════════════════════════
# ZOOM-ENABLED WEB VIEW
# QWebEngineView — setZoomFactor scales entire page including all CSS font sizes
# Ctrl+wheel zoom works correctly on body text, headings, and paragraph classes
# ══════════════════════════════════════════════════════════════════════════════

class ZoomView(QWebEngineView):
    """WebEngine browser with Ctrl+wheel zoom.
    setZoomFactor() scales the entire rendered page uniformly."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._zoom = 1.0
        s = self.settings()
        s.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, False)
        s.setAttribute(
            QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, False)

    def wheelEvent(self, event):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if event.angleDelta().y() > 0:
                self._zoom = min(self._zoom + 0.1, 3.0)
            else:
                self._zoom = max(self._zoom - 0.1, 0.5)
            self.setZoomFactor(self._zoom)
            event.accept()
        else:
            super().wheelEvent(event)

    def zoomIn(self, range=1):
        self._zoom = min(self._zoom + 0.1, 3.0)
        self.setZoomFactor(self._zoom)

    def zoomOut(self, range=1):
        self._zoom = max(self._zoom - 0.1, 0.5)
        self.setZoomFactor(self._zoom)
