"""
The YiJing — Navigating Change
journal.py — Version 1.0.2 — Wednesday 28 October 2026
GNU GPL v3
"""

import os, sys, re, json
from datetime import datetime, timezone

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QLineEdit, QScrollArea, QMessageBox,
    QDialog, QSplitter, QMenu,
)
from PySide6.QtCore import Qt, Signal, QByteArray, QTimer
from PySide6.QtGui import QPixmap, QPainter
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

def _users_backup_path():
    return os.path.join(_yijing_dir(), "users_backup.json")

# Journal files are named alias + registration stamp (journal_rjv_20261028-091402.json)
# so no two accounts can share one. Accounts from before the stamp keep their
# old file (journal_rjv.json) until their next consultation moves them.

def _safe(username):
    return re.sub(r'[^a-zA-Z0-9_-]', '_', username)

_STAMP_RE = re.compile(r"_(\d{8}-\d{6}(?:-\d+)?)\.json$")

def _stamps_on_disk(username):
    prefix = f"journal_{_safe(username)}_"
    return [m.group(1) for f in os.listdir(_yijing_dir())
            if f.startswith(prefix) and not f.endswith("_backup.json")
            and (m := _STAMP_RE.search(f)) and f == f"{prefix}{m.group(1)}.json"]

def _registered(username):
    """The account's registration stamp, or None for a pre-stamp account. If the
    profiles store is unreadable, a single stamped file on disk is still found."""
    try:
        profiles = _load_store(_profile_path(), _profile_backup_path(), dict)
    except StoreError:
        found = _stamps_on_disk(username)
        return found[0] if len(found) == 1 else None
    return profiles.get(username, {}).get("registered")

def _journal_stem(username):
    stamp = _registered(username)
    return f"journal_{_safe(username)}" + (f"_{stamp}" if stamp else "")

def _journal_path(username="Default"):
    return os.path.join(_yijing_dir(), _journal_stem(username) + ".json")

def _journal_backup_path(username="Default"):
    return os.path.join(_yijing_dir(), _journal_stem(username) + "_backup.json")

def _new_stamp(username):
    """A registration stamp whose journal file name is not already taken, on disk
    or by another account whose alias cleans to the same name."""
    taken = set(_stamps_on_disk(username))
    try:
        profiles = _load_store(_profile_path(), _profile_backup_path(), dict)
        taken |= {p.get("registered") for a, p in profiles.items()
                  if a != username and _safe(a) == _safe(username)}
    except StoreError:
        pass
    base = datetime.now().strftime("%Y%m%d-%H%M%S"); stamp = base; n = 2
    while stamp in taken:
        stamp = f"{base}-{n}"; n += 1
    return stamp

def _set_registered(username, stamp):
    profiles = _load_store(_profile_path(), _profile_backup_path(), dict)
    profiles.setdefault(username, _blank_profile(username))["registered"] = stamp
    _write_store(_profile_path(), _profile_backup_path(), profiles)

def _ensure_registered(username):
    """Give a pre-stamp account its stamp, copying its readings into the stamped
    file first. The old file is left untouched. If the stamp cannot be saved the
    account simply stays on its old file and is tried again next time."""
    if _registered(username):
        return
    try:                                      # no stray copies: only move if the stamp can be saved
        _load_store(_profile_path(), _profile_backup_path(), dict)
    except StoreError:
        return
    entries = load_journal(username)          # old file, or its backup; StoreError if both unreadable
    stamp = _new_stamp(username)
    stem = f"journal_{_safe(username)}_{stamp}"
    _write_store(os.path.join(_yijing_dir(), stem + ".json"),
                 os.path.join(_yijing_dir(), stem + "_backup.json"), entries)
    try:
        _set_registered(username, stamp)
    except StoreError:
        pass


# ── Data stores (journal, users, profiles) ───────────────────────────────────
# A store that exists but cannot be read is never written over: reads fall
# back to the backup, and if both are unreadable StoreError is raised so the
# caller can warn and save nothing. The backup always holds the previous
# good version; writes go through a temp file and os.replace.

class StoreError(Exception):
    """A data file exists but neither it nor its backup can be read."""

def store_warning(parent, err):
    QMessageBox.warning(parent, "Not Saved",
        "A data file could not be read, so nothing was saved.\n"
        f"The existing file has been left untouched:\n{err.args[0]}")

def _read_json(path, kind):
    """(data, state) — state is 'ok', 'missing' or 'bad' (unreadable or wrong type)."""
    if not os.path.exists(path):
        return None, "missing"
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return None, "bad"
    return (data, "ok") if isinstance(data, kind) else (None, "bad")

def _load_store(path, backup, kind):
    data, state = _read_json(path, kind)
    if state == "ok":
        return data
    bdata, bstate = _read_json(backup, kind)
    if bstate == "ok":
        return bdata
    if state == "missing" and bstate == "missing":
        return kind()
    raise StoreError(path)

def _replace_atomically(path, text):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)

def _write_store(path, backup, data):
    if _read_json(path, type(data))[1] == "ok":
        with open(path, encoding="utf-8") as f:
            _replace_atomically(backup, f.read())
    _replace_atomically(path, json.dumps(data, ensure_ascii=False, indent=2))


def load_users(strict=False):
    """Return list of user aliases. Empty list if none created yet.
    strict=True raises StoreError instead of returning [] for an unreadable file."""
    try:
        users = _load_store(_users_path(), _users_backup_path(), list)
    except StoreError:
        if strict:
            raise
        return []
    # Filter out the old "Default" placeholder if present
    return [u for u in users if u != "Default"]

