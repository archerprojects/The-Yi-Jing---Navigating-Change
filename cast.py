"""
The YiJing — Navigating Change
cast.py — Casting panel, coin and yarrow widgets

Imported lazily by yijing_main.py — never at module level.
LineWidget imported directly by HexDisplay.

Version 2.8.44
GNU GPL v3
"""

import os, sys, re, base64, random, time

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QStackedWidget, QFrame,
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QPainter, QPen, QColor, QPixmap

def _resource(rel):
    base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel)


# ══════════════════════════════════════════════════════════════════════════════
# COIN IMAGE LOADER
# Loads GIF frames from coin_images.py (base64 strings).
# Image data: Copyright (C) 1999-2006 Stephen M. Gava (pyChing), GPL-2.0
# ══════════════════════════════════════════════════════════════════════════════

def load_coin_pixmaps():
    """
    Load coin animation frames from coin_images.py (bundled as data file).
    Read as a file and parse the base64 strings — matches the --add-data
    bundling pattern (the module is a data file, not an importable module).
    Returns list of QPixmaps: frames 0-13 spinning, then yin, yang, blank.
    """
    try:
        path = _resource("coin_images.py")
        with open(path) as f:
            content = f.read()
        frames = re.findall(r'"([A-Za-z0-9+/=]{40,})"', content)
        pixmaps = []
        for data in frames:
            raw = base64.b64decode(data.strip())
            pm  = QPixmap()
            pm.loadFromData(raw, 'GIF')
            pixmaps.append(pm)
        return pixmaps
    except Exception:
        return []


# ══════════════════════════════════════════════════════════════════════════════
# LINE WIDGET — fixed-size QPainter hex line
# ══════════════════════════════════════════════════════════════════════════════

