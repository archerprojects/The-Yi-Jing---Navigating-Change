"""
The YiJing — Navigating Change
yarrow_animation.py — Animated yarrow stalk casting widget

Imported lazily by cast.py. Never imported at module level.
Self-contained: owns all narration text, animation logic, and QPainter rendering.
Emits line_cast(int, int, list) and cast_done() — identical signature to coin panel.

Version 2.8.51
GNU GPL v3
"""

import random

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QSizePolicy,
)
from PySide6.QtCore import Qt, QTimer, Signal, QRect, QPointF
from PySide6.QtGui import (
    QPainter, QColor, QPen, QFont, QFontMetrics,
    QLinearGradient, QRadialGradient, QPainterPath, QBrush,
    QPainterPathStroker,
)


# ══════════════════════════════════════════════════════════════════════════════
# NARRATION TEXT
# ══════════════════════════════════════════════════════════════════════════════

_NARRATION = {
    "divide": (
        "Concentrate on your question.\n\n"
        "Click anywhere to divide the stalks into two groups."
    ),
    "sorting":  "Counting in groups of four…",
    "round_done": "Round {round} complete — {count} stalks set aside.",
    "line_done":  "Line {line} cast: {name}\n\nClick to continue.",
    "complete":   "All six lines cast. The hexagram is complete.",
}

_LINE_NAMES = {
    6: ("⚋×  Old Yin — Moving",    "#8b1a1a"),
    7: ("⚊   Young Yang — Stable", "#515150"),
    8: ("⚋   Young Yin — Stable",  "#515150"),
    9: ("⚊○  Old Yang — Moving",   "#8b4513"),
}

# ── Palette ───────────────────────────────────────────────────────────────────
_C_HIGHLIGHT = QColor(0xE8, 0xC8, 0x80)
_C_TEXT      = QColor(0x8B, 0x1A, 0x1A)
_C_STATUS    = QColor(0x33, 0x33, 0x33)


# ══════════════════════════════════════════════════════════════════════════════
# CAST LOGIC
# ══════════════════════════════════════════════════════════════════════════════

def _cast_line():
    """
    Three-round yarrow sort. Returns (line_value, [c1,c2,c3], (r1,r2,r3)).
    Probabilities: 6→1/16, 7→5/16, 8→7/16, 9→3/16.
    """
    def round1():
        east = random.randint(1, 47)
        west = 48 - east
        re = east % 4 or 4
        rw = west % 4 or 4
        total = 1 + re + rw
        return (3 if total == 5 else 2), total, east, west, re, rw

    def round23(pool):
        avail = max(2, pool - 1)
        east  = random.randint(1, max(1, avail - 1))
        west  = avail - east
        re    = east % 4 or 4
        rw    = west % 4 or 4
        total = 1 + re + rw
        return (3 if total == 4 else 2), total, east, west, re, rw

    c1, t1, e1, w1, re1, rw1 = round1()
    pool2 = 49 - t1
    c2, t2, e2, w2, re2, rw2 = round23(pool2)
    pool3 = pool2 - t2
    c3, t3, e3, w3, re3, rw3 = round23(pool3)

    line_val = c1 + c2 + c3
    r1 = (c1, t1, e1, w1, re1, rw1, 49)
    r2 = (c2, t2, e2, w2, re2, rw2, pool2)
    r3 = (c3, t3, e3, w3, re3, rw3, pool3)
    return line_val, [c1, c2, c3], (r1, r2, r3)


# ══════════════════════════════════════════════════════════════════════════════
# STALK RENDERING
# ══════════════════════════════════════════════════════════════════════════════

