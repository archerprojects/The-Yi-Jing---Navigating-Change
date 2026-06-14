"""
The YiJing — Navigating Change
journal.py — Version 2.8.12
GNU GPL v3
"""

import os, sys, re, json
from datetime import date, datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QLineEdit, QFrame, QScrollArea, QMessageBox,
    QDialog, QFormLayout, QSplitter, QMenu,
)
from PySide6.QtCore import Qt, Signal, QByteArray
from PySide6.QtGui import QColor, QPixmap, QPainter
from PySide6.QtSvg import QSvgRenderer
import hexfig


def _hex_names():
    try:
        import yijing_main
        return yijing_main.HEX_NAMES
    except Exception:
        return {}

def _hex_chars():
    try:
        import yijing_main
        return yijing_main.HEX_CHARS
    except Exception:
        return {}


def _yijing_dir():
    d = os.path.join(os.path.expanduser("~"), ".local", "share", "yijing")
    os.makedirs(d, exist_ok=True)
    return d

def _users_path():
    return os.path.join(_yijing_dir(), "users.json")

def _journal_path(username="Default"):
    safe = re.sub(r'[^a-zA-Z0-9_-]', '_', username)
    return os.path.join(_yijing_dir(), f"journal_{safe}.json")

def _journal_backup_path(username="Default"):
    safe = re.sub(r'[^a-zA-Z0-9_-]', '_', username)
    return os.path.join(_yijing_dir(), f"journal_{safe}_backup.json")


def load_users():
    """Return list of user aliases. Empty list if none created yet."""
    try:
        with open(_users_path(), encoding="utf-8") as f:
            users = json.load(f)
        if not isinstance(users, list):
            return []
        # Filter out the old "Default" placeholder if present
        return [u for u in users if u != "Default"]
    except Exception:
        return []

