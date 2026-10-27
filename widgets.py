"""
The YiJing — Navigating Change
widgets.py — Shared widget classes

Imported by both yijing_main.py and journal.py.
No circular dependencies.

Version 1.0.2 — Wednesday 28 October 2026
GNU GPL v3
"""

from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineSettings, QWebEngineNavigationRequest
from PySide6.QtCore import Qt
from PySide6.QtGui import QDesktopServices


def keep_window(owner, win):
    """Hold a parentless top-level window until it closes, then free it.
    Without a reference Python can collect the window and Qt destroys it;
    a parent would keep it alive but pin it above its owner on Linux WMs."""
    win.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
    held = owner.__dict__.setdefault("_held_windows", set())
    held.add(win)
    win.destroyed.connect(lambda *_: held.discard(win))


# ══════════════════════════════════════════════════════════════════════════════
# ZOOM-ENABLED WEB VIEW
# QWebEngineView — setZoomFactor scales entire page including all CSS font sizes
# Ctrl+wheel zoom works correctly on body text, headings, and paragraph classes
# ══════════════════════════════════════════════════════════════════════════════

_EXTERNAL = ("http", "https", "mailto")


class ZoomView(QWebEngineView):
    """WebEngine browser with Ctrl+wheel zoom.
    setZoomFactor() scales the entire rendered page uniformly.
    Web and mail links open in the user's own browser / mail app (through the
    desktop portal inside the Flatpak); in-app links navigate as usual.
    Other navigationRequested handlers must not accept() what they don't own —
    accepting is the default, and an explicit accept() would undo the reject here."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.page().navigationRequested.connect(self._external_links)
        self._zoom = 1.0
        s = self.settings()
        s.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, False)
        s.setAttribute(
            QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, False)

    def _external_links(self, request):
        url = request.url()
        if (url.scheme() in _EXTERNAL and request.navigationType() ==
                QWebEngineNavigationRequest.NavigationType.LinkClickedNavigation):
            request.reject()
            QDesktopServices.openUrl(url)

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