def _draw_bundle(painter, cx, top, count, highlight=False, horizontal=False, max_h=None):
    """
    Draw a bundle of `count` naturally crooked stalks centred at cx.
    Returns bounding QRect.
    """
    if count <= 0:
        return QRect(cx - 20, top, 40, 10)

    # Bundle geometry
    stalk_h  = int(min(160, max(70, 75 + count * 1.6)))
    if max_h is not None:
        stalk_h = min(stalk_h, max_h)
    visible  = min(count, 20)
    spread   = min(visible * 3, 48)
    step     = spread / max(visible - 1, 1)
    left_x   = cx - spread // 2

    painter.save()

    # Soft ground shadow to seat the bundle
    painter.setPen(Qt.NoPen)
    sh = QRadialGradient(QPointF(cx, top + stalk_h + 5), spread * 0.9)
    sh.setColorAt(0.0, QColor(0, 0, 0, 50))
    sh.setColorAt(1.0, QColor(0, 0, 0, 0))
    painter.setBrush(QBrush(sh))
    painter.drawEllipse(QPointF(cx, top + stalk_h + 5), spread * 0.85, 6)

    for i in range(visible):
        x = left_x + int(i * step)
        # Seed mixes index and count so stalks differ but stay stable per frame
        _draw_one_stalk(painter, x, top, stalk_h, highlight,
                        seed=i * 13 + count)

    # Horizontal finger stalk across top of bundle
    if horizontal:
        _draw_horizontal_stalk(painter, cx, top - 5, 36)

    painter.restore()
    return QRect(left_x - 8, top - 12, spread + 16, stalk_h + 18)


def _draw_one_stalk(painter, x, top, h, highlight=False, seed=0):
    """Single naturally crooked stalk: bezier spine, cylindrical gradient,
    node rings, rounded tips. All variation is seeded → stable per repaint."""
    rng = random.Random(seed * 7919 + 17)
    w = 5  # stalk width

    dh   = rng.uniform(-6, 4)     # bottom-edge variance
    dtop = rng.uniform(-4, 3)     # top-edge variance
    tone = rng.uniform(-16, 16)   # per-stalk tone shift
    top2, h2 = top + dtop, h + dh

    # Crooked spine: cubic bezier with lateral kinks at 1/3 and 2/3 height
    k1    = rng.uniform(-3.5, 3.5)
    k2    = rng.uniform(-3.5, 3.5)
    drift = rng.uniform(-2.0, 2.0)            # tip drift
    spine = QPainterPath(QPointF(x, top2 + h2))            # bottom
    spine.cubicTo(QPointF(x + k1, top2 + h2 * 0.66),
                  QPointF(x + k2, top2 + h2 * 0.33),
                  QPointF(x + drift, top2))                 # top

    stroker = QPainterPathStroker()
    stroker.setWidth(w)
    stroker.setCapStyle(Qt.RoundCap)
    body = stroker.createStroke(spine)

    def _c(r, g, b):
        return QColor(max(0, min(255, int(r + tone))),
                      max(0, min(255, int(g + tone))),
                      max(0, min(255, int(b + tone * 0.6))))

    # Gradient: left dark → center light → right dark (cylindrical)
    grad = QLinearGradient(QPointF(x - w, top2), QPointF(x + w, top2))
    if highlight:
        grad.setColorAt(0.0,  _c(0xA0, 0x70, 0x28))
        grad.setColorAt(0.3,  _c(0xF0, 0xD0, 0x80))
        grad.setColorAt(0.5,  _c(0xFF, 0xF0, 0xB0))
        grad.setColorAt(0.7,  _c(0xF0, 0xD0, 0x80))
        grad.setColorAt(1.0,  _c(0xA0, 0x70, 0x28))
    else:
        grad.setColorAt(0.0,  _c(0x7A, 0x4A, 0x18))
        grad.setColorAt(0.25, _c(0xC8, 0x86, 0x40))
        grad.setColorAt(0.5,  _c(0xEE, 0xB8, 0x68))
        grad.setColorAt(0.75, _c(0xC8, 0x86, 0x40))
        grad.setColorAt(1.0,  _c(0x7A, 0x4A, 0x18))

    painter.setPen(Qt.NoPen)
    painter.fillPath(body, QBrush(grad))

    # Node rings: short ticks following the curved spine
    painter.setPen(QPen(QColor(0x6B, 0x42, 0x16, 75), 1))
    for frac in ([0.35, 0.7] if h2 > 95 else [0.55]):
        t = min(0.95, max(0.05, frac + rng.uniform(-0.08, 0.08)))
        pt = spine.pointAtPercent(1.0 - t)    # percent runs bottom→top
        painter.drawLine(QPointF(pt.x() - w / 2 + 0.8, pt.y()),
                         QPointF(pt.x() + w / 2 - 0.8, pt.y()))

    # Tip highlight — small sheen at spine top
    tippt = spine.pointAtPercent(1.0)
    tip_grad = QRadialGradient(tippt, w)
    tip_grad.setColorAt(0.0, QColor(0xFF, 0xF0, 0xD0, 190))
    tip_grad.setColorAt(1.0, QColor(0xC8, 0x86, 0x40, 0))
    painter.setBrush(QBrush(tip_grad))
    painter.setPen(Qt.NoPen)
    painter.drawEllipse(tippt, w * 0.7, 2.0)