def save_users(users):
    with open(_users_path(), "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

def add_user(alias):
    users = load_users()
    if alias and alias not in users:
        users.append(alias)
        save_users(users)
    return users


def load_journal(username="Default"):
    try:
        with open(_journal_path(username), encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_journal(entries, username="Default"):
    path   = _journal_path(username)
    backup = _journal_backup_path(username)
    data   = json.dumps(entries, ensure_ascii=False, indent=2)
    with open(path, "w", encoding="utf-8") as f:
        f.write(data)
    with open(backup, "w", encoding="utf-8") as f:
        f.write(data)

def delete_journal_entry(entry_id, username="Default"):
    entries = [e for e in load_journal(username) if e.get("id") != entry_id]
    save_journal(entries, username)
    return entries

def auto_save_entry(hex_model, question, username, moment_data):
    HEX_NAMES = _hex_names()
    HEX_CHARS = _hex_chars()
    now    = datetime.now()
    hid    = hex_model.hex_id()
    name   = HEX_NAMES.get(hid, f"Hexagram {hid}")
    moving = [i+1 for i, v in enumerate(hex_model.lines) if v in (6,9)]
    rid    = hex_model.relating_id() if hex_model.has_moving() else None
    rname  = HEX_NAMES.get(rid, "") if rid else ""
    entry = {
        "id":            now.isoformat(),
        "date":          now.strftime("%Y-%m-%d"),
        "time":          now.strftime("%H:%M"),
        "moon":          moon_phase(),
        "hexagram":      hid,
        "hexagram_name": name,
        "hexagram_char": HEX_CHARS.get(hid, ""),
        "moving_lines":  moving,
        "relating":      rid,
        "relating_name": rname,
        "relating_char": HEX_CHARS.get(rid, "") if rid else "",
        "question":      question,
        "purpose":       moment_data.get("purpose", []),
        "mood":          moment_data.get("mood", ""),
        "weather":       moment_data.get("weather", []),
        "circumstance":  "",
        "reflection":    "",
        "tags":          [],
        "cast_method":   moment_data.get("cast_method", "coin"),
    }
    entries = load_journal(username)
    entries.insert(0, entry)
    save_journal(entries, username)
    return entry["id"]


def moon_phase(d=None):
    if d is None:
        d = date.today()
    known_new = date(2000, 1, 6)
    cycle = (d - known_new).days % 29.53058867
    if cycle < 1.85:    return "🌑 New Moon"
    elif cycle < 7.38:  return "🌒 Waxing Crescent"
    elif cycle < 9.22:  return "🌓 First Quarter"
    elif cycle < 14.77: return "🌔 Waxing Gibbous"
    elif cycle < 16.61: return "🌕 Full Moon"
    elif cycle < 22.15: return "🌖 Waning Gibbous"
    elif cycle < 23.99: return "🌗 Last Quarter"
    else:               return "🌘 Waning Crescent"


class AddNotesDialog(QWidget):
    saved = Signal()

    def __init__(self, entry_id, username="Default", parent=None):
        super().__init__(parent, Qt.Window)
        self.setWindowTitle("Add Notes to Reading")
        self.setMinimumWidth(500)
        self._entry_id = entry_id
        self._username = username
        self._build()

    def _build(self):
        entries = load_journal(self._username)
        entry   = next((e for e in entries if e.get("id") == self._entry_id), None)

        vl = QVBoxLayout(self)
        vl.setContentsMargins(20, 20, 20, 20)
        vl.setSpacing(10)

        title = QLabel("Add Notes to Reading")
        title.setStyleSheet("font-size:15px; font-weight:bold; color:#515150;")
        vl.addWidget(title)

        if entry:
            hid   = entry.get("hexagram", "")
            hname = entry.get("hexagram_name", "")
            char  = entry.get("hexagram_char", "")
            info  = QLabel(f"<b>{char} {hid}. {hname}</b>  "
                           f"<span style='color:#888;'>"
                           f"{entry.get('date','')} {entry.get('time','')}</span>")
            info.setStyleSheet("font-size:13px;")
            vl.addWidget(info)

        for attr, label, placeholder, height in [
            ("_circ", "Notes",
             "Brief context — what situation prompted this reading?", 80),
            ("_refl", "Reflection",
             "Initial thoughts on the reading", 100),
        ]:
            lbl = QLabel(label)
            lbl.setStyleSheet("font-size:12px; font-weight:bold; color:#515150;")
            vl.addWidget(lbl)
            w = QTextEdit()
            w.setPlaceholderText(placeholder)
            w.setPlainText(entry.get(attr[1:], "") if entry else "")
            w.setFixedHeight(height)
            w.setStyleSheet(
                "QTextEdit { border:1px solid #c0c0bc; border-radius:3px; "
                "font-size:13px; padding:6px; background:#fff; color:#1a1a1a; }")
            vl.addWidget(w)
            setattr(self, attr, w)

        tags_lbl = QLabel("Tags")
        tags_lbl.setStyleSheet("font-size:12px; font-weight:bold; color:#515150;")
        vl.addWidget(tags_lbl)
        self._tags = QLineEdit()
        self._tags.setPlaceholderText("comma separated: work, family, decision…")
        self._tags.setText(", ".join(entry.get("tags", [])) if entry else "")
        self._tags.setStyleSheet(
            "QLineEdit { border:1px solid #c0c0bc; border-radius:3px; "
            "font-size:13px; padding:5px 8px; background:#fff; color:#1a1a1a; }")
        vl.addWidget(self._tags)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        skip = QPushButton("Skip")
        skip.clicked.connect(self.close)
        save_btn = QPushButton("Save Notes")
        save_btn.setStyleSheet(
            "QPushButton { background:#515150; color:#fff; "
            "border:none; padding:6px 18px; border-radius:3px; }"
            "QPushButton:hover { background:#3a3a39; }")
        save_btn.clicked.connect(self._save)
        btn_row.addWidget(skip)
        btn_row.addWidget(save_btn)
        vl.addLayout(btn_row)

    def _save(self):
        entries = load_journal(self._username)
        for i, e in enumerate(entries):
            if e.get("id") == self._entry_id:
                entries[i]["circumstance"] = self._circ.toPlainText().strip()
                entries[i]["reflection"]   = self._refl.toPlainText().strip()
                entries[i]["tags"] = [
                    t.strip() for t in self._tags.text().split(",") if t.strip()]
                break
        save_journal(entries, self._username)
        self.saved.emit()
        self.close()


class EditEntryDialog(QWidget):
    saved = Signal()

    def __init__(self, entry, username="Default", parent=None):
        super().__init__(parent, Qt.Window)
        self.setWindowTitle("Edit Journal Entry")
        self.setMinimumWidth(520)
        self._entry    = entry
        self._username = username
        self._build()

    def _build(self):
        vl = QVBoxLayout(self)
        vl.setContentsMargins(20, 20, 20, 20)
        vl.setSpacing(10)

        char  = self._entry.get("hexagram_char", "")
        hname = self._entry.get("hexagram_name", "")
        hid   = self._entry.get("hexagram", "")
        title = QLabel(f"<b>{char} {hid}. {hname}</b>  "
                       f"<span style='color:#888;'>"
                       f"{self._entry.get('date','')} "
                       f"{self._entry.get('time','')}</span>")
        title.setStyleSheet("font-size:13px;")
        vl.addWidget(title)

        _LS = "font-size:12px; font-weight:bold; color:#515150;"
        _FS = ("QLineEdit, QTextEdit { border:1px solid #c0c0bc; "
               "border-radius:3px; font-size:13px; padding:5px 8px; "
               "background:#fff; color:#1a1a1a; }")

        for attr, label, val in [
            ("_q",    "Question",    self._entry.get("question", "")),
            ("_mood", "Mood",        self._entry.get("mood", "")),
        ]:
            lbl = QLabel(label); lbl.setStyleSheet(_LS); vl.addWidget(lbl)
            w = QLineEdit(val); w.setStyleSheet(_FS); vl.addWidget(w)
            setattr(self, attr, w)

        for attr, label, val, h in [
            ("_circ", "Notes", self._entry.get("circumstance",""), 80),
            ("_refl", "Reflection",   self._entry.get("reflection",""),   100),
        ]:
            lbl = QLabel(label); lbl.setStyleSheet(_LS); vl.addWidget(lbl)
            w = QTextEdit(); w.setPlainText(val); w.setFixedHeight(h)
            w.setStyleSheet(_FS); vl.addWidget(w)
            setattr(self, attr, w)

        lbl = QLabel("Tags"); lbl.setStyleSheet(_LS); vl.addWidget(lbl)
        self._tags = QLineEdit(", ".join(self._entry.get("tags",[])))
        self._tags.setStyleSheet(_FS); vl.addWidget(self._tags)

        btn_row = QHBoxLayout(); btn_row.addStretch()
        cancel = QPushButton("Cancel"); cancel.clicked.connect(self.close)
        save_btn = QPushButton("Save")
        save_btn.setStyleSheet(
            "QPushButton { background:#515150; color:#fff; "
            "border:none; padding:6px 18px; border-radius:3px; }"
            "QPushButton:hover { background:#3a3a39; }")
        save_btn.clicked.connect(self._save)
        btn_row.addWidget(cancel); btn_row.addWidget(save_btn)
        vl.addLayout(btn_row)

    def _save(self):
        entries = load_journal(self._username)
        for i, e in enumerate(entries):
            if e.get("id") == self._entry.get("id"):
                entries[i]["question"]     = self._q.text().strip()
                entries[i]["mood"]         = self._mood.text().strip()
                entries[i]["circumstance"] = self._circ.toPlainText().strip()
                entries[i]["reflection"]   = self._refl.toPlainText().strip()
                entries[i]["tags"] = [
                    t.strip() for t in self._tags.text().split(",") if t.strip()]
                break
        save_journal(entries, self._username)
        self.saved.emit()
        self.close()


class JournalView(QWidget):
    load_hex = Signal(int)

    _BTN_STYLE = (
        "QPushButton { background:#515150; color:#fff; border:none; "
        "padding:4px 12px; border-radius:3px; font-size:11px; }"
        "QPushButton:hover { background:#3a3a39; }"
        "QPushButton:checked { background:#8b6914; }")
    _SECTION_LABEL = ("font-size:11px; font-weight:bold; color:#888; "
                      "text-transform:uppercase; letter-spacing:0.5px;")
    _BODY = "font-size:13px; color:#1a1a1a;"

    def __init__(self, username="Default", parent=None):
        super().__init__(parent, Qt.Window)
        self.setWindowTitle("Reading Journal")
        self.resize(1100, 720)
        self._username      = username
        self._entries       = []
        self._current_entry = None
        self._current_hex   = None
        self._entry_buttons = {}
        self._build()
        self.refresh()

    def _build(self):
        from widgets import ZoomView
        base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
        self._book_dir = os.path.join(base, "book")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        v_split = QSplitter(Qt.Vertical)
        h_split = QSplitter(Qt.Horizontal)

        left = QWidget()
        left.setMinimumWidth(180)
        left.setMaximumWidth(260)
        lv = QVBoxLayout(left)
        lv.setContentsMargins(8, 8, 8, 8)
        lv.setSpacing(6)

        filter_row = QHBoxLayout()
        self._filter = QLineEdit()
        self._filter.setPlaceholderText("Filter…")
        self._filter.setStyleSheet(
            "QLineEdit { border:1px solid #c0c0bc; border-radius:3px; "
            "padding:4px 6px; font-size:12px; color:#1a1a1a; background:#fff; }")
        self._filter.textChanged.connect(self._apply_filter)
        filter_row.addWidget(self._filter)
        refresh_btn = QPushButton("↺")
        refresh_btn.setFixedWidth(28)
        refresh_btn.clicked.connect(self.refresh)
        refresh_btn.setStyleSheet(self._BTN_STYLE)
        filter_row.addWidget(refresh_btn)
        lv.addLayout(filter_row)

        self._list_scroll = QScrollArea()
        self._list_scroll.setWidgetResizable(True)
        self._list_scroll.setStyleSheet("QScrollArea { border:none; }")
        self._list_inner  = QWidget()
        self._list_layout = QVBoxLayout(self._list_inner)
        self._list_layout.setSpacing(2)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.addStretch()
        self._list_scroll.setWidget(self._list_inner)
        lv.addWidget(self._list_scroll, 1)

        self._list_status = QLabel("")
        self._list_status.setStyleSheet("font-size:10px; color:#aaa;")
        lv.addWidget(self._list_status)

        h_split.addWidget(left)

        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setStyleSheet("QScrollArea { border:none; }")
        self._detail = QWidget()
        self._detail.setStyleSheet("background:#f8f8f6;")
        self._detail_layout = QVBoxLayout(self._detail)
        self._detail_layout.setContentsMargins(16, 14, 16, 14)
        self._detail_layout.setSpacing(10)
        self._detail_layout.addStretch()
        right_scroll.setWidget(self._detail)
        h_split.addWidget(right_scroll)

        h_split.setSizes([200, 700])
        h_split.setStretchFactor(0, 0)
        h_split.setStretchFactor(1, 1)
        v_split.addWidget(h_split)

        bottom = QWidget()
        bv = QVBoxLayout(bottom)
        bv.setContentsMargins(0, 0, 0, 0)
        bv.setSpacing(0)

        tab_bar = QHBoxLayout()
        tab_bar.setContentsMargins(8, 4, 8, 0)
        tab_bar.setSpacing(4)
        self._trans_btns = {}
        for author in ("Wilhelm", "Legge", "Hatcher"):
            btn = QPushButton(author)
            btn.setCheckable(True)
            btn.setStyleSheet(self._BTN_STYLE)
            btn.clicked.connect(
                lambda _, a=author.lower(): self._load_translation(a))
            tab_bar.addWidget(btn)
            self._trans_btns[author.lower()] = btn
        tab_bar.addStretch()
        bv.addLayout(tab_bar)

        self._trans_view = ZoomView()
        self._trans_view.page().navigationRequested.connect(
            self._on_trans_navigation)
        bv.addWidget(self._trans_view, 1)
        v_split.addWidget(bottom)

        v_split.setSizes([420, 280])
        v_split.setStretchFactor(0, 1)
        v_split.setStretchFactor(1, 0)

        root.addWidget(v_split, 1)

        self._current_author = "wilhelm"
        self._trans_btns["wilhelm"].setChecked(True)

    def refresh(self):
        self._entries = load_journal(self._username)
        self._apply_filter(self._filter.text())

    def _apply_filter(self, text):
        text = text.lower().strip()
        filtered = [e for e in self._entries
                    if not text or text in " ".join([
                        e.get("question",""), e.get("mood",""),
                        e.get("circumstance",""), e.get("reflection",""),
                        e.get("hexagram_name",""), e.get("moon",""),
                        " ".join(e.get("tags",[])),
                        " ".join(e.get("purpose",[])),
                    ]).lower()]
        self._render_list(filtered)

    def _render_list(self, entries):
        self._entry_buttons = {}
        while self._list_layout.count() > 1:
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for e in entries:
            btn = QPushButton(f"{e.get('date','?')}  {e.get('time','')}")
            btn.setStyleSheet(
                "QPushButton { text-align:left; border:none; "
                "border-bottom:1px solid #e0e0dc; padding:6px 8px; "
                "font-size:12px; color:#1a1a1a; background:#f8f8f6; }"
                "QPushButton:hover { background:#eeeeed; }"
                "QPushButton:checked { background:#515150; color:#fff; "
                "font-weight:bold; }")
            btn.setCheckable(True)
            btn.setContextMenuPolicy(Qt.CustomContextMenu)
            btn.customContextMenuRequested.connect(
                lambda pos, entry=e, b=btn: self._show_context_menu(pos, entry, b))
            btn.clicked.connect(
                lambda _, entry=e, b=btn: self._select_entry(entry, b))
            self._list_layout.insertWidget(self._list_layout.count()-1, btn)
            self._entry_buttons[e.get("id")] = btn

        n = len(entries)
        self._list_status.setText(
            f"{n} entr{'y' if n==1 else 'ies'}" +
            (f" of {len(self._entries)}"
             if len(entries) != len(self._entries) else ""))

    def _show_context_menu(self, pos, entry, btn):
        self._select_entry(entry, btn)
        menu = QMenu(self)
        read_act   = menu.addAction("Read")
        edit_act   = menu.addAction("Edit")
        menu.addSeparator()
        delete_act = menu.addAction("Delete")
        action = menu.exec(btn.mapToGlobal(pos))
        if action == read_act:
            hid = entry.get("hexagram")
            if hid:
                self.load_hex.emit(int(hid))
        elif action == edit_act:
            self._open_edit(entry)
        elif action == delete_act:
            self._delete_entry(entry)

    def _select_entry(self, entry, btn):
        for b in self._entry_buttons.values():
            if b is not btn:
                b.setChecked(False)
        btn.setChecked(True)
        self._current_entry = entry
        self._render_detail(entry)
        hid = entry.get("hexagram")
        if hid:
            self._load_hex_in_panel(int(hid))

    def _open_edit(self, entry):
        dlg = EditEntryDialog(entry, self._username)
        dlg.saved.connect(self.refresh)
        dlg.show(); dlg.raise_()

    def _delete_entry(self, entry):
        hid   = entry.get("hexagram","?")
        hname = entry.get("hexagram_name","")
        date_ = entry.get("date","?")
        reply = QMessageBox.question(
            self, "Delete Entry",
            f"Delete this journal entry?\n\n{hid}. {hname}  —  {date_}\n\nThis cannot be undone.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        entry_id = entry.get("id")
        delete_journal_entry(entry_id, self._username)
        if self._current_entry and self._current_entry.get("id") == entry_id:
            self._current_entry = None
            while self._detail_layout.count() > 1:
                item = self._detail_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
        self.refresh()

    def _hex_figure_pixmap(self, hex_id, size=72):
        """Render the six-line hexagram figure for hex_id to a QPixmap."""
        svg = hexfig.hex_svg(hex_id, size)
        renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
        dim = renderer.defaultSize()
        w = dim.width() or int(size * 1.4)
        h = dim.height() or size
        pm = QPixmap(w, h)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        renderer.render(p)
        p.end()
        return pm

    def _hex_figure_block(self, label, hex_id, caption):
        """Vertical block: small caption label over the rendered hex figure."""
        col = QVBoxLayout(); col.setSpacing(3)
        cap = QLabel(f"{label}  {caption}")
        cap.setStyleSheet("font-size:11px;color:#1a1a1a;font-weight:bold;background:transparent;")
        fig = QLabel()
        fig.setPixmap(self._hex_figure_pixmap(hex_id))
        fig.setStyleSheet("background:transparent;")
        col.addWidget(cap); col.addWidget(fig); col.addStretch()
        return col

    def _render_detail(self, e):
        while self._detail_layout.count() > 1:
            item = self._detail_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        def section(text):
            lbl = QLabel(text); lbl.setStyleSheet(self._SECTION_LABEL)
            self._detail_layout.insertWidget(self._detail_layout.count()-1, lbl)

        def row(label, value):
            if not value: return
            lbl = QLabel(f"<b>{label}:</b>  {value}")
            lbl.setStyleSheet(self._BODY); lbl.setWordWrap(True)
            self._detail_layout.insertWidget(self._detail_layout.count()-1, lbl)

        # ── ROW 1: Moment (left) | Auto-captured + Profile (right) ──────────
        prof = load_profile(e.get("alias", self._username))
        top_row = QHBoxLayout(); top_row.setSpacing(12)

        left_w = QWidget(); left_vl = QVBoxLayout(left_w)
        left_vl.setContentsMargins(0,0,0,0); left_vl.setSpacing(4)
        ts = QLabel(f"{e.get('date','')}  ·  {e.get('time','')}")
        ts.setStyleSheet("font-size:14px;font-weight:bold;color:#515150;")
        left_vl.addWidget(ts)
        q_lbl = QLabel(e.get("question",""))
        q_lbl.setStyleSheet("font-size:13px;color:#1a1a1a;font-style:italic;")
        q_lbl.setWordWrap(True); left_vl.addWidget(q_lbl)
        left_vl.addStretch(); top_row.addWidget(left_w, 1)

        right_w = QWidget(); right_vl = QVBoxLayout(right_w)
        right_vl.setContentsMargins(8,0,0,0); right_vl.setSpacing(2)
        right_w.setStyleSheet("border-left:1px solid #c0c0bc;")

        def r2(label, value):
            if not value: return
            lbl = QLabel(f"<span style='color:#888;font-size:11px;'>{label}</span>"
                         f"&nbsp;&nbsp;<span style='color:#1a1a1a;font-size:12px;'>{value}</span>")
            lbl.setWordWrap(True); right_vl.addWidget(lbl)

        weather = e.get("weather","")
        if isinstance(weather, list): weather = ", ".join(weather)
        r2("Date",           e.get("date",""))
        r2("Time",           e.get("time",""))
        r2("Moon",           e.get("moon",""))
        r2("Cast method",    e.get("cast_method","coin").capitalize())
        r2("Purpose",        ", ".join(e.get("purpose",[])))
        r2("Mood",           e.get("mood",""))
        r2("Weather",        weather)
        r2("Alias",          prof.get("alias",""))
        r2("Date of birth",  prof.get("dob",""))
        r2("Time of birth",  prof.get("tob",""))
        bl = prof.get("birth_lat",""); blo = prof.get("birth_lon","")
        r2("Birth location", f"{bl}, {blo}" if bl and blo else "")
        cl = prof.get("current_lat",""); clo = prof.get("current_lon","")
        r2("Current location", f"{cl}, {clo}" if cl and clo else "")
        right_vl.addStretch(); top_row.addWidget(right_w, 1)
        top_w = QWidget(); top_w.setLayout(top_row)
        self._detail_layout.insertWidget(self._detail_layout.count()-1, top_w)

        # ── ROW 2: Cast ───────────────────────────────────────────────────────
        section("Cast")
        hid   = e.get("hexagram","")
        hname = e.get("hexagram_name","")
        char  = e.get("hexagram_char","")
        row("Hexagram", f"{char}  {hid}. {hname}" if hid else "—")
        row("Method",   e.get("cast_method","coin").capitalize())
        moving = e.get("moving_lines",[])
        rid = rname = rchar = ""
        if moving:
            rid   = e.get("relating","")
            rname = e.get("relating_name","")
            rchar = e.get("relating_char","")
            row("Moving lines", str(moving))
            row("Relating",     f"{rchar}  {rid}. {rname}")
        # Hexagram figures (Primary, and Relating if there are moving lines)
        fig_row = QHBoxLayout(); fig_row.setSpacing(28)
        if hid:
            fig_row.addLayout(self._hex_figure_block("Primary", int(hid),
                                                      f"{char} {hid}"))
        if moving and rid:
            fig_row.addLayout(self._hex_figure_block("Relating", int(rid),
                                                     f"{rchar} {rid}"))
        fig_row.addStretch()
        self._detail_layout.insertLayout(self._detail_layout.count()-1, fig_row)

        hex_btn_row = QHBoxLayout()
        if hid:
            pb = QPushButton(f"Primary  {char} {hid}")
            pb.setStyleSheet(self._BTN_STYLE)
            pb.clicked.connect(lambda: self._load_hex_in_panel(int(hid)))
            hex_btn_row.addWidget(pb)
        if moving and rid:
            rb = QPushButton(f"Relating  {rchar} {rid}")
            rb.setStyleSheet(self._BTN_STYLE)
            rb.clicked.connect(lambda: self._load_hex_in_panel(int(rid)))
            hex_btn_row.addWidget(rb)
        hex_btn_row.addStretch()
        self._detail_layout.insertLayout(self._detail_layout.count()-1, hex_btn_row)

        section("Circumstance")
        circ_lbl = QLabel(e.get("circumstance","") or "—")
        circ_lbl.setStyleSheet(self._BODY); circ_lbl.setWordWrap(True)
        self._detail_layout.insertWidget(self._detail_layout.count()-1, circ_lbl)

        section("Reflection")
        self._refl_edit = QTextEdit()
        self._refl_edit.setPlainText(e.get("reflection",""))
        self._refl_edit.setFixedHeight(100)
        self._refl_edit.setStyleSheet(
            "QTextEdit { border:1px solid #c0c0bc; border-radius:3px; "
            "font-size:13px; padding:6px; background:#fff; color:#1a1a1a; }")
        self._detail_layout.insertWidget(self._detail_layout.count()-1, self._refl_edit)

        section("Tags")
        self._tags_edit = QLineEdit()
        self._tags_edit.setText(", ".join(e.get("tags",[])))
        self._tags_edit.setStyleSheet(
            "QLineEdit { border:1px solid #c0c0bc; border-radius:3px; "
            "font-size:13px; padding:5px 8px; background:#fff; color:#1a1a1a; }")
        self._detail_layout.insertWidget(self._detail_layout.count()-1, self._tags_edit)

        btn_row_detail = QHBoxLayout()

        edit_btn = QPushButton("Edit Entry")
        edit_btn.setStyleSheet(
            "QPushButton { background:#8b6914; color:#fff; border:none; "
            "padding:6px 16px; border-radius:3px; font-size:12px; }"
            "QPushButton:hover { background:#a07820; }")
        edit_btn.clicked.connect(lambda: self._open_edit(e))
        btn_row_detail.addWidget(edit_btn)

        save_btn = QPushButton("Save Reflection & Tags")
        save_btn.setStyleSheet(
            "QPushButton { background:#515150; color:#fff; border:none; "
            "padding:6px 16px; border-radius:3px; font-size:12px; }"
            "QPushButton:hover { background:#3a3a39; }")
        save_btn.clicked.connect(lambda: self._save_edits(e))
        btn_row_detail.addWidget(save_btn)
        btn_row_detail.addStretch()

        btn_detail_w = QWidget()
        btn_detail_w.setLayout(btn_row_detail)
        self._detail_layout.insertWidget(self._detail_layout.count()-1, btn_detail_w)

    def _save_edits(self, entry):
        entries = load_journal(self._username)
        for i, e in enumerate(entries):
            if e.get("id") == entry.get("id"):
                entries[i]["reflection"] = self._refl_edit.toPlainText().strip()
                entries[i]["tags"] = [
                    t.strip() for t in
                    self._tags_edit.text().split(",") if t.strip()]
                break
        save_journal(entries, self._username)
        self._entries = entries

    def _load_hex_in_panel(self, hex_id):
        self._current_hex = hex_id
        self.load_hex.emit(hex_id)
        self._load_translation(self._current_author)

    def _load_translation(self, author):
        self._current_author = author
        for a, btn in self._trans_btns.items():
            btn.setChecked(a == author)
        if self._current_hex is None:
            return
        hid  = self._current_hex
        path = os.path.join(
            self._book_dir, "en", author, f"hex{hid}", f"hex{hid}_0.html")
        self._load_trans_file(path)

    def _load_trans_file(self, path):
        if not os.path.exists(path):
            self._trans_view.setHtml(
                f"<p style='color:red'>Not found:<br>{path}</p>")
            return
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                html = f.read()
        except Exception as ex:
            self._trans_view.setHtml(f"<p style='color:red'>{ex}</p>")
            return
        css = """
        body  { background:#f8f8f6; font-family:Georgia,serif;
                font-size:15px; line-height:1.7; margin:16px 24px; }
        p.title       { color:#515150; font-size:1.4em; font-weight:bold;
                        font-style:italic;
                        font-family:'AR PL UKai CN',Georgia,serif; }
        p.composition { color:#515150; font-size:1.1em; font-weight:bold;
                        font-style:italic; margin-top:1em; }
        p.comment     { color:#1a1a1a; font-size:1.0em; margin-top:0.4em; }
        p.sec         { color:#515150; font-size:1.2em; font-weight:bold;
                        font-style:italic; margin-top:1em; }
        p.text        { color:#2a082a; font-size:1.0em; margin-top:0.3em; }
        .han          { font-family:'AR PL UKai CN',serif; font-size:1.8em;
                        vertical-align:middle; margin-right:0.2em; }
        em            { font-style:italic; color:#515150; }
        """
        import re as _re
        html = _re.sub(r'<LINK[^>]*>', '', html, flags=_re.IGNORECASE)
        html = html.replace("</head>", f"<style>{css}</style></head>", 1)
        if path.endswith("_0.html") and self._current_hex is not None \
                and f"hex{self._current_hex}_0" in path:
            try:
                html = hexfig.inject_hex_figure(html, self._current_hex, size=28)
            except Exception:
                pass
        from PySide6.QtCore import QUrl
        self._trans_view.setHtml(
            html, QUrl.fromLocalFile(os.path.dirname(path)+os.sep))

    def _on_trans_navigation(self, request):
        url  = request.url()
        path = url.toLocalFile()
        if path and path.endswith('.html') and 'hex' in path:
            request.reject(); self._load_trans_file(path)
        else:
            request.accept()


def _profile_path():
    return os.path.join(_yijing_dir(), "profiles.json")

def load_profile(username):
    try:
        with open(_profile_path(), encoding="utf-8") as f:
            profiles = json.load(f)
        return profiles.get(username, _blank_profile(username))
    except Exception:
        return _blank_profile(username)

def save_profile(username, profile):
    try:
        with open(_profile_path(), encoding="utf-8") as f:
            profiles = json.load(f)
    except Exception:
        profiles = {}
    profiles[username] = profile
    with open(_profile_path(), "w", encoding="utf-8") as f:
        json.dump(profiles, f, ensure_ascii=False, indent=2)

def _blank_profile(username):
    return {
        "alias": username, "created": datetime.now().isoformat(),
        "dob": "", "tob": "", "birth_lat": "", "birth_lon": "",
        "current_lat": "", "current_lon": "", "notes": "",
    }


class ProfileDialog(QDialog):
    _FIELD_STYLE = (
        "QLineEdit { background:#ffffff; color:#1a1a1a; "
        "border:1px solid #c0c0bc; border-radius:3px; "
        "font-size:13px; padding:5px 8px; }"
        "QLineEdit:read-only { background:#f0f0ee; color:#888; }")
    _LABEL_STYLE = "font-size:12px; font-weight:bold; color:#515150;"
    _HINT_STYLE  = "font-size:11px; color:#888;"

    def __init__(self, username, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Profile — {username}")
        self.setMinimumWidth(480)
        self._username = username
        self._profile  = load_profile(username)
        self._build()

    def _build(self):
        vl = QVBoxLayout(self)
        vl.setContentsMargins(24, 20, 24, 20)
        vl.setSpacing(12)

        hdr = QLabel(f"Profile: {self._username}")
        hdr.setStyleSheet("font-size:15px; font-weight:bold; color:#515150;")
        vl.addWidget(hdr)

        if self._username == "Guest":
            note = QLabel(
                "Guest sessions are not saved. "
                "Select a user on the opening screen to create a profile.")
            note.setStyleSheet(self._HINT_STYLE); note.setWordWrap(True)
            vl.addWidget(note)
            close_btn = QPushButton("Close"); close_btn.clicked.connect(self.reject)
            vl.addWidget(close_btn, alignment=Qt.AlignRight)
            return

        from PySide6.QtWidgets import QFormLayout
        form = QFormLayout(); form.setSpacing(8)
        form.setLabelAlignment(Qt.AlignRight)

        self._alias = QLineEdit(self._profile.get("alias", self._username))
        self._alias.setReadOnly(True); self._alias.setStyleSheet(self._FIELD_STYLE)
        form.addRow(self._lbl("Alias"), self._alias)

        self._dob = QLineEdit(self._profile.get("dob",""))
        self._dob.setPlaceholderText("YYYY-MM-DD  (optional)")
        self._dob.setStyleSheet(self._FIELD_STYLE)
        form.addRow(self._lbl("Date of birth"), self._dob)

        self._tob = QLineEdit(self._profile.get("tob",""))
        self._tob.setPlaceholderText("HH:MM  (optional)")
        self._tob.setStyleSheet(self._FIELD_STYLE)
        form.addRow(self._lbl("Time of birth"), self._tob)

        birth_row, self._birth_lat, self._birth_lon = self._coord_row(
            self._profile.get("birth_lat",""), self._profile.get("birth_lon",""))
        form.addRow(self._lbl("Birth location"), birth_row)
        form.addRow("", self._hint("Find at maps.google.com — right-click → What's here?"))

        curr_row, self._curr_lat, self._curr_lon = self._coord_row(
            self._profile.get("current_lat",""), self._profile.get("current_lon",""))
        form.addRow(self._lbl("Current location"), curr_row)
        form.addRow("", self._hint("Find at maps.google.com — right-click → What's here?"))

        vl.addLayout(form)

        notes_lbl = QLabel("Notes"); notes_lbl.setStyleSheet(self._LABEL_STYLE)
        vl.addWidget(notes_lbl)
        self._notes = QTextEdit()
        self._notes.setPlainText(self._profile.get("notes",""))
        self._notes.setFixedHeight(80)
        self._notes.setStyleSheet(
            "QTextEdit { background:#ffffff; color:#1a1a1a; "
            "border:1px solid #c0c0bc; border-radius:3px; "
            "font-size:13px; padding:5px; }")
        vl.addWidget(self._notes)

        btn_row = QHBoxLayout(); btn_row.addStretch()
        cancel = QPushButton("Cancel"); cancel.clicked.connect(self.reject)
        save_btn = QPushButton("Save Profile")
        save_btn.setStyleSheet(
            "QPushButton { background:#515150; color:#fff; border:none; "
            "padding:6px 20px; border-radius:3px; }"
            "QPushButton:hover { background:#3a3a39; }")
        save_btn.clicked.connect(self._save)
        btn_row.addWidget(cancel); btn_row.addWidget(save_btn)
        vl.addLayout(btn_row)

    def _lbl(self, text):
        lbl = QLabel(text); lbl.setStyleSheet(self._LABEL_STYLE); return lbl

    def _hint(self, text):
        lbl = QLabel(text); lbl.setStyleSheet(self._HINT_STYLE); return lbl

    def _coord_row(self, lat_val, lon_val):
        from PySide6.QtWidgets import QHBoxLayout
        row = QHBoxLayout()
        lat = QLineEdit(str(lat_val) if lat_val else "")
        lat.setPlaceholderText("Lat  e.g. 25.0330")
        lat.setStyleSheet(self._FIELD_STYLE); lat.setFixedWidth(130)
        lon = QLineEdit(str(lon_val) if lon_val else "")
        lon.setPlaceholderText("Long  e.g. 121.5654")
        lon.setStyleSheet(self._FIELD_STYLE); lon.setFixedWidth(130)
        row.addWidget(lat); row.addWidget(QLabel("  ")); row.addWidget(lon)
        row.addStretch()
        return row, lat, lon

    def _save(self):
        def fe(text):
            t = text.strip()
            if not t: return ""
            try: return float(t)
            except ValueError: return ""

        self._profile.update({
            "alias": self._username, "dob": self._dob.text().strip(),
            "tob": self._tob.text().strip(),
            "birth_lat":   fe(self._birth_lat.text()),
            "birth_lon":   fe(self._birth_lon.text()),
            "current_lat": fe(self._curr_lat.text()),
            "current_lon": fe(self._curr_lon.text()),
            "notes": self._notes.toPlainText().strip(),
        })
        save_profile(self._username, self._profile)
        self.accept()