class LineWidget(QWidget):
    LINE_W = 160
    LINE_H = 22
    GAP    = 26

    def __init__(self, parent=None):
        super().__init__(parent)
        self._value = None
        self.setFixedSize(self.LINE_W, self.LINE_H)

    def set_value(self, v):
        self._value = v
        self.update()

    def clear(self):
        self._value = None
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.LINE_W, self.LINE_H
        bar_h = 10
        y = (h - bar_h) // 2
        v = self._value

        if v is None:
            p.setPen(QPen(QColor("#cccccc"), 1, Qt.DashLine))
            p.drawLine(4, h//2, w-4, h//2)
            return

        is_moving = v in (6, 9)
        is_yang   = v in (7, 9)
        color = QColor("#cc2200") if is_moving else QColor("#1a1a1a")
        p.setPen(Qt.NoPen)
        p.setBrush(color)

        if is_yang:
            p.drawRect(2, y, w-4, bar_h)
        else:
            half = (w - self.GAP) // 2
            p.drawRect(2, y, half, bar_h)
            p.drawRect(w - half - 2, y, half, bar_h)

        if is_moving:
            cx, cy, r = w + 12, h//2, 5
            if v == 9:
                p.setPen(QPen(color, 2))
                p.setBrush(Qt.NoBrush)
                p.drawEllipse(cx-r, cy-r, 2*r, 2*r)
            else:
                p.setPen(QPen(color, 2))
                p.drawLine(cx-r, cy-r, cx+r, cy+r)
                p.drawLine(cx+r, cy-r, cx-r, cy+r)

        p.end()


# ══════════════════════════════════════════════════════════════════════════════
# COIN WIDGET
# ══════════════════════════════════════════════════════════════════════════════

class CoinWidget(QLabel):
    def __init__(self, pixmaps, parent=None):
        super().__init__(parent)
        self._pixmaps = pixmaps
        self.setFixedSize(74, 74)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("background: transparent;")
        self._show(0)

    def _show(self, frame):
        if frame < len(self._pixmaps):
            self.setPixmap(self._pixmaps[frame].scaled(
                66, 66, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def show_frame(self, frame):
        self._show(frame)

    def show_result(self, value):
        # value 2=tails→frame 12, value 3=heads→frame 13
        frame = 12 if value == 2 else 13
        self._show(min(frame, len(self._pixmaps) - 1))

    def show_rest(self):
        self._show(0)


# ══════════════════════════════════════════════════════════════════════════════
# COIN CAST PANEL
# ══════════════════════════════════════════════════════════════════════════════

class _CoinCastPanel(QWidget):
    line_cast = Signal(int, int, list)
    cast_done = Signal()

    def __init__(self, hex_model, parent=None):
        super().__init__(parent)
        self.hex               = hex_model
        self._pixmaps          = load_coin_pixmaps()
        self._lines            = []
        self._coin_vals        = []
        self._animating        = False
        self._anim_frame       = 0
        self._pending_result   = None
        self._cast_all_pending = []

        self._timer = QTimer()
        self._timer.timeout.connect(self._anim_step)
        self._build()

    def _build(self):
        vl = QVBoxLayout(self)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(8)

        # Coin row
        coin_row = QHBoxLayout()
        coin_row.setSpacing(10)
        self._coins = []
        for _ in range(3):
            cw = CoinWidget(self._pixmaps)
            coin_row.addWidget(cw)
            self._coins.append(cw)
        coin_row.addStretch()
        vl.addLayout(coin_row)

        # Line results grid
        grid = QGridLayout()
        grid.setSpacing(3)
        self._line_widgets = []
        self._line_labels  = []
        for i in range(6):
            display_row = 5 - i
            lbl = QLabel(f"Line {i+1}")
            lbl.setStyleSheet("font-size:11px; color:#888888; background:transparent;")
            lbl.setFixedWidth(52)
            lw = LineWidget()
            grid.addWidget(lbl, display_row, 0)
            grid.addWidget(lw,  display_row, 1)
            self._line_widgets.append(lw)
            self._line_labels.append(lbl)
        vl.addLayout(grid)

        # Status
        self._status = QLabel("Cast a line to begin")
        self._status.setStyleSheet("font-size:11px; color:#555555; background:transparent;")
        vl.addWidget(self._status)

        # Buttons
        self._btn_line = QPushButton("Cast Line 1 of 6")
        self._btn_line.setStyleSheet(self._btn_style(True))
        self._btn_line.clicked.connect(self._cast_next_line)
        vl.addWidget(self._btn_line)

        self._btn_all = QPushButton("Cast All 6 Lines")
        self._btn_all.setStyleSheet(self._btn_style(False))
        self._btn_all.clicked.connect(self._cast_all)
        vl.addWidget(self._btn_all)

        vl.addStretch()

    def _btn_style(self, primary=True):
        if primary:
            return ("QPushButton{background:#515150;color:#fff;border:none;"
                    "border-radius:5px;padding:7px 14px;font-size:12px;font-weight:bold;}"
                    "QPushButton:hover{background:#3a3a39;}"
                    "QPushButton:disabled{background:#aaaaaa;}")
        return ("QPushButton{background:#eeeeec;color:#333;border:1px solid #c0c0bc;"
                "border-radius:5px;padding:7px 14px;font-size:12px;}"
                "QPushButton:hover{background:#dddddb;}"
                "QPushButton:disabled{color:#aaaaaa;}")

    def reset(self):
        self._lines            = []
        self._animating        = False
        self._cast_all_pending = []
        self._timer.stop()
        for cw in self._coins:
            cw.show_rest()
        for lw in self._line_widgets:
            lw.clear()
        for lbl in self._line_labels:
            lbl.setStyleSheet("font-size:11px; color:#888888; background:transparent;")
        self._btn_line.setText("Cast Line 1 of 6")
        self._btn_line.setVisible(True)
        self._btn_line.setEnabled(True)
        self._btn_all.setEnabled(True)
        self._status.setText("Cast a line to begin")
        try:
            self._btn_line.clicked.disconnect()
        except Exception:
            pass
        self._btn_line.clicked.connect(self._cast_next_line)

    def _cast_next_line(self):
        if self._animating or len(self._lines) >= 6:
            return
        self._btn_line.setEnabled(False)
        self._btn_all.setEnabled(False)
        self._start_animation()

    def _cast_all(self):
        if self._animating:
            return
        remaining = list(range(len(self._lines), 6))
        if not remaining:
            return
        self._btn_line.setEnabled(False)
        self._btn_all.setEnabled(False)
        self._cast_all_pending = remaining[1:]
        self._start_animation()

    def _start_animation(self):
        line_num = len(self._lines)
        self._status.setText(f"Casting line {line_num + 1} of 6 …")
        self._animating    = True
        self._anim_frame   = 0
        from PySide6.QtGui import QCursor
        pos  = QCursor.pos()
        seed = int(time.time() * 1000) ^ (pos.x() << 16) ^ pos.y()
        random.seed(seed)
        self._coin_vals      = [random.choice([2, 3]) for _ in range(3)]
        self._pending_result = sum(self._coin_vals)
        self._timer.start(20)

    def _anim_step(self):
        frame = self._anim_frame % 14
        for cw in self._coins:
            cw.show_frame(frame)
        self._anim_frame += 1
        if self._anim_frame >= 28:
            self._timer.stop()
            self._finish_line()

    def _finish_line(self):
        for i, cw in enumerate(self._coins):
            cw.show_result(self._coin_vals[i])

        line_idx = len(self._lines)
        val      = self._pending_result
        self._lines.append(val)
        self._line_widgets[line_idx].set_value(val)

        lbl = self._line_labels[line_idx]
        if val in (6, 9):
            lbl.setStyleSheet("font-size:11px; color:#cc2200; font-weight:bold; background:transparent;")
        else:
            lbl.setStyleSheet("font-size:11px; color:#515150; background:transparent;")

        self._animating = False
        self.line_cast.emit(line_idx, val, self._coin_vals)

        if len(self._lines) == 6:
            self._complete()
        elif self._cast_all_pending:
            self._cast_all_pending.pop(0)
            QTimer.singleShot(800, self._start_animation)
        else:
            n = len(self._lines) + 1
            self._btn_line.setText(f"Cast Line {n} of 6")
            self._btn_line.setEnabled(True)
            self._btn_all.setEnabled(True)
            self._status.setText(f"Line {len(self._lines)} cast. Cast line {n} when ready.")

    def _complete(self):
        self._status.setText("All 6 lines cast.")
        self._btn_line.setVisible(False)
        self._btn_all.setEnabled(False)
        for cw in self._coins:
            cw.show_rest()
        self.cast_done.emit()

    def get_lines(self):
        return list(self._lines)


# ══════════════════════════════════════════════════════════════════════════════
# YARROW PANEL — lazy import
# ══════════════════════════════════════════════════════════════════════════════

def _get_yarrow_panel_class():
    from yarrow_animation import YarrowPanel as _YP
    return _YP


# ══════════════════════════════════════════════════════════════════════════════
# CAST PANEL — outer wrapper with mode toggle and alias/moon header
# ══════════════════════════════════════════════════════════════════════════════

class CastPanel(QWidget):
    line_cast   = Signal(int, int, list)
    cast_done   = Signal()
    new_reading = Signal()
    method_requested = Signal(int)   # toggle clicked; MainWindow decides whether to gate

    _TOGGLE_ON = (
        "QPushButton{background:#515150;color:#fff;border:none;"
        "border-radius:4px;padding:5px 14px;font-size:12px;font-weight:bold;}"
    )
    _TOGGLE_OFF = (
        "QPushButton{background:#eeeeec;color:#555555;"
        "border:1px solid #c0c0bc;border-radius:4px;"
        "padding:5px 14px;font-size:12px;}"
        "QPushButton:hover{background:#dddddb;}"
    )

    def __init__(self, hex_model, parent=None):
        super().__init__(parent)
        self.hex       = hex_model
        self._is_guest = True
        self._build()

    def set_user(self, username):
        self._is_guest = (username == "Guest")

    def set_alias(self, name):
        self._alias_lbl.setText(name if name != "Guest" else "")

    def _build(self):
        vl = QVBoxLayout(self)
        vl.setContentsMargins(8, 4, 8, 4)
        vl.setSpacing(4)

        # ── Header: title | stretch | alias | moon ───────────────────────────
        header_row = QHBoxLayout()
        header_row.setSpacing(6)

        self._title_lbl = QLabel("Cast by Coin")
        self._title_lbl.setStyleSheet(
            "font-size:13px;font-weight:bold;color:#1a1a1a;background:transparent;")
        header_row.addWidget(self._title_lbl)
        header_row.addStretch()

        self._alias_lbl = QLabel("")
        self._alias_lbl.setStyleSheet(
            "font-size:26px;color:#777777;font-style:italic;background:transparent;")
        self._alias_lbl.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        header_row.addWidget(self._alias_lbl)
        header_row.addStretch()

        from journal import moon_phase as _moon_phase
        _phase = _moon_phase()
        _parts = _phase.split(" ", 1)
        _icon  = _parts[0] if _parts else _phase
        _name  = _parts[1] if len(_parts) > 1 else ""

        moon_col = QVBoxLayout()
        moon_col.setSpacing(0)
        moon_col.setContentsMargins(0, 0, 0, 0)

        self._moon_icon_lbl = QLabel(_icon)
        self._moon_icon_lbl.setStyleSheet("font-size:49px;background:transparent;")
        self._moon_icon_lbl.setAlignment(Qt.AlignHCenter)
        self._moon_icon_lbl.setToolTip(_phase)
        moon_col.addWidget(self._moon_icon_lbl)

        self._moon_name_lbl = QLabel(_name)
        self._moon_name_lbl.setStyleSheet(
            "font-size:10px;color:#777777;background:transparent;")
        self._moon_name_lbl.setAlignment(Qt.AlignHCenter)
        moon_col.addWidget(self._moon_name_lbl)

        header_row.addLayout(moon_col)
        vl.addLayout(header_row)

        # ── Mode toggle ───────────────────────────────────────────────────────
        toggle_row = QHBoxLayout()
        self._coin_btn   = QPushButton("🪙  Coin")
        self._yarrow_btn = QPushButton("𝌭  Yarrow")
        self._coin_btn.setStyleSheet(self._TOGGLE_ON)
        self._yarrow_btn.setStyleSheet(self._TOGGLE_OFF)
        self._coin_btn.clicked.connect(lambda: self.method_requested.emit(0))
        self._yarrow_btn.clicked.connect(lambda: self.method_requested.emit(1))
        toggle_row.addWidget(self._coin_btn)
        toggle_row.addWidget(self._yarrow_btn)
        toggle_row.addStretch()
        vl.addLayout(toggle_row)

        # ── Stacked cast panels ───────────────────────────────────────────────
        self._stack = QStackedWidget()
        self._coin_panel   = _CoinCastPanel(self.hex)
        YarrowPanel        = _get_yarrow_panel_class()
        self._yarrow_panel = YarrowPanel(self.hex)

        self._coin_panel.line_cast.connect(self.line_cast)
        self._coin_panel.cast_done.connect(self._on_cast_done)
        self._yarrow_panel.line_cast.connect(self._forward_yarrow_line)
        self._yarrow_panel.cast_done.connect(self._on_cast_done)

        self._stack.addWidget(self._coin_panel)    # index 0
        self._stack.addWidget(self._yarrow_panel)  # index 1
        vl.addWidget(self._stack, 1)

    def _forward_yarrow_line(self, line_idx, value, counts):
        """Explicit slot — signal-to-signal forwarding fails silently on X11."""
        self.line_cast.emit(line_idx, value, counts)

    def _on_cast_done(self):
        self.cast_done.emit()

    def current_method(self):
        return self._stack.currentIndex()

    def apply_method(self, index):
        self._stack.setCurrentIndex(index)
        if index == 0:
            self._title_lbl.setText("Cast by Coin")
            self._coin_btn.setStyleSheet(self._TOGGLE_ON)
            self._yarrow_btn.setStyleSheet(self._TOGGLE_OFF)
        else:
            self._title_lbl.setText("Yarrow Stalk Ritual")
            self._coin_btn.setStyleSheet(self._TOGGLE_OFF)
            self._yarrow_btn.setStyleSheet(self._TOGGLE_ON)

    def reset(self):
        self._coin_panel.reset()
        self._yarrow_panel.reset()

    def get_lines(self):
        if self._stack.currentIndex() == 0:
            return self._coin_panel.get_lines()
        return self._yarrow_panel.get_lines()