def _draw_horizontal_stalk(painter, cx, y, half_len):
    """Single horizontal stalk — finger hold indicator. Same natural
    treatment: gently bowed spine, rounded ends, node ring."""
    rng = random.Random(4242)                  # fixed seed → stable shape
    w = 5
    bow = rng.uniform(1.0, 2.0)                # slight vertical bow
    spine = QPainterPath(QPointF(cx - half_len, y + 2))
    spine.cubicTo(QPointF(cx - half_len * 0.33, y + 2 - bow),
                  QPointF(cx + half_len * 0.33, y + 2 + bow),
                  QPointF(cx + half_len, y + 2))
    stroker = QPainterPathStroker()
    stroker.setWidth(w)
    stroker.setCapStyle(Qt.RoundCap)
    body = stroker.createStroke(spine)

    grad = QLinearGradient(QPointF(cx, y - w), QPointF(cx, y + w))
    grad.setColorAt(0.0, QColor(0x7A, 0x4A, 0x18))
    grad.setColorAt(0.3, QColor(0xEE, 0xB8, 0x68))
    grad.setColorAt(0.7, QColor(0xEE, 0xB8, 0x68))
    grad.setColorAt(1.0, QColor(0x7A, 0x4A, 0x18))
    painter.setPen(Qt.NoPen)
    painter.fillPath(body, QBrush(grad))

    # single node ring near one end
    pt = spine.pointAtPercent(0.3)
    painter.setPen(QPen(QColor(0x6B, 0x42, 0x16, 75), 1))
    painter.drawLine(QPointF(pt.x(), pt.y() - w / 2 + 0.8),
                     QPointF(pt.x(), pt.y() + w / 2 - 0.8))


# ══════════════════════════════════════════════════════════════════════════════
# ANIMATION WIDGET
# ══════════════════════════════════════════════════════════════════════════════