def save_users(users):
    _write_store(_users_path(), _users_backup_path(), users)

def add_user(alias):
    users = load_users(strict=True)
    if alias and alias not in users:
        users.append(alias)
        save_users(users)
        try:
            _set_registered(alias, _new_stamp(alias))
        except StoreError:
            pass                                  # stamped at its first consultation instead
    return users


def load_journal(username="Default"):
    """Raises StoreError if the journal and its backup are both unreadable."""
    return _load_store(_journal_path(username), _journal_backup_path(username), list)

def save_journal(entries, username="Default"):
    _write_store(_journal_path(username), _journal_backup_path(username), entries)

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
    _ensure_registered(username)
    entries = load_journal(username)
    entries.insert(0, entry)
    save_journal(entries, username)
    return entry["id"]


_SYNODIC        = 29.530588853                                    # mean synodic month, days
_NEW_MOON_EPOCH = datetime(2000, 1, 6, 18, 14, tzinfo=timezone.utc)   # reference new moon
_PHASES = ["🌑 New Moon", "🌒 Waxing Crescent", "🌓 First Quarter", "🌔 Waxing Gibbous",
           "🌕 Full Moon", "🌖 Waning Gibbous", "🌗 Last Quarter", "🌘 Waning Crescent"]

def moon_phase(when=None):
    """Phase name for a moment (default: now), from the mean moon's age in UTC with
    eight windows centred on each phase — within about a day of the true phase.
    A plain date is taken at noon UTC; a naive datetime as local time."""
    if when is None:
        when = datetime.now(timezone.utc)
    elif not isinstance(when, datetime):
        when = datetime(when.year, when.month, when.day, 12, tzinfo=timezone.utc)
    elif when.tzinfo is None:
        when = when.astimezone(timezone.utc)
    age = ((when - _NEW_MOON_EPOCH).total_seconds() / 86400) % _SYNODIC
    return _PHASES[int(((age + _SYNODIC / 16) % _SYNODIC) // (_SYNODIC / 8))]


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
        try:
            entries = load_journal(self._username)
        except StoreError:
            entries = []
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
        try:
            entries = load_journal(self._username)
        except StoreError as err:
            store_warning(self, err); return
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
        try:
            entries = load_journal(self._username)
        except StoreError as err:
            store_warning(self, err); return
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
        try:
            self._entries = load_journal(self._username)
        except StoreError as err:
            self._entries = []
            QMessageBox.warning(self, "Journal Unreadable",
                "Your journal file could not be read. It has been left untouched, "
                f"and nothing will be saved to it:\n{err.args[0]}")
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
        from widgets import keep_window
        dlg = EditEntryDialog(entry, self._username)
        keep_window(self, dlg)
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
        try:
            delete_journal_entry(entry_id, self._username)
        except StoreError as err:
            store_warning(self, err); return
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
        fig_row.setContentsMargins(0, 0, 0, 0)
        if hid:
            fig_row.addLayout(self._hex_figure_block("Primary", int(hid),
                                                      f"{char} {hid}"))
        if moving and rid:
            fig_row.addLayout(self._hex_figure_block("Relating", int(rid),
                                                     f"{rchar} {rid}"))
        fig_row.addStretch()
        fig_w = QWidget(); fig_w.setLayout(fig_row)   # widget-wrapped: re-render deletes it
        self._detail_layout.insertWidget(self._detail_layout.count()-1, fig_w)

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
        hex_btn_row.setContentsMargins(0, 0, 0, 0)
        hex_btn_w = QWidget(); hex_btn_w.setLayout(hex_btn_row)   # widget-wrapped: re-render deletes it
        self._detail_layout.insertWidget(self._detail_layout.count()-1, hex_btn_w)

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
        try:
            entries = load_journal(self._username)
        except StoreError as err:
            store_warning(self, err); return
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
        # browsing stays in the journal; only the "Read" menu action emits load_hex
        self._current_hex = hex_id
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
            # load after this callback returns — loading inside it aborts QtWebEngine
            request.reject(); QTimer.singleShot(0, lambda p=path: self._follow_trans(p))

    def _follow_trans(self, path):
        m = re.search(r'hex(\d+)/hex\1_0\.html$', path.replace(os.sep, '/'))
        if m:
            self._load_hex_in_panel(int(m.group(1)))
        else:
            self._load_trans_file(path)


def _profile_path():
    return os.path.join(_yijing_dir(), "profiles.json")

def _profile_backup_path():
    return os.path.join(_yijing_dir(), "profiles_backup.json")

def load_profile(username, strict=False):
    try:
        profiles = _load_store(_profile_path(), _profile_backup_path(), dict)
    except StoreError:
        if strict:
            raise
        profiles = {}
    return profiles.get(username, _blank_profile(username))

def save_profile(username, profile):
    profiles = _load_store(_profile_path(), _profile_backup_path(), dict)
    stamp = profiles.get(username, {}).get("registered")
    if stamp and "registered" not in profile:     # a dialog opened before the stamp must not drop it
        profile = dict(profile, registered=stamp)
    profiles[username] = profile
    _write_store(_profile_path(), _profile_backup_path(), profiles)

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
        try:
            save_profile(self._username, self._profile)
        except StoreError as err:
            store_warning(self, err); return
        self.accept()
