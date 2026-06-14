#!/usr/bin/env python3
"""
wheel.py — The Hexagram Wheel (Study screen).

A circular compass of all 64 hexagrams (King Wen order): number ring and
six-line figure per wedge, 易經 hub, fixed pointer at 12 o'clock.

Interaction:
  • click a wedge          → selected(hex_id)
  • drag / flick the wheel → spins with momentum, snaps to a wedge,
                             then landed(hex_id)
  • spin() (Spin button)   → random momentum spin, same landing path
  • hover                  → hovered(hex_id) and wedge highlight

Rendering: the static wheel is painted once to a cached pixmap and rotated
per frame; hub and pointer are drawn unrotated on top. Cheap at 60 fps.

This module deliberately imports only hexfig (line data). Hexagram
names/characters are passed in by the caller to avoid circular imports.
"""

import math
import random

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QTimer, QPointF, Signal, QRectF
from PySide6.QtGui import (
    QPainter, QPixmap, QColor, QPen, QFont, QFontMetrics, QBrush,
    QPolygonF, QPainterPath, QRadialGradient,
)

import hexfig

_WEDGE = 360.0 / 64.0          # 5.625° per hexagram


class WheelWidget(QWidget):
    hovered  = Signal(int)     # cursor over a wedge (hex_id, 0 = none)
    selected = Signal(int)     # wedge clicked
    landed   = Signal(int)     # spin finished on this hexagram

    def __init__(self, hex_names, hex_chars, parent=None):
        super().__init__(parent)
        self._names = hex_names
        self._chars = hex_chars
        self._angle = 0.0          # wheel rotation, degrees
        self._vel = 0.0            # angular velocity, deg/tick
        self._hover_hid = 0
        self._base = None          # cached static wheel pixmap
        self._base_size = 0

        # geometry ratios (of half-size)
        self._r_out, self._r_num, self._r_sym, self._r_hub = 0.97, 0.91, 0.80, 0.42

        self._drag = False
        self._drag_last_a = 0.0
        self._drag_samples = []    # (ms, angle) for release velocity
        self._snapping = False
        self._snap_target = 0.0

        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._tick)

        self.setMouseTracking(True)
        self.setMinimumSize(420, 420)

    # ------------------------------------------------------------ public
    def spin(self):
        """Random momentum spin (Spin button)."""
        self._snapping = False
        self._vel = random.uniform(14.0, 22.0) * random.choice((-1.0, 1.0))
        self._timer.start()

    def current_hex(self):
        """Hexagram currently under the pointer (12 o'clock)."""
        i = int(round(-self._angle / _WEDGE)) % 64
        return i + 1

    # -------------------------------------------------------- geometry
    def _radius_px(self):
        return min(self.width(), self.height()) / 2.0

    def _hex_at(self, pos):
        """Hexagram wedge under widget-space point, or 0."""
        half = self._radius_px()
        dx, dy = pos.x() - self.width() / 2.0, pos.y() - self.height() / 2.0
        r = math.hypot(dx, dy)
        if not (self._r_hub * half < r < self._r_out * half):
            return 0
        a = math.degrees(math.atan2(dy, dx))           # screen angle
        i = int(round((a + 90.0 - self._angle) / _WEDGE)) % 64
        return i + 1

    def _pointer_angle_of(self, pos):
        dx, dy = pos.x() - self.width() / 2.0, pos.y() - self.height() / 2.0
        return math.degrees(math.atan2(dy, dx))

    # ---------------------------------------------------------- physics
    def _tick(self):
        if self._snapping:
            diff = self._snap_target - self._angle
            if abs(diff) < 0.15:
                self._angle = self._snap_target
                self._timer.stop()
                self._snapping = False
                self.update()
                self.landed.emit(self.current_hex())
                return
            self._angle += diff * 0.18
        else:
            self._angle += self._vel
            self._vel *= 0.975
            if abs(self._vel) < 0.25:
                # decelerated — ease onto the nearest wedge centre
                self._snap_target = round(self._angle / _WEDGE) * _WEDGE
                self._snapping = True
        self.update()

    # ------------------------------------------------------------ mouse
    def mousePressEvent(self, ev):
        if ev.button() != Qt.LeftButton:
            return
        self._timer.stop()
        self._snapping = False
        self._vel = 0.0
        self._drag = True
        self._moved = 0.0
        self._drag_last_a = self._pointer_angle_of(ev.position())
        self._drag_samples = [(ev.timestamp(), self._angle)]

    def mouseMoveEvent(self, ev):
        if self._drag:
            a = self._pointer_angle_of(ev.position())
            d = a - self._drag_last_a
            while d > 180.0:
                d -= 360.0
            while d < -180.0:
                d += 360.0
            self._angle += d
            self._moved += abs(d)
            self._drag_last_a = a
            self._drag_samples.append((ev.timestamp(), self._angle))
            if len(self._drag_samples) > 6:
                self._drag_samples.pop(0)
            self.update()
        else:
            hid = self._hex_at(ev.position())
            if hid != self._hover_hid:
                self._hover_hid = hid
                self.hovered.emit(hid)
                self.update()

    def mouseReleaseEvent(self, ev):
        if ev.button() != Qt.LeftButton or not self._drag:
            return
        self._drag = False
        if self._moved < 2.0:                       # a click, not a drag
            hid = self._hex_at(ev.position())
            if hid:
                self.selected.emit(hid)
            return
        # flick: velocity from recent samples
        if len(self._drag_samples) >= 2:
            t0, a0 = self._drag_samples[0]
            t1, a1 = self._drag_samples[-1]
            dt = max(t1 - t0, 1)                    # ms
            self._vel = (a1 - a0) / dt * 16.0       # deg per 16 ms tick
        if abs(self._vel) > 0.4:
            self._timer.start()
        else:                                       # gentle release: snap
            self._snap_target = round(self._angle / _WEDGE) * _WEDGE
            self._snapping = True
            self._timer.start()

    def leaveEvent(self, ev):
        if self._hover_hid:
            self._hover_hid = 0
            self.hovered.emit(0)
            self.update()

    # ---------------------------------------------------------- painting
    def resizeEvent(self, ev):
        self._base = None                            # re-render cache
        super().resizeEvent(ev)

    def paintEvent(self, ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        cx, cy = self.width() / 2.0, self.height() / 2.0
        size = int(self._radius_px() * 2)
        if self._base is None or self._base_size != size:
            self._render_base(size)

        # rotated wheel
        p.save()
        p.translate(cx, cy)
        p.rotate(self._angle)
        p.drawPixmap(int(-size / 2), int(-size / 2), self._base)
        p.restore()

        half = self._radius_px()

        # hover highlight wedge (drawn in screen space)
        if self._hover_hid and not self._drag and not self._timer.isActive():
            i = self._hover_hid - 1
            start = -(i * _WEDGE + self._angle + 90.0 + _WEDGE / 2.0)
            path = QPainterPath()
            path.moveTo(QPointF(cx, cy))
            rect = QRectF(cx - half * self._r_out, cy - half * self._r_out,
                          half * self._r_out * 2, half * self._r_out * 2)
            path.arcTo(rect, start, _WEDGE)
            path.closeSubpath()
            inner = QPainterPath()
            inner.addEllipse(QPointF(cx, cy), half * self._r_hub, half * self._r_hub)
            p.fillPath(path.subtracted(inner), QColor(212, 175, 55, 60))

        # hub (unrotated)
        hub_r = half * self._r_hub
        p.setBrush(QColor("#f5f0e6"))
        p.setPen(QPen(QColor("#5a4632"), 2))
        p.drawEllipse(QPointF(cx, cy), hub_r, hub_r)
        p.setPen(QColor("#3a2c1a"))
        f = QFont("AR PL UKai CN")
        f.setPointSizeF(max(18.0, hub_r * 0.42))
        f.setBold(True)
        p.setFont(f)
        fm = QFontMetrics(p.font())
        t = "易經"
        p.drawText(QPointF(cx - fm.horizontalAdvance(t) / 2.0,
                           cy + fm.ascent() / 2.0 - 4), t)

        # pointer at 12 o'clock
        tip_y = cy - half * self._r_out
        p.setBrush(QColor("#8b1a1a"))
        p.setPen(Qt.NoPen)
        p.drawPolygon(QPolygonF([
            QPointF(cx, tip_y + half * 0.055),
            QPointF(cx - half * 0.025, tip_y - half * 0.01),
            QPointF(cx + half * 0.025, tip_y - half * 0.01)]))
        p.end()

    def _render_base(self, size):
        """Render the static wheel (rings, spokes, numbers, figures)."""
        self._base = QPixmap(size, size)
        self._base.fill(Qt.transparent)
        self._base_size = size
        p = QPainter(self._base)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        c = size / 2.0
        half = c
        r_out = half * self._r_out
        r_num = half * self._r_num
        r_sym = half * self._r_sym
        r_hub = half * self._r_hub

        # parchment disc
        disc = QRadialGradient(QPointF(c, c), r_out)
        disc.setColorAt(0.0, QColor("#f7f2e8"))
        disc.setColorAt(1.0, QColor("#efe6d2"))
        p.setBrush(QBrush(disc))
        p.setPen(QPen(QColor("#5a4632"), 2))
        p.drawEllipse(QPointF(c, c), r_out, r_out)
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor("#5a4632"), 1.4))
        p.drawEllipse(QPointF(c, c), r_num - half * 0.045, r_num - half * 0.045)
        p.drawEllipse(QPointF(c, c), r_sym - half * 0.065, r_sym - half * 0.065)

        # spokes (on wedge boundaries)
        p.setPen(QPen(QColor(0x5a, 0x46, 0x32, 140), 1))
        for i in range(64):
            a = math.radians(i * _WEDGE - 90.0 + _WEDGE / 2.0)
            p.drawLine(QPointF(c + r_hub * math.cos(a), c + r_hub * math.sin(a)),
                       QPointF(c + r_out * math.cos(a), c + r_out * math.sin(a)))

        num_font = QFont("Sans")
        num_font.setPointSizeF(max(7.0, half * 0.026))
        num_font.setBold(True)
        line_w = half * 0.048
        line_gap = half * 0.0115

        for i in range(64):
            hid = i + 1
            ang = i * _WEDGE - 90.0
            a = math.radians(ang)

            # number
            p.save()
            p.translate(c + r_num * math.cos(a), c + r_num * math.sin(a))
            p.rotate(ang + 90.0)
            p.setPen(QColor("#3a2c1a"))
            p.setFont(num_font)
            fm = QFontMetrics(p.font())
            s = str(hid)
            p.drawText(QPointF(-fm.horizontalAdvance(s) / 2.0,
                               fm.ascent() / 2.0 - 1), s)
            p.restore()

            # six-line figure, base toward hub
            p.save()
            p.translate(c + r_sym * math.cos(a), c + r_sym * math.sin(a))
            p.rotate(ang + 90.0)
            p.setPen(QPen(QColor("#2a1f12"), max(1.6, half * 0.0068)))
            for li, lt in enumerate(hexfig.hex_lines(hid)):   # bottom→top
                y = (2.5 - li) * line_gap                     # top line at rim
                if lt == 7:                                   # yang — solid
                    p.drawLine(QPointF(-line_w / 2, y), QPointF(line_w / 2, y))
                else:                                         # yin — broken
                    p.drawLine(QPointF(-line_w / 2, y), QPointF(-line_w * 0.12, y))
                    p.drawLine(QPointF(line_w * 0.12, y), QPointF(line_w / 2, y))
            p.restore()
        p.end()