class YarrowAnimWidget(QWidget):
    """
    QPainter-rendered yarrow stalk animation.
    Three-round sort sequence per line, 6 lines per reading.
    Emits line_cast(line_idx, value, counts) and cast_done().
    """

    line_cast = Signal(int, int, list)
    cast_done = Signal()
    started   = Signal()

    _IDLE       = "idle"
    _DIVIDE     = "divide"
    _SORTING    = "sorting"
    _ROUND_DONE = "round_done"
    _LINE_DONE  = "line_done"
    _COMPLETE   = "complete"

    # ── Layout zones ──────────────────────────────────────────────────────────
    _PAD       = 16     # frame padding
    _RES_W     = 104    # right results column width
    _BUNDLE_DX = 36     # working-bundle centre offset from left pad

    _INFO = (
        "The Yarrow Stalk Method — a more ancient method than coins. "
        "Using the coin toss, every line type is equally likely. "
        "Sorting yarrow stalks weights them unequally. Early diviners "
        "understood the cosmos as a moving yin line (Old Yin) being rare, "
        "just 1 in 16. This weighting is the reason behind the different "
        "methods. Full probability table in Study \u25b8 Practice. "
        "Click the stalks to begin."
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumHeight(220)
        self.setCursor(Qt.PointingHandCursor)
        self.setMouseTracking(True)

        self._lines      = []
        self._counts     = []
        self._round_data = None
        self._round_idx  = 0
        self._line_val   = 0
        self._step       = self._IDLE

        self._anim_timer  = QTimer(self)
        self._anim_timer.timeout.connect(self._anim_tick)
        self._anim_phase  = 0
        self._speed_ms    = 250

        self._main_count    = 49
        self._left_count    = 0
        self._right_count   = 0
        self._finger        = [0, 0, 0]
        self._result_counts = [0, 0, 0]
        self._hover         = False
        self._clickable_rects = []

    def set_speed(self, ms):
        self._speed_ms = ms
        if self._anim_timer.isActive():
            self._anim_timer.setInterval(ms)

    def get_lines(self):
        return list(self._lines)

    def reset(self):
        self._anim_timer.stop()
        self._lines         = []
        self._counts        = []
        self._round_data    = None
        self._round_idx     = 0
        self._line_val      = 0
        self._main_count    = 49
        self._left_count    = 0
        self._right_count   = 0
        self._finger        = [0, 0, 0]
        self._result_counts = [0, 0, 0]
        self._step          = self._IDLE
        self.update()

    # ── Interaction ──────────────────────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._on_click()

    def mouseMoveEvent(self, event):
        in_hot = any(r.contains(event.pos()) for r in self._clickable_rects)
        if in_hot != self._hover:
            self._hover = in_hot
            self.update()

    def _on_click(self):
        if self._step == self._IDLE:
            self.started.emit()
            self._begin_line()
        elif self._step == self._DIVIDE:
            self._do_divide()
        elif self._step == self._ROUND_DONE:
            self._next_round()
        elif self._step == self._LINE_DONE:
            self._accept_line()

    # ── Cast logic ───────────────────────────────────────────────────────────

    def _begin_line(self):
        self._counts        = []
        self._round_idx     = 0
        self._finger        = [0, 0, 0]
        self._result_counts = [0, 0, 0]
        self._main_count    = 49
        self._left_count    = 0
        self._right_count   = 0
        self._line_val, self._counts, self._round_data = _cast_line()
        self._step = self._DIVIDE
        self.update()

    def _do_divide(self):
        rd = self._round_data[self._round_idx]
        _, _, east, west, _, _, pool = rd
        self._main_count  = 0
        self._left_count  = east
        self._right_count = west
        self._step        = self._SORTING
        self._anim_phase  = 0
        self._anim_timer.start(self._speed_ms)
        self.update()

    def _anim_tick(self):
        rd = self._round_data[self._round_idx]
        c_val, t_val, east, west, rem_east, rem_west, pool = rd
        phase = self._anim_phase

        if phase == 0:
            self._right_count -= 1
            self._finger[self._round_idx] = 1
            self._anim_phase = 1
        elif phase == 1:
            if self._left_count > rem_east:
                self._left_count -= min(4, self._left_count - rem_east)
            else:
                self._anim_phase = 2
        elif phase == 2:
            self._finger[self._round_idx] += rem_east
            self._left_count = 0
            self._anim_phase = 3
        elif phase == 3:
            if self._right_count > rem_west:
                self._right_count -= min(4, self._right_count - rem_west)
            else:
                self._anim_phase = 4
        elif phase == 4:
            self._finger[self._round_idx] += rem_west
            self._right_count = 0
            self._anim_phase = 5
        elif phase == 5:
            self._result_counts[self._round_idx] = self._finger[self._round_idx]
            self._main_count = pool - t_val
            self._anim_timer.stop()
            self._step       = self._ROUND_DONE
            self._anim_phase = 0

        self.update()

    def _next_round(self):
        self._round_idx += 1
        if self._round_idx >= 3:
            self._step = self._LINE_DONE
            self.update()
            return
        self._left_count  = 0
        self._right_count = 0
        self._step        = self._DIVIDE
        self.update()

    def _accept_line(self):
        line_idx = len(self._lines)
        self._lines.append(self._line_val)
        self.line_cast.emit(line_idx, self._line_val, self._counts)

        if len(self._lines) == 6:
            self._step = self._COMPLETE
            self.update()
            self.cast_done.emit()
        else:
            self._step          = self._IDLE
            self._main_count    = 49
            self._left_count    = 0
            self._right_count   = 0
            self._finger        = [0, 0, 0]
            self._result_counts = [0, 0, 0]
            self._round_idx     = 0
            self.update()

    # ── Painting ─────────────────────────────────────────────────────────────

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        self._clickable_rects = []
        w, h = self.width(), self.height()

        dispatch = {
            self._IDLE:       self._draw_idle,
            self._DIVIDE:     self._draw_divide,
            self._SORTING:    self._draw_sorting,
            self._ROUND_DONE: self._draw_round_done,
            self._LINE_DONE:  self._draw_line_done,
            self._COMPLETE:   self._draw_complete,
        }
        dispatch.get(self._step, lambda p,w,h: None)(painter, w, h)
        painter.end()

    def _label(self, painter, text, cx, y, color=None, bold=False, size=11):
        painter.save()
        f = QFont("Georgia, serif")
        f.setPointSize(size)
        f.setBold(bold)
        painter.setFont(f)
        painter.setPen(color or _C_TEXT)
        fm = QFontMetrics(f)
        painter.drawText(cx - fm.horizontalAdvance(text) // 2, y, text)
        painter.restore()

    def _label_left(self, painter, text, x, y, color=None, bold=False, size=11):
        painter.save()
        f = QFont("Georgia, serif")
        f.setPointSize(size)
        f.setBold(bold)
        painter.setFont(f)
        painter.setPen(color or _C_TEXT)
        painter.drawText(x, y, text)
        painter.restore()

    # ── Zone helpers ───────────────────────────────────────────────────────────
    def _bundle_cx(self):
        return self._PAD + self._BUNDLE_DX

    def _left_w(self, w):
        return max(140, w - self._RES_W - 3 * self._PAD)

    def _res_cx(self, w):
        return w - self._RES_W // 2 - self._PAD

    def _status_left(self, painter, text, y, w):
        """Narration/info text in the LEFT zone — width-limited so it never
        reaches the right-hand results column."""
        painter.save()
        f = QFont("Georgia, serif")
        f.setPointSize(10)
        painter.setFont(f)
        painter.setPen(_C_STATUS)
        painter.drawText(QRect(self._PAD, y, self._left_w(w), self.height() - y - 6),
                         Qt.AlignTop | Qt.AlignLeft | Qt.TextWordWrap, text)
        painter.restore()

    def _draw_results(self, painter, w):
        """R1/R2/R3 set-aside stalks, stacked vertically on the RIGHT."""
        cx = self._res_cx(w)
        y  = self._PAD + 8
        for i in range(3):
            cnt = self._result_counts[i]
            if cnt > 0:
                r = _draw_bundle(painter, cx, y, cnt, horizontal=True, max_h=52)
                self._label(painter, f"R{i+1}: {cnt}", cx, r.bottom() + 12, size=9)
                y = r.bottom() + 26

    # ── State renderers ──────────────────────────────────────────────────────
    def _draw_idle(self, painter, w, h):
        cx  = self._bundle_cx()
        top = self._PAD
        r   = _draw_bundle(painter, cx, top, 49, highlight=self._hover)
        self._clickable_rects = [QRect(0, 0, w, h)]
        self._label(painter, "49", cx, r.bottom() + 16, bold=True)
        if len(self._lines) == 0:
            self._status_left(painter, self._INFO, r.bottom() + 32, w)
        else:
            line_n = len(self._lines) + 1
            self._status_left(painter, f"Line {line_n} of 6 — " + _NARRATION["divide"],
                              r.bottom() + 32, w)

    def _draw_divide(self, painter, w, h):
        cx  = self._bundle_cx()
        top = self._PAD
        r   = _draw_bundle(painter, cx, top, self._main_count, highlight=self._hover)
        self._clickable_rects = [QRect(0, 0, w, h)]
        self._label(painter, str(self._main_count), cx, r.bottom() + 16, bold=True)
        rn = self._round_idx + 1
        self._status_left(painter, f"Round {rn} of 3 — " + _NARRATION["divide"],
                          r.bottom() + 32, w)
        self._draw_results(painter, w)

    def _draw_sorting(self, painter, w, h):
        top  = self._PAD
        lx   = self._bundle_cx()
        rx   = lx + 70
        bott = top + 80
        if self._left_count > 0:
            rl = _draw_bundle(painter, lx, top, self._left_count)
            self._label(painter, str(self._left_count), lx, rl.bottom() + 14)
            bott = max(bott, rl.bottom() + 14)
        if self._main_count > 0:
            rm = _draw_bundle(painter, lx, top, self._main_count)
            self._label(painter, str(self._main_count), lx, rm.bottom() + 14)
            bott = max(bott, rm.bottom() + 14)
        if self._right_count > 0:
            has_f = self._finger[self._round_idx] > 0 and self._anim_phase >= 1
            rr = _draw_bundle(painter, rx, top, self._right_count, horizontal=has_f)
            self._label(painter, str(self._right_count), rx, rr.bottom() + 14)
            bott = max(bott, rr.bottom() + 14)
        self._status_left(painter, _NARRATION["sorting"], bott + 16, w)
        self._draw_results(painter, w)

    def _draw_round_done(self, painter, w, h):
        top  = self._PAD
        cx   = self._bundle_cx()
        bott = top + 80
        if self._main_count > 0:
            rm = _draw_bundle(painter, cx, top, self._main_count)
            self._label(painter, str(self._main_count), cx, rm.bottom() + 14)
            bott = rm.bottom() + 14
        rn  = self._round_idx + 1
        cnt = self._result_counts[self._round_idx]
        msg = _NARRATION["round_done"].format(round=rn, count=cnt)
        msg += ("\n\nClick to continue to round " + str(rn + 1) + "."
                if rn < 3 else "\n\nClick to see the line result.")
        self._status_left(painter, msg, bott + 16, w)
        self._draw_results(painter, w)
        self._clickable_rects = [QRect(0, 0, w, h)]

    def _draw_line_done(self, painter, w, h):
        top = self._PAD
        x   = self._PAD
        name, color = _LINE_NAMES.get(self._line_val, ("Unknown", "#515150"))
        line_n = len(self._lines) + 1

        painter.save()
        f = QFont(); f.setPointSize(26)
        painter.setFont(f)
        painter.setPen(QColor(color))
        painter.drawText(x, top + 34, name.split()[0])
        painter.restore()

        self._label_left(painter, name, x, top + 60, color=QColor(color), bold=True, size=12)
        c = self._counts
        self._label_left(painter, f"Counts: {c[0]} + {c[1]} + {c[2]} = {self._line_val}",
                         x, top + 80, color=QColor(0x51, 0x51, 0x50), size=10)

        msg = _NARRATION["line_done"].format(line=line_n, name=name.strip())
        msg += (f"\n\nClick to cast Line {line_n + 1}." if line_n < 6
                else "\n\nClick to complete the reading.")
        self._status_left(painter, msg, top + 98, w)
        self._draw_results(painter, w)
        self._clickable_rects = [QRect(0, 0, w, h)]

    def _draw_complete(self, painter, w, h):
        x = self._PAD
        self._label_left(painter, "Reading Complete", x, 34, bold=True, size=13)
        lines_text = ""
        for i, v in enumerate(self._lines):
            name, _ = _LINE_NAMES.get(v, ("?", "#515150"))
            lines_text += f"Line {i+1}: {name.strip()}\n"
        self._status_left(painter, lines_text, 52, w)


# ══════════════════════════════════════════════════════════════════════════════
# YARROW PANEL — wrapper for cast.py
# ══════════════════════════════════════════════════════════════════════════════

class YarrowPanel(QWidget):
    """
    Thin wrapper hosting YarrowAnimWidget + speed control.
    Drop-in replacement for old YarrowPanel in cast.py.
    Signals: line_cast(int, int, list), cast_done().
    """

    line_cast = Signal(int, int, list)
    cast_done = Signal()

    _SPEEDS = [("Slow", 600), ("Med", 250), ("Fast", 80)]

    def __init__(self, hex_model, parent=None):
        super().__init__(parent)
        self.hex = hex_model
        self._build()

    def _build(self):
        vl = QVBoxLayout(self)
        vl.setContentsMargins(4, 4, 4, 4)
        vl.setSpacing(4)

        self._anim = YarrowAnimWidget()
        self._anim.line_cast.connect(self._on_line_cast)
        self._anim.cast_done.connect(self._on_cast_done)
        vl.addWidget(self._anim, 1)

        speed_row = QHBoxLayout()
        lbl = QLabel("Speed:")
        lbl.setStyleSheet("font-size:10px;color:#888;background:transparent;")
        speed_row.addWidget(lbl)

        self._speed_slider = QSlider(Qt.Horizontal)
        self._speed_slider.setMinimum(0)
        self._speed_slider.setMaximum(2)
        self._speed_slider.setValue(1)
        self._speed_slider.setTickPosition(QSlider.TicksBelow)
        self._speed_slider.setTickInterval(1)
        self._speed_slider.setFixedWidth(80)
        self._speed_slider.valueChanged.connect(self._on_speed_change)
        speed_row.addWidget(self._speed_slider)

        for label, _ in self._SPEEDS:
            l = QLabel(label)
            l.setStyleSheet("font-size:9px;color:#aaa;background:transparent;")
            speed_row.addWidget(l)

        speed_row.addStretch()
        vl.addLayout(speed_row)

    def _on_speed_change(self, idx):
        _, ms = self._SPEEDS[idx]
        self._anim.set_speed(ms)

    def _on_line_cast(self, line_idx, value, counts):
        self.line_cast.emit(line_idx, value, counts)

    def _on_cast_done(self):
        self.cast_done.emit()

    def get_lines(self):
        return self._anim.get_lines()

    def reset(self):
        self._anim.reset()
