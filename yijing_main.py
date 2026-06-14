"""
The YiJing (I Ching) — Navigating Change

Python/PySide6 port of iching-0.2 by Jean Pierre Charalambos (2002).
Coin casting engine from pyChing by Stephen M. Gava (1999-2006).
Translations: Richard Wilhelm (1923), James Legge (1899).
Port and redesign: rjv, 2026 — GNU GPL v3
"""

# ── Application Identity ──────────────────────────────────────────────────────
APP_NAME    = "The YiJing (I Ching) — Navigating Change"
APP_VER     = "1.0.0"
APP_DEV     = "archerprojects"
APP_CONTACT = "archer.projects@proton.me"
APP_ID      = "io.archerprojects.YiJingNavigatingChange"
APP_LICENSE = "GPL-3.0-or-later"
AOYAGI_FAMILY = "aoyagireisyosimo2"   # read back from font at startup; fallback to known subset name
# Reader sources: (key, book-dir author, tab label)
SOURCES = [
    ("wilhelm",  "wilhelm",  "Wilhelm"),
    ("legge",    "legge",    "Legge"),
    ("hatcher",  "hatcher",  "Hatcher"),
    ("zhongwen", "zhongwen", "中文"),
    ("wings",    "wings",    "Ten Wings / 十翼"),
]
# ─────────────────────────────────────────────────────────────────────────────

import sys, os, re

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QStackedWidget,
    QSplitter, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QTabWidget, QStatusBar,
    QFileDialog, QMessageBox, QLineEdit, QFrame, QSizePolicy,
    QScrollArea, QGridLayout, QDialog,
)
from PySide6.QtCore import Qt, QTimer, Signal, QObject, QSize
from PySide6.QtWebEngineCore import QWebEngineSettings
from PySide6.QtGui import QPainter, QColor, QFont, QPixmap, QPalette, QFontDatabase

def resource(rel):
    base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel)

BOOK_DIR = resource("book")

TRIGRAMS = {
    1:("☰","Qián","Heaven",  "Creative",    "Father",      "Strong",      "乾"),
    2:("☱","Duì", "Lake",    "Joyous",      "3rd Daughter","Open",        "兌"),
    3:("☲","Lí",  "Fire",    "Clinging",    "2nd Daughter","Bright",      "離"),
    4:("☳","Zhèn","Thunder", "Arousing",    "1st Son",     "Movement",    "震"),
    5:("☴","Xùn", "Wind",    "Gentle",      "1st Daughter","Penetrating", "巽"),
    6:("☵","Kǎn", "Water",   "Abysmal",     "2nd Son",     "Dangerous",   "坎"),
    7:("☶","Gèn", "Mountain","Keeping Still","3rd Son",    "Resting",     "艮"),
    8:("☷","Kūn", "Earth",   "Receptive",   "Mother",      "Yielding",    "坤"),
}
HEX_CHARS = {
    1:"乾", 2:"坤", 3:"屯", 4:"蒙", 5:"需", 6:"訟", 7:"師", 8:"比",
    9:"小畜",10:"履",11:"泰",12:"否",13:"同人",14:"大有",15:"謙",16:"豫",
    17:"隨",18:"蠱",19:"臨",20:"觀",21:"噬嗑",22:"賁",23:"剝",24:"復",
    25:"無妄",26:"大畜",27:"頤",28:"大過",29:"坎",30:"離",31:"咸",32:"恆",
    33:"遯",34:"大壯",35:"晉",36:"明夷",37:"家人",38:"睽",39:"蹇",40:"解",
    41:"損",42:"益",43:"夬",44:"姤",45:"萃",46:"升",47:"困",48:"井",
    49:"革",50:"鼎",51:"震",52:"艮",53:"漸",54:"歸妹",55:"豐",56:"旅",
    57:"巽",58:"兌",59:"渙",60:"節",61:"中孚",62:"小過",63:"既濟",64:"未濟",
}
HEX_TABLE = {}
def _build_hex_table():
    data = [
        (1,1,1),(2,8,8),(3,6,4),(4,7,6),(5,6,1),(6,1,6),(7,6,8),(8,8,6),
        (9,5,1),(10,1,2),(11,8,1),(12,1,8),(13,1,3),(14,3,1),(15,8,7),(16,4,8),
        (17,2,4),(18,7,5),(19,8,2),(20,5,8),(21,3,4),(22,7,3),(23,7,8),(24,8,4),
        (25,1,4),(26,7,1),(27,7,4),(28,2,5),(29,6,6),(30,3,3),(31,2,7),(32,4,5),
        (33,1,7),(34,4,1),(35,3,8),(36,8,3),(37,5,3),(38,3,2),(39,6,7),(40,4,6),
        (41,7,2),(42,5,4),(43,2,1),(44,1,5),(45,2,8),(46,8,5),(47,2,6),(48,6,5),
        (49,2,3),(50,3,5),(51,4,4),(52,7,7),(53,5,7),(54,4,2),(55,4,3),(56,3,7),
        (57,5,5),(58,2,2),(59,5,6),(60,6,2),(61,5,2),(62,4,7),(63,6,3),(64,3,6),
    ]
    for hid,sup,inf in data: HEX_TABLE[(sup,inf)]=hid
_build_hex_table()

HEX_NAMES = {
    1:"Qián — The Creative",2:"Kūn — The Receptive",3:"Zhūn — Difficulty",
    4:"Méng — Youthful Folly",5:"Xū — Waiting",6:"Sòng — Conflict",
    7:"Shī — The Army",8:"Bǐ — Union",9:"Xiǎo Xù — Small Taming",
    10:"Lǚ — Treading",11:"Tài — Peace",12:"Pǐ — Standstill",
    13:"Tóng Rén — Fellowship",14:"Dà Yǒu — Great Possession",
    15:"Qiān — Modesty",16:"Yù — Enthusiasm",17:"Suí — Following",
    18:"Gǔ — Work on the Decayed",19:"Lín — Approach",20:"Guān — Contemplation",
    21:"Shì Hé — Biting Through",22:"Bì — Grace",23:"Bō — Splitting Apart",
    24:"Fù — Return",25:"Wú Wàng — Innocence",26:"Dà Xù — Great Taming",
    27:"Yí — Nourishment",28:"Dà Guò — Great Excess",29:"Kǎn — The Abysmal",
    30:"Lí — The Clinging",31:"Xián — Influence",32:"Héng — Duration",
    33:"Dùn — Retreat",34:"Dà Zhuàng — Great Power",35:"Jìn — Progress",
    36:"Míng Yí — Darkening",37:"Jiā Rén — The Family",38:"Kuí — Opposition",
    39:"Jiǎn — Obstruction",40:"Xiè — Deliverance",41:"Sǔn — Decrease",
    42:"Yì — Increase",43:"Guài — Breakthrough",44:"Gòu — Coming to Meet",
    45:"Cuì — Gathering",46:"Shēng — Pushing Upward",47:"Kùn — Oppression",
    48:"Jǐng — The Well",49:"Gé — Revolution",50:"Dǐng — The Cauldron",
    51:"Zhèn — The Arousing",52:"Gèn — Keeping Still",53:"Jiàn — Development",
    54:"Guī Mèi — The Marrying Maiden",55:"Fēng — Abundance",56:"Lǚ — The Wanderer",
    57:"Xùn — The Gentle",58:"Duì — The Joyous",59:"Huàn — Dispersion",
    60:"Jié — Limitation",61:"Zhōng Fú — Inner Truth",62:"Xiǎo Guò — Small Excess",
    63:"Jì Jì — After Completion",64:"Wèi Jì — Before Completion",
}

# ══════════════════════════════════════════════════════════════════════════════
# HEX MODEL
# ══════════════════════════════════════════════════════════════════════════════
class HexModel(QObject):
    changed = Signal()
    def __init__(self):
        super().__init__(); self.lines=[7,7,7,7,7,7]
    def set_lines(self,lines):
        self.lines=list(lines); self.changed.emit()
    def inf_id(self): return self._tri_id(self.lines[0:3])
    def sup_id(self): return self._tri_id(self.lines[3:6])
    def _tri_id(self,three):
        norm=[7 if v in (7,9) else 8 for v in three]
        tmap={(True,True,True):1,(False,True,True):2,(True,False,True):3,
              (False,False,True):4,(True,True,False):5,(False,True,False):6,
              (True,False,False):7,(False,False,False):8}
        return tmap.get(tuple(v==7 for v in norm),1)
    def hex_id(self): return HEX_TABLE.get((self.sup_id(),self.inf_id()),1)
    def has_moving(self): return any(v in (6,9) for v in self.lines)
    def relating_lines(self): return [7 if v==6 else 8 if v==9 else v for v in self.lines]
    def relating_id(self):
        if not self.has_moving(): return None
        rel=HexModel(); rel.lines=self.relating_lines()
        return HEX_TABLE.get((rel.sup_id(),rel.inf_id()),1)

from widgets import ZoomView
from journal import load_users, add_user

# ══════════════════════════════════════════════════════════════════════════════
# HEX DISPLAY — two column: primary | → | relating
#
# resizeEvent scales LineWidget instances and trigram grid columns
# proportionally so the display fills all available vertical space.
# ══════════════════════════════════════════════════════════════════════════════
class HexDisplay(QWidget):
    read_hex = Signal(int)
    width_hint = Signal(int)   # emits content width when columns change

    # Fixed content rows outside the 6 line widgets:
    # title(1) + divider(1) + tri_header(1) + tri_glyph(1) + tri_image(1) + tri_nature(1) + read_btn(1) = 7
    _FIXED_ROWS   = 7
    _TITLE_H      = 20   # px reserved for title row
    _DIV_H        = 8    # px for divider
    _TRI_ROW_H    = 22   # px per trigram row (3 rows)
    _BTN_H        = 30   # px for read button
    _MARGINS_V    = 16   # total top+bottom margins in the column
    _SPACING      = 3    # vl spacing

    def __init__(self, hex_model, parent=None):
        super().__init__(parent)
        self.hex = hex_model
        from cast import LineWidget
        self._LineWidget = LineWidget
        self.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Expanding)
        self._build()
        hex_model.changed.connect(self.refresh)

    def _build(self):
        main = QHBoxLayout(self)
        main.setContentsMargins(8, 8, 8, 8)
        main.setSpacing(0)

        self._prim_widget, self._prim_title, self._prim_lines, \
            self._prim_tri, self._prim_read_btn, self._prim_tri_grid = self._make_col()
        main.addWidget(self._prim_widget, 0)

        main.addSpacing(10)
        self._arrow = QLabel("→")
        self._arrow.setStyleSheet("font-size:20px;color:#555555;background:transparent;")
        self._arrow.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        self._arrow.setFixedWidth(30)
        self._arrow.setVisible(False)
        main.addWidget(self._arrow)
        main.addSpacing(10)

        self._rel_widget, self._rel_title, self._rel_lines, \
            self._rel_tri, self._rel_read_btn, self._rel_tri_grid = self._make_col()
        self._rel_widget.setVisible(False)
        main.addWidget(self._rel_widget, 0)

        main.addStretch(1)

    def _make_col(self):
        outer = QWidget()
        outer.setStyleSheet("background:transparent;")
        outer.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Expanding)
        vl = QVBoxLayout(outer)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(self._SPACING)

        title = QLabel("—")
        title.setStyleSheet(
            "font-size:12px;font-weight:bold;color:#1a1a1a;"
            "font-family:'AR PL UKai CN',sans-serif;background:transparent;")
        title.setAlignment(Qt.AlignCenter)
        vl.addWidget(title)

        lines = []
        for _ in range(6):
            lw = self._LineWidget()
            vl.addWidget(lw)
            lines.append(lw)

        div = QFrame()
        div.setFrameShape(QFrame.HLine)
        div.setStyleSheet("color:#c0c0bc;background:#c0c0bc;max-height:1px;margin:4px 0;")
        vl.addWidget(div)

        tri_grid = QGridLayout()
        tri_grid.setSpacing(2)
        tri_grid.setContentsMargins(0, 0, 0, 0)
        tri_grid.setHorizontalSpacing(4)

        tri_labels = {}
        for col, text in [(0,"▲"),(1,"Upper"),(2,"▼"),(3,"Lower")]:
            lbl = QLabel(text)
            lbl.setStyleSheet("font-size:12px;color:#888888;background:transparent;")
            tri_grid.addWidget(lbl, 0, col)
        for prefix, col_offset in [("sup",0),("inf",2)]:
            g = QLabel("☰")
            g.setStyleSheet("font-size:18px;color:#515150;background:transparent;")
            n = QLabel("—")
            n.setStyleSheet(
                "font-size:14px;font-weight:bold;color:#1a1a1a;"
                "font-family:'AR PL UKai CN',sans-serif;background:transparent;")
            tri_grid.addWidget(g, 1, col_offset)
            tri_grid.addWidget(n, 1, col_offset + 1)
            tri_labels[f"{prefix}_glyph"] = g
            tri_labels[f"{prefix}_name"]  = n
        for prefix, col_offset in [("sup",0),("inf",2)]:
            lbl = QLabel("—")
            lbl.setStyleSheet("font-size:13px;color:#555555;background:transparent;")
            tri_grid.addWidget(lbl, 2, col_offset, 1, 2)
            tri_labels[f"{prefix}_image"] = lbl
        for prefix, col_offset in [("sup",0),("inf",2)]:
            lbl = QLabel("—")
            lbl.setStyleSheet("font-size:13px;color:#777777;background:transparent;")
            tri_grid.addWidget(lbl, 3, col_offset, 1, 2)
            tri_labels[f"{prefix}_nature"] = lbl
        tri_grid.setColumnStretch(4, 1)   # phantom column absorbs slack; real cols stay at content width

        vl.addLayout(tri_grid)

        read_btn = QPushButton("Read this hex ▼")
        read_btn.setStyleSheet(
            "QPushButton{background:#515150;color:#fff;border:none;"
            "border-radius:4px;padding:4px 10px;font-size:10px;font-weight:bold;}"
            "QPushButton:hover{background:#3a3a39;}")
        read_btn.setEnabled(False)
        vl.addWidget(read_btn)

        return outer, title, lines, tri_labels, read_btn, tri_grid

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._rescale()

    def _rescale(self):
        """
        Scale hex line widgets vertically to fill available height.
        Width is fixed to the painted bar width (LineWidget.LINE_W) plus a
        margin for the moving-line marker — the bar is painted at LINE_W, so a
        wider widget would only add dead space and inflate the column.
        Only resizes this display's own line widgets.
        """
        h = self.height()
        if h < 50:
            return

        fixed_px = (self._MARGINS_V + self._TITLE_H + self._DIV_H +
                    (self._SPACING * 8) + (self._TRI_ROW_H * 4) + self._BTN_H)
        available = max(60, h - fixed_px)
        line_h = max(14, available // 6)
        line_w = self._LineWidget.LINE_W + 20   # bar (LINE_W) + moving-marker margin

        # Resize only this display's own line widgets
        for lw in self._prim_lines + self._rel_lines:
            try:
                lw.setFixedSize(line_w, line_h)
                lw.update()
            except RuntimeError:
                pass

    def _emit_width(self):
        """Flush layout and broadcast current content width so the parent
        stack can be capped to it (no gray dead zone on the casting view)."""
        lay = self.layout()
        if lay is not None:
            lay.activate()
        self.width_hint.emit(self.sizeHint().width())

    @staticmethod
    def _title_text(char, hid, name):
        """Two-line title: '<num>. <glyph> <pinyin>' over English."""
        if " — " in name:
            pinyin, eng = name.split(" — ", 1)
        else:
            pinyin, eng = name, ""
        head = f"{hid}.  {char}  {pinyin}" if char else f"{hid}.  {pinyin}"
        return f"{head}\n{eng}" if eng else head

    def _fill_trig(self, tri_labels, sup_id, inf_id):
        for prefix, tid in [("sup",sup_id),("inf",inf_id)]:
            t = TRIGRAMS.get(tid, TRIGRAMS[1])
            c = t[6] if len(t) > 6 else ""
            tri_labels[f"{prefix}_glyph"].setText(t[0])
            tri_labels[f"{prefix}_name"].setText(f"{c} {t[1]}" if c else t[1])
            tri_labels[f"{prefix}_image"].setText(t[2])
            tri_labels[f"{prefix}_nature"].setText(t[3])

    def refresh(self):
        hid = self.hex.hex_id()
        char = HEX_CHARS.get(hid, "")
        name = HEX_NAMES.get(hid, f"Hexagram {hid}")
        self._prim_title.setText(self._title_text(char, hid, name))
        for di, mi in enumerate(range(5,-1,-1)):
            self._prim_lines[di].set_value(self.hex.lines[mi])
        self._fill_trig(self._prim_tri, self.hex.sup_id(), self.hex.inf_id())
        self._prim_read_btn.setEnabled(True)
        try: self._prim_read_btn.clicked.disconnect()
        except: pass
        self._prim_read_btn.clicked.connect(lambda: self.read_hex.emit(hid))
        has_mov = self.hex.has_moving()
        self._arrow.setVisible(has_mov)
        self._rel_widget.setVisible(has_mov)
        if has_mov:
            rid = self.hex.relating_id()
            rchar = HEX_CHARS.get(rid, "")
            rname = HEX_NAMES.get(rid, f"Hexagram {rid}")
            self._rel_title.setText(self._title_text(rchar, rid, rname))
            rel_lines = self.hex.relating_lines()
            for di, mi in enumerate(range(5,-1,-1)):
                self._rel_lines[di].set_value(rel_lines[mi])
            rel = HexModel(); rel.lines = rel_lines
            self._fill_trig(self._rel_tri, rel.sup_id(), rel.inf_id())
            self._rel_read_btn.setEnabled(True)
            try: self._rel_read_btn.clicked.disconnect()
            except: pass
            self._rel_read_btn.clicked.connect(lambda: self.read_hex.emit(rid))
        self._emit_width()

    def set_line_partial(self, line_idx, value):
        self._prim_lines[5 - line_idx].set_value(value)
        hid = self.hex.hex_id()
        char = HEX_CHARS.get(hid, "")
        name = HEX_NAMES.get(hid, "")
        self._prim_title.setText(self._title_text(char, hid, name))
        self._fill_trig(self._prim_tri, self.hex.sup_id(), self.hex.inf_id())
        self._emit_width()

    def clear(self):
        self._prim_title.setText("—"); self._rel_title.setText("—")
        for lw in self._prim_lines: lw.clear()
        for lw in self._rel_lines:  lw.clear()
        self._arrow.setVisible(False); self._rel_widget.setVisible(False)
        self._prim_read_btn.setEnabled(False); self._rel_read_btn.setEnabled(False)
        self._emit_width()


# ══════════════════════════════════════════════════════════════════════════════
# BOOK BROWSER
# ══════════════════════════════════════════════════════════════════════════════
class BookBrowser(QWidget):
    def __init__(self, hex_model, author="wilhelm", parent=None):
        super().__init__(parent); self.hex=hex_model; self._author=author
        self._current_hex_id=1; self._section=0; self._active=False
        self._build()
        hex_model.changed.connect(self._on_hex_changed)

    def _build(self):
        vl=QVBoxLayout(self); vl.setContentsMargins(0,0,0,0); vl.setSpacing(4)
        bar=QHBoxLayout(); bar.setContentsMargins(6,4,6,0)
        self._section_lbl=QLabel("")
        self._section_lbl.setStyleSheet("font-size:12px;color:#555555;background:transparent;")
        bar.addWidget(self._section_lbl); bar.addStretch()
        btn_style=("QPushButton{background:#515150;color:#fff;border:none;"
            "border-radius:4px;padding:6px 14px;font-size:13px;font-weight:bold;}"
            "QPushButton:hover{background:#3a3a39;}")
        for label,delta in [("◀  Prev",-1),("Next  ▶",1)]:
            b=QPushButton(label); b.setStyleSheet(btn_style)
            b.clicked.connect(lambda _,d=delta: self._nav(d)); bar.addWidget(b)
        self._bar_widget=QWidget(); self._bar_widget.setLayout(bar)
        vl.addWidget(self._bar_widget)
        self.browser=ZoomView()
        self.browser.page().navigationRequested.connect(self._on_navigation)
        vl.addWidget(self.browser,1)

    def set_nav_visible(self,visible): self._bar_widget.setVisible(visible)
    def set_active(self,active): self._active=active

    def load_opening(self):
        """Load opening HTML. setBackgroundColor deferred via QTimer — avoids X11 hang."""
        self._active=False
        from PySide6.QtCore import QUrl, QTimer
        path=resource(os.path.join("content","opening_dark.html"))
        if not os.path.exists(path):
            path=resource(os.path.join("content","opening.html"))
        try:
            with open(path,encoding="utf-8") as f: html=f.read()
        except Exception as e: html=f"<p>Could not load opening: {e}</p>"
        html=html.replace("</head>",
            "<style>html,body{background:transparent!important;"
            "background-color:transparent!important;}</style></head>",1)
        self.browser.setHtml(html,QUrl.fromLocalFile(path))
        QTimer.singleShot(0, lambda: self.browser.page().setBackgroundColor(QColor(0,0,0,0)))

    def _on_hex_changed(self):
        if self._active:
            self._current_hex_id=self.hex.hex_id()
            self._section=0; self._load()

    def load_hex_id(self,hex_id,section=0):
        self._active=True
        self._current_hex_id=hex_id; self._section=section; self._load()

    def _nav(self,delta):
        self._section=max(0,min(7,self._section+delta)); self._load()

    def _load(self):
        hid=self._current_hex_id; sec=self._section
        fname=f"hex{hid}_0.html" if sec==0 else f"hex{hid}_{sec}.html"
        path=os.path.join(BOOK_DIR,"en",self._author,f"hex{hid}",fname)
        self._section_lbl.setText(f"Section {sec} of 6" if sec>0 else "Overview")
        self._load_file(path)

    def _load_file(self,path):
        if not os.path.exists(path):
            self.browser.setHtml(f"<p style='color:red'>Not found:<br>{path}</p>"); return
        try:
            with open(path,"r",encoding="utf-8",errors="replace") as f: html=f.read()
        except Exception as e:
            self.browser.setHtml(f"<p style='color:red'>{e}</p>"); return
        css="""body{background-color:#f8f8f6;font-family:Georgia,serif;
            font-size:15px;line-height:1.7;margin:16px 24px;}
            p.title{color:#515150;font-size:1.6em;font-weight:bold;font-style:italic;
            font-family:'aoyagireisyosimo2','AR PL UKai CN',Georgia,serif;margin-bottom:0.3em;line-height:1.4;}
            p.composition{color:#515150;font-size:1.1em;font-weight:bold;
            font-style:italic;margin-top:1em;margin-bottom:0.2em;}
            p.comment{color:#1a1a1a;font-size:1.0em;margin-top:0.4em;}
            p.sec{color:#515150;font-size:1.2em;font-weight:bold;
            font-style:italic;margin-top:1em;}
            p.text{color:#2a082a;font-size:1.0em;margin-top:0.3em;}
            .han{font-family:'aoyagireisyosimo2','AR PL UKai CN',serif;font-size:1.8em;
            vertical-align:middle;margin-right:0.2em;}
            em{font-style:italic;color:#515150;}a{color:#515150;}
            blockquote{margin-left:20px;border-left:2px solid #c0c0bc;
            padding-left:12px;color:#555;}"""
        html=re.sub(r'<LINK[^>]*>','',html,flags=re.IGNORECASE)
        html=html.replace("</head>",f"<style>{css}</style></head>",1)
        if path.endswith("_0.html") and f"hex{self._current_hex_id}_0" in path:
            try:
                from hexfig import inject_hex_figure
                html=inject_hex_figure(html,self._current_hex_id,size=28)
            except Exception: pass
        from PySide6.QtCore import QUrl
        self.browser.setHtml(html,QUrl.fromLocalFile(os.path.dirname(path)+os.sep))

    def _on_navigation(self,request):
        url=request.url(); path=url.toLocalFile()
        if path and path.endswith('.html') and 'hex' in path:
            request.reject(); self._load_file(path)
        else: request.accept()


# ══════════════════════════════════════════════════════════════════════════════
# NEW USER DIALOG
# ══════════════════════════════════════════════════════════════════════════════
class NewUserDialog(QDialog):
    def __init__(self,parent=None):
        super().__init__(parent); self.setWindowTitle("New User"); self.setMinimumWidth(340)
        self.setStyleSheet("QDialog{background:#f8f8f6;border-radius:10px;}"
            "QLabel{color:#1a1a1a;font-size:13px;background:transparent;}")
        self._alias=""; self._build()

    def _build(self):
        vl=QVBoxLayout(self); vl.setContentsMargins(24,20,24,20); vl.setSpacing(14)
        title=QLabel("Create New User")
        title.setStyleSheet("font-size:15px;font-weight:bold;color:#515150;background:transparent;")
        vl.addWidget(title); vl.addWidget(QLabel("Enter an alias:"))
        self._edit=QLineEdit(); self._edit.setPlaceholderText("alias…")
        self._edit.setStyleSheet("QLineEdit{background:#fff;color:#1a1a1a;"
            "border:1px solid #c0c0bc;border-radius:6px;font-size:14px;padding:7px 10px;}")
        self._edit.returnPressed.connect(self._accept_alias); vl.addWidget(self._edit)
        btn_row=QHBoxLayout(); btn_row.addStretch()
        cancel=QPushButton("Cancel")
        cancel.setStyleSheet("QPushButton{background:#e8e8e6;color:#1a1a1a;border:none;"
            "border-radius:6px;padding:7px 20px;font-size:13px;}"
            "QPushButton:hover{background:#d8d8d6;}")
        cancel.clicked.connect(self.reject)
        ok_btn=QPushButton("Create")
        ok_btn.setStyleSheet("QPushButton{background:#515150;color:#fff;border:none;"
            "border-radius:6px;padding:7px 20px;font-size:13px;font-weight:bold;}"
            "QPushButton:hover{background:#3a3a39;}")
        ok_btn.clicked.connect(self._accept_alias)
        btn_row.addWidget(cancel); btn_row.addWidget(ok_btn); vl.addLayout(btn_row)

    def _accept_alias(self):
        alias=self._edit.text().strip()
        if not alias: return
        if alias.lower()=="guest":
            QMessageBox.warning(self,"Reserved","'Guest' is reserved."); return
        self._alias=alias; self.accept()

    def alias(self): return self._alias


# ══════════════════════════════════════════════════════════════════════════════
# OPENING USER PANEL
# ══════════════════════════════════════════════════════════════════════════════
class OpeningUserPanel(QWidget):
    user_selected=Signal(bool)
    _PANEL_BG="transparent"
    _BTN_GHOST=("QPushButton{background:rgba(255,255,255,0.12);color:#e8d8a0;"
                "border:1px solid rgba(200,180,100,0.50);border-radius:5px;"
                "font-size:13px;padding:6px 12px;}"
                "QPushButton:hover{background:rgba(255,255,255,0.22);}")

    def __init__(self,parent=None):
        super().__init__(parent); self._users=[]; self._idx=-1
        self.setAttribute(Qt.WA_StyledBackground,True)
        self.setStyleSheet("background:transparent;")
        self._build()

    def _build(self):
        vl=QVBoxLayout(self); vl.setContentsMargins(16,24,16,16); vl.setSpacing(14)
        vl.addStretch()
        instr=QLabel("Please select a Profile and answer\nthe Questions to Unlock and\nProceed to the Oracle")
        instr.setStyleSheet("font-size:12px;color:#c0b080;background:transparent;")
        instr.setAlignment(Qt.AlignCenter); instr.setWordWrap(True)
        vl.addWidget(instr)
        lbl=QLabel("Who is consulting?")
        lbl.setStyleSheet("font-size:15px;color:#ffffff;background:transparent;")
        lbl.setAlignment(Qt.AlignCenter); vl.addWidget(lbl)
        row=QHBoxLayout(); row.setSpacing(6)
        self._prev_btn=QPushButton("◀"); self._prev_btn.setFixedWidth(34)
        self._prev_btn.setStyleSheet(self._BTN_GHOST); self._prev_btn.clicked.connect(self._prev)
        row.addWidget(self._prev_btn)
        self._name_btn=QPushButton("select user"); self._name_btn.setStyleSheet(self._unsel())
        self._name_btn.clicked.connect(self._next); row.addWidget(self._name_btn,1)
        self._next_btn=QPushButton("▶"); self._next_btn.setFixedWidth(34)
        self._next_btn.setStyleSheet(self._BTN_GHOST); self._next_btn.clicked.connect(self._next)
        row.addWidget(self._next_btn); vl.addLayout(row)
        new_btn=QPushButton("+ New User"); new_btn.setStyleSheet(self._BTN_GHOST)
        new_btn.clicked.connect(self._on_new_user); vl.addWidget(new_btn,0,Qt.AlignCenter)
        self._guest_lbl=QLabel("Guest session — readings will not be saved.")
        self._guest_lbl.setStyleSheet("font-size:11px;color:#c0b080;background:transparent;")
        self._guest_lbl.setAlignment(Qt.AlignCenter); self._guest_lbl.setWordWrap(True)
        self._guest_lbl.setVisible(False); vl.addWidget(self._guest_lbl)
        pmsg=QLabel("Edit your profile with details that improve "
            "the accuracy of your readings: Journal → Profile")
        pmsg.setStyleSheet("font-size:11px;color:#c0b080;background:transparent;")
        pmsg.setAlignment(Qt.AlignCenter); pmsg.setWordWrap(True)
        vl.addWidget(pmsg)
        vl.addStretch()
        self._users=load_users()

    def _unsel(self):
        return ("QPushButton{background:rgba(255,255,255,0.06);color:#a09060;"
                "border:1px solid rgba(200,180,100,0.30);border-radius:5px;"
                "font-size:14px;padding:6px 10px;}"
                "QPushButton:hover{background:rgba(255,255,255,0.12);}")
    def _sel(self):
        return ("QPushButton{background:rgba(255,255,255,0.18);color:#ffffff;"
                "border:1px solid rgba(200,180,100,0.70);border-radius:5px;"
                "font-size:15px;font-weight:bold;padding:6px 10px;}"
                "QPushButton:hover{background:rgba(255,255,255,0.26);}")

    def _slots(self): return list(self._users)+["Guest"]

    def _next(self):
        slots=self._slots()
        if not slots: return
        self._idx=0 if self._idx==-1 else (-1 if self._idx+1>=len(slots) else self._idx+1)
        self._update()

    def _prev(self):
        slots=self._slots()
        if not slots: return
        if self._idx==-1: self._idx=len(slots)-1
        elif self._idx==0: self._idx=-1
        else: self._idx-=1
        self._update()

    def _update(self):
        slots=self._slots()
        if self._idx==-1:
            self._name_btn.setText("select user"); self._name_btn.setStyleSheet(self._unsel())
            self._guest_lbl.setVisible(False); self.user_selected.emit(False)
        else:
            name=slots[self._idx]; self._name_btn.setText(name)
            self._name_btn.setStyleSheet(self._sel())
            self._guest_lbl.setVisible(name=="Guest"); self.user_selected.emit(True)

    def _on_new_user(self):
        dlg=NewUserDialog(self)
        if dlg.exec()!=QDialog.Accepted: return
        alias=dlg.alias()
        if not alias: return
        self._users=add_user(alias)
        slots=self._slots()
        if alias in slots: self._idx=slots.index(alias)
        self._update()

    def current_user(self):
        slots=self._slots()
        return None if self._idx==-1 or not slots else slots[self._idx]

    def select_user(self,alias):
        self._users=load_users()
        slots=self._slots()
        if alias in slots:
            self._idx=slots.index(alias); self._update()

    def reset(self):
        self._idx=-1; self._users=load_users()
        self._name_btn.setText("select user"); self._name_btn.setStyleSheet(self._unsel())
        self._guest_lbl.setVisible(False); self.user_selected.emit(False)


# ══════════════════════════════════════════════════════════════════════════════
# OPENING FORM PANEL
# paintEvent draws opening_image.png when in new_reading mode (image behind form only)
# ══════════════════════════════════════════════════════════════════════════════
class OpeningFormPanel(QWidget):
    proceed=Signal(str,str,dict)
    PURPOSE_OPTIONS=["Personal","Relationship","Work","Health","Creative","Spiritual","Decision","Other"]
    MOOD_OPTIONS=["Calm","Restless","Tired","Energised","Unwell","Focused","Scattered"]
    WEATHER_OPTIONS=["☀️ Sunny","☁️ Cloudy","🌧️ Rainy","💨 Windy","❄️ Snowing",
                     "🌡️ Hot","🌤️ Mild","🥶 Cold","💧 Humid","🏜️ Dry"]
    _BTN_OFF=("QPushButton{background:rgba(255,255,255,0.10);color:#e8d8a0;"
              "border:1px solid rgba(200,180,100,0.40);border-radius:3px;"
              "font-size:13px;padding:5px 9px;}"
              "QPushButton:hover{background:rgba(255,255,255,0.20);}")
    _BTN_ON=("QPushButton{background:#8b6914;color:#f0e8d0;"
             "border:1px solid #a07820;border-radius:3px;"
             "font-size:13px;padding:5px 9px;font-weight:bold;}"
             "QPushButton:hover{background:#a07820;}")
    _PROC_ON=("QPushButton{background:#8b6914;color:#f0e8d0;font-size:15px;"
              "font-weight:bold;border:none;border-radius:5px;padding:9px 28px;}"
              "QPushButton:hover{background:#a07820;}")
    _PROC_OFF=("QPushButton{background:rgba(100,80,40,0.35);"
               "color:rgba(200,180,120,0.45);font-size:15px;font-weight:bold;"
               "border:none;border-radius:5px;padding:9px 28px;}")

    def __init__(self,user_panel,parent=None):
        super().__init__(parent); self._user_panel=user_panel
        self._purpose_sel=set(); self._mood_sel=None; self._weather_sel=set()
        self._purpose_btns={}; self._mood_btns={}; self._weather_btns={}
        self._user_ready=False
        self.setAttribute(Qt.WA_StyledBackground,True)
        self.setStyleSheet("background:transparent;")
        self._bg_pixmap=QPixmap(resource("opening_image.png"))
        self._show_bg=False
        self._build()
        user_panel.user_selected.connect(self._on_user_selected)

    def set_show_bg(self,show):
        self._show_bg=show; self.update()

    def paintEvent(self,event):
        if self._show_bg and not self._bg_pixmap.isNull():
            p=QPainter(self)
            scaled=self._bg_pixmap.scaled(self.size(),Qt.KeepAspectRatioByExpanding,Qt.SmoothTransformation)
            x=(scaled.width()-self.width())//2; y=(scaled.height()-self.height())//2
            p.drawPixmap(0,0,scaled,x,y,self.width(),self.height()); p.end()
        super().paintEvent(event)

    def _build(self):
        vl=QVBoxLayout(self); vl.setContentsMargins(16,16,16,12); vl.setSpacing(8)
        instr=QLabel("Please answer the Questions below to Unlock and Proceed to the Oracle")
        instr.setStyleSheet("font-size:12px;color:#c0b080;background:transparent;")
        instr.setAlignment(Qt.AlignCenter); instr.setWordWrap(True)
        vl.addWidget(instr)
        self._question=QLineEdit()
        self._question.setPlaceholderText("What question do you bring to the oracle?")
        self._question.setStyleSheet("QLineEdit{background:rgba(255,255,255,0.12);color:#ffffff;"
            "font-size:14px;border:1px solid rgba(200,180,100,0.45);"
            "border-radius:4px;padding:7px 10px;}")
        self._question.textChanged.connect(self._check_proc_enabled)
        vl.addWidget(self._question)
        for section,opts,attr in [
            ("Purpose  (pick any)",self.PURPOSE_OPTIONS,"_purpose_btns"),
            ("Mood  (pick one)",   self.MOOD_OPTIONS,   "_mood_btns"),
            ("Weather  (pick any)",self.WEATHER_OPTIONS,"_weather_btns"),
        ]:
            lbl=QLabel(section)
            lbl.setStyleSheet("font-size:12px;color:#c0b080;background:transparent;")
            vl.addWidget(lbl)
            r=QHBoxLayout(); r.setSpacing(5); d={}
            for opt in opts:
                btn=QPushButton(opt); btn.setCheckable(True); btn.setStyleSheet(self._BTN_OFF)
                btn.clicked.connect(lambda checked,o=opt,a=attr: self._toggle(o,a))
                r.addWidget(btn); d[opt]=btn
            r.addStretch(); vl.addLayout(r); setattr(self,attr,d)
        vl.addSpacing(14)   # small gap below weather row; button sits up near questions
        pr=QHBoxLayout(); pr.addStretch()
        self._proc_btn=QPushButton("Proceed to the Oracle  ▶")
        self._proc_btn.setStyleSheet(self._PROC_OFF); self._proc_btn.setEnabled(False)
        self._proc_btn.clicked.connect(self._on_proceed); pr.addWidget(self._proc_btn)
        vl.addLayout(pr)

    def _on_user_selected(self,ready):
        self._user_ready=ready; self._check_proc_enabled()

    def set_user_ready(self,ready):
        self._user_ready=ready; self._check_proc_enabled()

    def _check_proc_enabled(self):
        has_question=bool(self._question.text().strip())
        has_purpose=bool(self._purpose_sel)
        has_mood=self._mood_sel is not None
        has_weather=bool(self._weather_sel)
        enabled=self._user_ready and has_question and has_purpose and has_mood and has_weather
        self._proc_btn.setEnabled(enabled)
        self._proc_btn.setStyleSheet(self._PROC_ON if enabled else self._PROC_OFF)

    def _set_proc_enabled(self,enabled):
        self._proc_btn.setEnabled(enabled)
        self._proc_btn.setStyleSheet(self._PROC_ON if enabled else self._PROC_OFF)

    def _toggle(self,opt,attr):
        d=getattr(self,attr)
        if attr=="_mood_btns":
            if self._mood_sel and self._mood_sel!=opt:
                d[self._mood_sel].setStyleSheet(self._BTN_OFF); d[self._mood_sel].setChecked(False)
            if self._mood_sel==opt:
                self._mood_sel=None; d[opt].setStyleSheet(self._BTN_OFF); d[opt].setChecked(False)
            else:
                self._mood_sel=opt; d[opt].setStyleSheet(self._BTN_ON); d[opt].setChecked(True)
        else:
            sel=self._purpose_sel if attr=="_purpose_btns" else self._weather_sel
            if opt in sel:
                sel.discard(opt); d[opt].setStyleSheet(self._BTN_OFF); d[opt].setChecked(False)
            else:
                sel.add(opt); d[opt].setStyleSheet(self._BTN_ON); d[opt].setChecked(True)
        self._check_proc_enabled()

    def reset(self):
        self._question.clear()
        for d in [self._purpose_btns,self._mood_btns,self._weather_btns]:
            for b in d.values(): b.setChecked(False); b.setStyleSheet(self._BTN_OFF)
        self._purpose_sel.clear(); self._mood_sel=None; self._weather_sel.clear()
        self._set_proc_enabled(False)

    def set_proceed_label(self,label): self._proc_btn.setText(label)

    def _on_proceed(self):
        username=self._user_panel.current_user()
        if not username: return
        question=self._question.text().strip()
        if not question: return
        moment={"question":question,"purpose":sorted(self._purpose_sel),
                "mood":self._mood_sel or "","weather":sorted(self._weather_sel)}
        self.proceed.emit(username,question,moment)


# ══════════════════════════════════════════════════════════════════════════════
# MAIN WINDOW
# ══════════════════════════════════════════════════════════════════════════════
class _CurrentPageStack(QStackedWidget):
    """QStackedWidget that sizes to the CURRENT page only (hint and minimum),
    instead of the tallest page. Keeps the hidden hex panel from inflating the
    short opening form's pane and wasting vertical space."""
    def __init__(self, *a):
        super().__init__(*a)
        self.currentChanged.connect(lambda _i: self.updateGeometry())
    def sizeHint(self):
        w = self.currentWidget()
        return w.sizeHint() if w else super().sizeHint()
    def minimumSizeHint(self):
        w = self.currentWidget()
        return w.minimumSizeHint() if w else super().minimumSizeHint()


class MainWindow(QMainWindow):
    MODE_OPENING="opening"; MODE_READER="reader"
    MODE_CASTING="casting"; MODE_NEW_READING="new_reading"
    MODE_STUDY="study"
    _WIDGET_MAX=16777215   # Qt QWIDGETSIZE_MAX — releases the casting-view width cap

    def __init__(self):
        super().__init__()
        self.hex=HexModel(); self._question=""; self._current_user="Guest"
        self._moment_data={}; self._mode=self.MODE_OPENING; self._last_entry_id=None
        self._study_page=None
        self._cast_started=False; self._cast_complete=False
        self._bg_pixmap=QPixmap(resource("opening_image.png"))
        self._build_ui(); self._build_menus()
        self.setWindowTitle(APP_NAME); self.resize(1100,750)
        self.hex.changed.connect(self._on_hex_changed)

    def paintEvent(self,event):
        """Full-window background image — opening mode only."""
        super().paintEvent(event)
        if self._mode==self.MODE_OPENING and not self._bg_pixmap.isNull():
            p=QPainter(self)
            scaled=self._bg_pixmap.scaled(self.size(),Qt.KeepAspectRatioByExpanding,Qt.SmoothTransformation)
            x=(scaled.width()-self.width())//2; y=(scaled.height()-self.height())//2
            p.drawPixmap(0,0,scaled,x,y,self.width(),self.height()); p.end()

    def _build_ui(self):
        central=QWidget(); self.setCentralWidget(central)
        vl=QVBoxLayout(central); vl.setContentsMargins(0,0,0,0); vl.setSpacing(0)
        self._main_stack=QStackedWidget()

        # Index 0: opening / casting
        oc=QWidget(); oc_vl=QVBoxLayout(oc); oc_vl.setContentsMargins(4,4,4,4); oc_vl.setSpacing(4)
        self._top_split=QSplitter(Qt.Horizontal); self._top_split.setChildrenCollapsible(False)

        # Left stack: user panel (0) / cast panel (1)
        self._left_stack=_CurrentPageStack()
        self._user_panel=OpeningUserPanel(); self._left_stack.addWidget(self._user_panel)
        from cast import LineWidget, CastPanel
        self._cast_panel=CastPanel(self.hex)
        self._cast_panel.line_cast.connect(self._on_line_cast)
        self._cast_panel.cast_done.connect(self._on_cast_done)
        self._cast_panel.new_reading.connect(self._new_reading)
        self._cast_panel.method_requested.connect(self._on_method_requested)
        self._cast_panel.setMinimumWidth(280); self._left_stack.addWidget(self._cast_panel)
        self._left_stack.setCurrentIndex(0); self._top_split.addWidget(self._left_stack)

        # Right stack: form (0) / hex display (1)
        self._right_stack=_CurrentPageStack()
        self._form_panel=OpeningFormPanel(self._user_panel)
        self._form_panel.proceed.connect(self._on_proceed)
        self._form_container=QWidget(); self._form_container.setMinimumWidth(240)
        fc_vl=QVBoxLayout(self._form_container); fc_vl.setContentsMargins(0,0,0,0)
        fc_vl.addWidget(self._form_panel)
        self._right_stack.addWidget(self._form_container)

        # Hex display panel — no addStretch, Expanding policy fills the frame
        self._hex_display=HexDisplay(self.hex)
        self._hex_display.read_hex.connect(self._on_read_hex)
        self._hex_display.width_hint.connect(self._on_hex_width)
        rf=QFrame()
        rf.setStyleSheet("QFrame{background:#f0f0ee;border-left:1px solid #c0c0bc;}")
        rf.setMinimumWidth(240)
        rf.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Expanding)
        rf_vl=QVBoxLayout(rf); rf_vl.setContentsMargins(8,4,8,8); rf_vl.setSpacing(0)
        ht=QLabel("Hexagram")
        ht.setStyleSheet("font-size:13px;font-weight:bold;color:#555555;background:transparent;")
        rf_vl.addWidget(ht)
        rf_vl.addWidget(self._hex_display, 1)   # stretch=1 — fills frame height
        self._right_stack.addWidget(rf); self._right_stack.setCurrentIndex(0)
        self._top_split.addWidget(self._right_stack)
        self._top_split.setStretchFactor(0,1); self._top_split.setStretchFactor(1,0)

        # Bottom tabs
        self._tabs=QTabWidget()
        self._tabs.setStyleSheet("""QTabBar::tab{padding:8px 22px;min-width:80px;
            background:#eeeeec;color:#555555;border-radius:4px 4px 0 0;margin-right:2px;}
            QTabBar::tab:selected{background:#515150;color:#fff;font-weight:bold;}""")
        self._browsers={}
        for key,author,label in SOURCES:
            b=BookBrowser(self.hex,author=author)
            self._browsers[key]=b
            setattr(self,f"_{key}_browser",b)
            self._tabs.addTab(b,label)
        for b in self._browsers.values():
            b.load_opening(); b.set_nav_visible(False)
        self._v_split=QSplitter(Qt.Vertical); self._v_split.setChildrenCollapsible(False)
        self._v_split.addWidget(self._top_split); self._v_split.addWidget(self._tabs)
        self._v_split.setStretchFactor(0, 0)
        self._v_split.setStretchFactor(1, 1)
        self._v_split.setSizes([320, 430])
        oc_vl.addWidget(self._v_split,1); self._main_stack.addWidget(oc)

        # Index 1: full reader
        self._reader_browser=ZoomView(); self._main_stack.addWidget(self._reader_browser)
        vl.addWidget(self._main_stack,1)
        self._status_bar=QStatusBar(); self.setStatusBar(self._status_bar)
        self._tabs.tabBar().setVisible(False)
        self._apply_opening_style()

    def _build_menus(self):
        mb=self.menuBar()
        jm=mb.addMenu("&Journal")
        jm.addAction("&Profile…",                self._show_profile)
        jm.addAction("&View Journal",             self._view_journal)
        jm.addSeparator()
        jm.addAction("&New Reading",              self._new_reading,    "Ctrl+N")
        jm.addAction("Manual Cast Entry",         self._show_manual_cast)
        jm.addSeparator()
        jm.addAction("&Export to PDF",            self._export_to_pdf,  "Ctrl+S")
        jm.addSeparator()
        jm.addAction("&Quit", self.close,         "Ctrl+Q")
        mb.addAction("&Practice").triggered.connect(self._show_practice)
        sm=mb.addMenu("&Study")
        sm.addAction("Hexagram Wheel", self._set_mode_study)
        sm.addSeparator()
        for label,fname in [
            ("繫辭上 · Great Treatise I",      "xici_1.html"),
            ("繫辭下 · Great Treatise II",     "xici_2.html"),
            ("說卦 · Trigrams Discussed",      "shuogua.html"),
            ("序卦 · Sequence",                "xugua.html"),
            ("雜卦 · Miscellaneous",           "zagua.html"),
        ]:
            sm.addAction(label, lambda _=False,f=fname: self._load_content_html(f))
        mb.addAction("&Commentaries").triggered.connect(self._show_commentaries)
        mb.addAction("&History").triggered.connect(self._show_history)
        hm=mb.addMenu("&Help")
        hm.addAction("&User Guide",lambda: self._load_content_html("help.html"))
        hm.addAction("&About",     lambda: self._load_content_html("about.html"))

    def _set_mode_opening(self):
        self._mode=self.MODE_OPENING
        self._main_stack.setCurrentIndex(0)
        self._left_stack.setCurrentIndex(0); self._right_stack.setCurrentIndex(0)
        self._right_stack.setMaximumWidth(self._WIDGET_MAX)
        self._top_split.setSizes([220,880])
        self._tabs.tabBar().setVisible(False)
        self._form_panel.set_show_bg(False)
        for b in self._browsers.values():
            b.set_nav_visible(False); b.set_active(False)
        self._apply_opening_style()
        self.update()

    def _set_mode_new_reading(self):
        self._cast_started=False; self._cast_complete=False
        self._mode=self.MODE_NEW_READING
        self._main_stack.setCurrentIndex(0)
        self._left_stack.setCurrentIndex(1)
        self._right_stack.setCurrentIndex(0)
        self._cast_panel.setEnabled(False)
        self._form_panel.reset()
        self._cast_panel.reset()
        self._form_panel.set_user_ready(True)
        self._form_panel.set_show_bg(True)
        self._form_panel.set_proceed_label("Begin New Reading  ▶")
        self._right_stack.setMaximumWidth(self._WIDGET_MAX)
        self._top_split.setSizes([420,680])
        self._tabs.tabBar().setVisible(True)
        for b in self._browsers.values():
            b.set_nav_visible(True)
        self._apply_casting_style()
        self.update()

    def _set_mode_reader(self,html,base_url=None):
        self._mode=self.MODE_READER
        from PySide6.QtCore import QUrl
        if base_url: self._reader_browser.setHtml(html,base_url)
        else: self._reader_browser.setHtml(html)
        self._main_stack.setCurrentIndex(1); self.update()

    def _set_mode_casting(self):
        self._mode=self.MODE_CASTING
        self._main_stack.setCurrentIndex(0)
        self._left_stack.setCurrentIndex(1); self._right_stack.setCurrentIndex(1)
        self._size_hex_pane()
        self._tabs.tabBar().setVisible(True)
        self._form_panel.set_show_bg(False)
        for b in self._browsers.values():
            b.set_nav_visible(True)
        self._form_panel.set_proceed_label("Proceed to the Oracle  ▶")
        self._apply_casting_style()
        self.update()

    _HEX_CHROME = 24   # rf margins (8+8) + border + slack around the hex columns

    def _size_hex_pane(self, content_w=None):
        """Cap the right stack to the hex columns' width AND hand the recovered
        width to the cast panel. Called on entering casting mode and whenever the
        hex content width changes, so the cast panel reclaims space as columns shrink."""
        if content_w is None:
            lay = self._hex_display.layout()
            if lay is not None:
                lay.activate()
            content_w = self._hex_display.sizeHint().width()
        cap = content_w + self._HEX_CHROME
        self._right_stack.setMaximumWidth(cap)
        total = self._top_split.width()
        if total > cap:
            self._top_split.setSizes([total - cap, cap])

    def _on_hex_width(self, w):
        if self._mode == self.MODE_CASTING:
            self._size_hex_pane(w)

    def _apply_opening_style(self):
        t="transparent"
        self._v_split.setStyleSheet("QSplitter{background:transparent;}QSplitter::handle{background:transparent;}")
        self._top_split.setStyleSheet("QSplitter{background:transparent;}QSplitter::handle{background:transparent;}")
        self._tabs.setStyleSheet(
            f"QTabWidget::pane{{background:{t};border:none;}}"
            f"QTabBar::tab{{background:{t};color:{t};border:none;"
            f"padding:8px 22px;min-width:80px;}}"
            f"QTabBar::tab:selected{{background:{t};}}")

    def _apply_casting_style(self):
        self._v_split.setStyleSheet("")
        self._top_split.setStyleSheet("")
        self._tabs.setStyleSheet(
            "QTabBar::tab{padding:8px 22px;min-width:80px;"
            "background:#eeeeec;color:#555555;"
            "border-radius:4px 4px 0 0;margin-right:2px;}"
            "QTabBar::tab:selected{background:#515150;color:#fff;font-weight:bold;}")

    def _on_proceed(self,username,question,moment_data):
        self._cast_started=False; self._cast_complete=False
        self._current_user=username; self._question=question; self._moment_data=moment_data
        self._cast_panel.set_user(username)
        self._cast_panel.set_alias(username)   # alias now lives in CastPanel header
        self._cast_panel.reset()
        self._cast_panel.setEnabled(True)
        self._hex_display.clear()
        self.hex.lines=[7,7,7,7,7,7]
        for b in self._browsers.values():
            b.set_active(True)
        self._right_stack.setCurrentIndex(1)
        self._set_mode_casting()
        self._status_bar.showMessage(
            "Welcome{}.  Cast a hexagram to begin.".format(
                ", "+username if username!="Guest" else ""),5000)

    def _load_content_html(self,content_file):
        from PySide6.QtCore import QUrl
        path=resource(os.path.join("content",content_file))
        try:
            with open(path,encoding="utf-8") as f: html=f.read()
        except Exception as e: html=f"<p>Could not load {content_file}: {e}</p>"
        self._set_mode_reader(html,QUrl.fromLocalFile(path))

    def _show_practice(self):     self._load_content_html("practice.html")
    def _show_commentaries(self): self._load_content_html("commentaries.html")
    def _show_history(self):      self._load_content_html("history.html")

    def _build_study_page(self):
        """Wheel + info panel. Built lazily on first Study visit."""
        from wheel import WheelWidget            # lazy: keep startup lean
        from PySide6.QtWidgets import (QHBoxLayout, QVBoxLayout, QWidget,
                                       QLabel, QPushButton, QFrame)
        page=QWidget(); page.setStyleSheet("background:#efe6d2;")
        hl=QHBoxLayout(page); hl.setContentsMargins(18,18,18,18); hl.setSpacing(18)

        self._wheel=WheelWidget(HEX_NAMES,HEX_CHARS)
        hl.addWidget(self._wheel,1)

        info=QFrame(); info.setFixedWidth(280)
        info.setStyleSheet("""QFrame{background:#f7f2e8;border:1px solid #5a4632;
            border-radius:8px;} QLabel{border:none;background:transparent;color:#3a2c1a;}""")
        il=QVBoxLayout(info); il.setContentsMargins(16,16,16,16); il.setSpacing(10)
        t=QLabel("Study the 64 Hexagrams"); t.setStyleSheet("font-size:17px;font-weight:bold;")
        t.setWordWrap(True); il.addWidget(t)
        ways=QLabel("Three ways to open a hexagram:\n\n"
                    "\u2022  Spin — let chance choose\n"
                    "\u2022  Drag the wheel and release\n"
                    "\u2022  Click a hexagram directly")
        ways.setStyleSheet("font-size:13px;line-height:1.5;"); ways.setWordWrap(True)
        il.addWidget(ways)
        self._study_spin=QPushButton("\u21bb  Spin the Wheel")
        self._study_spin.setStyleSheet("""QPushButton{background:#8b6f2e;color:#fff;
            font-size:14px;font-weight:bold;padding:10px;border:none;border-radius:6px;}
            QPushButton:hover{background:#a3853a;}""")
        il.addWidget(self._study_spin)
        il.addSpacing(8)
        self._study_id=QLabel(""); self._study_id.setWordWrap(True)
        self._study_id.setStyleSheet(
            "font-size:15px;font-weight:bold;font-family:'AR PL UKai CN',serif;")
        il.addWidget(self._study_id)
        il.addStretch()
        lk=QPushButton("Trigram Lookup")
        lk.setStyleSheet("""QPushButton{background:transparent;color:#5a4632;
            border:1px solid #5a4632;border-radius:5px;padding:7px;font-size:12px;}
            QPushButton:hover{background:#e6d9bd;}""")
        lk.clicked.connect(self._show_trigram_lookup)
        il.addWidget(lk)
        hl.addWidget(info,0)

        self._study_spin.clicked.connect(self._wheel.spin)
        self._wheel.selected.connect(self._show_study_hex)
        self._wheel.landed.connect(self._show_study_hex)
        self._wheel.hovered.connect(self._on_wheel_hover)
        return page

    def _on_wheel_hover(self,hid):
        if hid:
            self._study_id.setText(
                f"{hid} \u00b7 {HEX_CHARS.get(hid,'')}  {HEX_NAMES.get(hid,'')}")
        else:
            self._study_id.setText("")

    def _set_mode_study(self):
        if self._study_page is None:
            self._study_page=self._build_study_page()
            self._main_stack.addWidget(self._study_page)   # index 2
        self._mode=self.MODE_STUDY
        self._main_stack.setCurrentWidget(self._study_page)
        self._status_bar.showMessage("Study:  spin, drag, or click the wheel",5000)

    def _show_study_hex(self,hex_id):
        from PySide6.QtCore import QUrl
        path=os.path.join(BOOK_DIR,"en","wilhelm",f"hex{hex_id}",f"hex{hex_id}_0.html")
        if not os.path.exists(path):
            self._status_bar.showMessage(f"File not found for hex {hex_id}",3000); return
        try:
            with open(path,"r",encoding="utf-8",errors="replace") as f: html=f.read()
        except Exception as e: html=f"<p style='color:red'>{e}</p>"
        css="""body{background-color:#f8f8f6;font-family:Georgia,serif;font-size:15px;line-height:1.7;margin:16px 24px;}
            p.title{color:#515150;font-size:1.6em;font-weight:bold;font-style:italic;
            font-family:'aoyagireisyosimo2','AR PL UKai CN',Georgia,serif;line-height:1.4;}
            p.composition{color:#515150;font-size:1.1em;font-weight:bold;font-style:italic;margin-top:1em;}
            p.comment{color:#1a1a1a;font-size:1.0em;margin-top:0.4em;}
            p.sec{color:#515150;font-size:1.2em;font-weight:bold;font-style:italic;margin-top:1em;}
            p.text{color:#2a082a;font-size:1.0em;margin-top:0.3em;}
            .han{font-family:'aoyagireisyosimo2','AR PL UKai CN',serif;font-size:1.8em;vertical-align:middle;margin-right:0.2em;}
            em{font-style:italic;color:#515150;}"""
        html=re.sub(r'<LINK[^>]*>','',html,flags=re.IGNORECASE)
        html=html.replace("</head>",f"<style>{css}</style></head>",1)
        try:
            from hexfig import inject_hex_figure; html=inject_hex_figure(html,hex_id,size=28)
        except Exception: pass
        from PySide6.QtCore import QUrl
        self._set_mode_reader(html,QUrl.fromLocalFile(
            os.path.join(BOOK_DIR,"en","wilhelm",f"hex{hex_id}")+os.sep))
        self._status_bar.showMessage(f"Study:  Hexagram {hex_id} — {HEX_NAMES.get(hex_id,'')}",6000)

    def _on_read_hex(self,hex_id):
        if self._mode!=self.MODE_CASTING: self._set_mode_casting()
        for b in self._browsers.values():
            b.load_hex_id(hex_id)
        self._status_bar.showMessage(f"Reading:  Hexagram {hex_id} — {HEX_NAMES.get(hex_id,'')}",4000)

    def _on_line_cast(self,line_idx,value,coin_vals):
        self._cast_started=True
        self._right_stack.setCurrentIndex(1)
        self.hex.lines[line_idx]=value
        self.hex.changed.emit()
        t=('moving yin' if value==6 else 'yang' if value==7 else 'yin' if value==8 else 'moving yang')
        self._status_bar.showMessage(f"Line {line_idx+1} cast — coins: {coin_vals} = {value} ({t})",4000)

    def _on_cast_done(self):
        self._cast_complete=True
        lines=self._cast_panel.get_lines()
        self.hex.set_lines(lines)
        hid=self.hex.hex_id()
        for b in self._browsers.values():
            b.set_active(True); b.load_hex_id(hid)
        name=HEX_NAMES.get(hid,f"Hexagram {hid}")
        msg=f"Hexagram {hid} — {name}"
        if self.hex.has_moving():
            rid=self.hex.relating_id()
            msg+=f"  →  Hexagram {rid} — {HEX_NAMES.get(rid,'')}"
        if self._current_user!="Guest":
            from journal import auto_save_entry
            self._last_entry_id=auto_save_entry(
                self.hex,self._question,self._current_user,self._moment_data)
            self._status_bar.showMessage(msg+"  ·  Entry saved to journal.")
        else:
            self._status_bar.showMessage(msg)

    def _on_hex_changed(self):
        hid=self.hex.hex_id(); name=HEX_NAMES.get(hid,f"Hexagram {hid}")
        msg=f"Hexagram {hid}  —  {name}"
        if self.hex.has_moving():
            rid=self.hex.relating_id()
            msg+=f"  →  Hexagram {rid} — {HEX_NAMES.get(rid,'')}"
        self.setWindowTitle(f"{APP_NAME}  [{msg}]")

    def _new_reading(self): self._set_mode_new_reading()

    def _on_method_requested(self, index):
        if index == self._cast_panel.current_method():
            return                                  # already on this method
        if not self._cast_started:
            self._cast_panel.apply_method(index)    # no cast yet — free switch
        elif not self._cast_complete:
            QMessageBox.information(self, "Cast in Progress",
                "Please Complete the Current Cast before Switching")
        else:
            self._cast_panel.apply_method(index)    # completed reading — start a new one
            self._set_mode_new_reading()

    def _add_notes(self):
        if self._current_user=="Guest":
            QMessageBox.information(self,"Guest Session",
                "Select a user profile to save journal entries."); return
        if not self._last_entry_id:
            QMessageBox.information(self,"No Reading",
                "Complete a cast first — notes are saved to the most recent reading."); return
        from journal import AddNotesDialog
        dlg=AddNotesDialog(self._last_entry_id,self._current_user)
        dlg.show(); dlg.raise_()

    def _view_journal(self):
        from journal import JournalView
        jv=JournalView(self._current_user); jv.load_hex.connect(self._on_read_hex); jv.show(); jv.raise_()

    def _show_profile(self):
        from journal import ProfileDialog
        if self._current_user=="Guest":
            if QMessageBox.question(self,"Create Profile",
                    "You're in a Guest session.\n"
                    "Create a profile to save your readings?",
                    QMessageBox.Yes|QMessageBox.No)==QMessageBox.Yes:
                self._create_profile_flow()
            return
        ProfileDialog(self._current_user,self).exec()

    def _create_profile_flow(self):
        """Guest → new resident profile; the just-cast reading becomes its first entry."""
        from journal import add_user, ProfileDialog, auto_save_entry
        dlg=NewUserDialog(self)
        if dlg.exec()!=QDialog.Accepted: return
        alias=dlg.alias()
        if not alias: return
        add_user(alias)
        self._current_user=alias
        self._user_panel.select_user(alias)
        ProfileDialog(alias,self).exec()
        if getattr(self,"_cast_complete",False) and self._last_entry_id is None:
            self._last_entry_id=auto_save_entry(
                self.hex,self._question,alias,self._moment_data)
            self._status_bar.showMessage(
                f"Profile '{alias}' created — this reading saved as its first entry.")
        else:
            self._status_bar.showMessage(f"Profile '{alias}' created.")

    def closeEvent(self,ev):
        # Guest with an unsaved completed reading: offer to keep it before exit.
        if (self._current_user=="Guest" and getattr(self,"_cast_complete",False)
                and self._last_entry_id is None):
            if QMessageBox.question(self,"Before You Go",
                    "Would you like to create a user profile from the journal tab?",
                    QMessageBox.Yes|QMessageBox.No)==QMessageBox.Yes:
                ev.ignore(); self._create_profile_flow(); return
        ev.accept()

    def _show_manual_cast(self):
        dlg=ManualCastDialog(); dlg.cast_accepted.connect(self._on_manual_cast); dlg.show(); dlg.raise_()

    def _on_manual_cast(self,lines):
        self._new_reading(); self._pending_manual_lines=lines

    def _open_file(self):
        path,_=QFileDialog.getOpenFileName(self,"Open Reading","","YiJing readings (*.ich);;All files (*)")
        if not path: return
        try:
            with open(path,encoding="utf-8") as f:
                lines=[int(c) for c in f.readline().strip()[:6]]
            self.hex.set_lines(lines); self._cast_panel.reset()
            for i,v in enumerate(lines): self._cast_panel._line_widgets[i].set_value(v)
            self._cast_panel._lines=lines
            self._status_bar.showMessage(f"Loaded: {path}",3000)
        except Exception as e: QMessageBox.critical(self,"Error",str(e))

    def _export_to_pdf(self):
        from PySide6.QtWidgets import QFileDialog
        from datetime import datetime
        timestamp=datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name=f"yijing_reading_{timestamp}.pdf"
        path,_=QFileDialog.getSaveFileName(
            self,"Export Reading to PDF",default_name,
            "PDF files (*.pdf);;All files (*)")
        if not path: return
        if not path.endswith(".pdf"): path+=".pdf"
        tab_idx=self._tabs.currentIndex()
        browsers=list(self._browsers.values())
        if 0<=tab_idx<len(browsers):
            browsers[tab_idx].browser.page().printToPdf(path)
            self._status_bar.showMessage(f"Exported to {path}",4000)
        else:
            QMessageBox.information(self,"Export to PDF","Open a hexagram reading first.")

    def _show_trigram_lookup(self):
        dlg=TrigramLookup(); dlg.load_hex.connect(self._show_study_hex); dlg.show(); dlg.raise_()

    def _show_about(self):
        QMessageBox.about(self,f"About {APP_NAME}",
            f"<h2>{APP_NAME}</h2><p>Version {APP_VER}</p><hr>"
            "<p><b>Original software:</b><br>iching-0.2 by Jean Pierre Charalambos (2002)</p>"
            "<p><b>Coin casting engine:</b><br>pyChing by Stephen M. Gava (1999–2006)</p>"
            "<p><b>Translations:</b><br>Richard Wilhelm (1923) — English tr. Cary F. Baynes<br>"
            "James Legge (1899) — Sacred Books of the East</p>"
            "<p><b>Port and redesign:</b> archerprojects, 2026</p><hr>"
            "<p>GNU General Public License v3 or later.</p>")


# ══════════════════════════════════════════════════════════════════════════════
# TRIGRAM LOOKUP
# ══════════════════════════════════════════════════════════════════════════════
class TrigramLookup(QWidget):
    load_hex=Signal(int)
    def __init__(self,parent=None):
        super().__init__(parent,Qt.Window); self.setWindowTitle("Trigram Lookup")
        self.setFixedWidth(420); self._upper=1; self._lower=1; self._current_hid=None
        self._build(); self._update_result()

    def _build(self):
        vl=QVBoxLayout(self); vl.setContentsMargins(20,20,20,20); vl.setSpacing(14)
        def lbl(text,size=12,bold=False):
            l=QLabel(text); l.setStyleSheet(f"font-size:{size}px;{'font-weight:bold;' if bold else ''}color:#515150;"); return l
        vl.addWidget(lbl("Trigram Lookup",15,True))
        desc=QLabel("Select upper and lower trigrams to identify the hexagram.")
        desc.setStyleSheet("font-size:12px;color:#666;"); desc.setWordWrap(True); vl.addWidget(desc)
        vl.addWidget(lbl("Upper Trigram  (上卦)",12,True)); vl.addLayout(self._make_grid("upper"))
        vl.addWidget(lbl("Lower Trigram  (下卦)",12,True)); vl.addLayout(self._make_grid("lower"))
        self._result=QLabel("")
        self._result.setStyleSheet("font-size:15px;font-weight:bold;color:#515150;padding:10px;"
            "background:#f0f0ee;border:1px solid #c0c0bc;border-radius:4px;")
        self._result.setAlignment(Qt.AlignCenter); self._result.setWordWrap(True); vl.addWidget(self._result)
        row=QHBoxLayout()
        view_btn=QPushButton("Read This Hexagram")
        view_btn.setStyleSheet("QPushButton{background:#515150;color:#fff;border:none;"
            "padding:8px 20px;border-radius:3px;font-size:13px;}QPushButton:hover{background:#3a3a39;}")
        view_btn.clicked.connect(self._emit_hex)
        close_btn=QPushButton("Close"); close_btn.clicked.connect(self.close)
        row.addWidget(close_btn); row.addWidget(view_btn); vl.addLayout(row)

    def _make_grid(self,which):
        grid=QHBoxLayout(); grid.setSpacing(6); buttons=[]
        for tid in range(1,9):
            t=TRIGRAMS[tid]; btn=QPushButton(f"{t[0]}\n{t[6]} {t[1]}\n{t[2]}")
            btn.setCheckable(True); btn.setFixedSize(46,60)
            btn.setStyleSheet("QPushButton{font-size:10px;border:1px solid #c0c0bc;"
                "border-radius:3px;background:#f8f8f6;color:#1a1a1a;padding:2px;}"
                "QPushButton:checked{background:#515150;color:#fff;border-color:#515150;}"
                "QPushButton:hover:!checked{background:#e8e8e6;}")
            btn.setChecked(tid==1)
            btn.clicked.connect(lambda checked,t=tid,w=which: self._select(w,t))
            grid.addWidget(btn); buttons.append(btn)
        if which=="upper": self._upper_btns=buttons
        else: self._lower_btns=buttons
        return grid

    def _select(self,which,tid):
        if which=="upper":
            self._upper=tid
            for i,btn in enumerate(self._upper_btns): btn.setChecked(i+1==tid)
        else:
            self._lower=tid
            for i,btn in enumerate(self._lower_btns): btn.setChecked(i+1==tid)
        self._update_result()

    def _update_result(self):
        hid=HEX_TABLE.get((self._upper,self._lower))
        if hid:
            sup=TRIGRAMS[self._upper]; inf=TRIGRAMS[self._lower]
            self._result.setText(f"{HEX_CHARS.get(hid,'')}  {hid}. {HEX_NAMES.get(hid,'')}\n"
                f"{sup[0]} {sup[1]} over {inf[0]} {inf[1]}")
            self._current_hid=hid
        else: self._result.setText("—"); self._current_hid=None

    def _emit_hex(self):
        if self._current_hid: self.load_hex.emit(self._current_hid); self.close()


# ══════════════════════════════════════════════════════════════════════════════
# MANUAL CAST ENTRY
# ══════════════════════════════════════════════════════════════════════════════
class ManualCastDialog(QWidget):
    cast_accepted=Signal(list)
    LINE_LABELS={6:"⚋×  6 — Old Yin (moving)",7:"⚊   7 — Young Yang (stable)",
                 8:"⚋   8 — Young Yin (stable)",9:"⚊○  9 — Old Yang (moving)"}

    def __init__(self,parent=None):
        super().__init__(parent,Qt.Window); self.setWindowTitle("Manual Cast Entry")
        self.setFixedWidth(400); self._selectors=[]; self._build()

    def _build(self):
        vl=QVBoxLayout(self); vl.setContentsMargins(20,20,20,20); vl.setSpacing(12)
        title=QLabel("Manual Cast Entry")
        title.setStyleSheet("font-size:15px;font-weight:bold;color:#515150;"); vl.addWidget(title)
        desc=QLabel("Enter the value for each line.\nLines numbered bottom (1) to top (6).")
        desc.setStyleSheet("font-size:12px;color:#666;"); desc.setWordWrap(True); vl.addWidget(desc)
        grid=QGridLayout(); grid.setSpacing(8)
        for col,txt in enumerate(["Line","Value","Type"]):
            l=QLabel(txt); l.setStyleSheet("font-size:11px;font-weight:bold;color:#888;"); grid.addWidget(l,0,col)
        self._type_labels=[]
        for i in range(6):
            lbl=QLabel(f"Line {i+1}  {'(bottom)' if i==0 else '(top)' if i==5 else ''}")
            lbl.setStyleSheet("font-size:12px;color:#1a1a1a;"); grid.addWidget(lbl,i+1,0)
            br=QHBoxLayout(); br.setSpacing(4); btns=[]
            for v in (6,7,8,9):
                btn=QPushButton(str(v)); btn.setCheckable(True); btn.setFixedSize(32,28)
                btn.setStyleSheet("QPushButton{border:1px solid #c0c0bc;border-radius:3px;"
                    "font-size:12px;font-weight:bold;background:#f8f8f6;}"
                    "QPushButton:checked{background:#515150;color:#fff;border-color:#515150;}"
                    "QPushButton:hover:!checked{background:#e8e8e6;}")
                btn.setChecked(v==7)
                btn.clicked.connect(lambda _,row=i,val=v: self._select(row,val))
                btns.append(btn); br.addWidget(btn)
            bw=QWidget(); bw.setLayout(br); grid.addWidget(bw,i+1,1)
            tl=QLabel(self.LINE_LABELS[7]); tl.setStyleSheet("font-size:11px;color:#515150;")
            grid.addWidget(tl,i+1,2); self._selectors.append({'buttons':btns,'value':7}); self._type_labels.append(tl)
        vl.addLayout(grid)
        quick=QHBoxLayout(); ql=QLabel("Quick set all:"); ql.setStyleSheet("font-size:11px;color:#888;"); quick.addWidget(ql)
        for v,label in [(7,"All Yang"),(8,"All Yin")]:
            btn=QPushButton(label)
            btn.setStyleSheet("QPushButton{border:1px solid #c0c0bc;padding:2px 8px;"
                "font-size:11px;border-radius:3px;background:#f0f0ee;}"
                "QPushButton:hover{background:#e4e4e2;}")
            btn.clicked.connect(lambda _,val=v: self._set_all(val)); quick.addWidget(btn)
        quick.addStretch(); vl.addLayout(quick)
        self._preview=QLabel(""); self._preview.setStyleSheet("font-size:13px;font-weight:bold;"
            "color:#515150;padding:8px;background:#f0f0ee;border:1px solid #c0c0bc;border-radius:4px;")
        self._preview.setAlignment(Qt.AlignCenter); vl.addWidget(self._preview); self._update_preview()
        row2=QHBoxLayout(); row2.addStretch()
        cancel=QPushButton("Cancel"); cancel.clicked.connect(self.close)
        accept=QPushButton("Accept Reading")
        accept.setStyleSheet("QPushButton{background:#515150;color:#fff;border:none;"
            "padding:8px 20px;border-radius:3px;font-size:13px;}QPushButton:hover{background:#3a3a39;}")
        accept.clicked.connect(self._accept); row2.addWidget(cancel); row2.addWidget(accept); vl.addLayout(row2)

    def _select(self,row,val):
        self._selectors[row]['value']=val
        for i,btn in enumerate(self._selectors[row]['buttons']): btn.setChecked(i+6==val)
        self._type_labels[row].setText(self.LINE_LABELS[val]); self._update_preview()

    def _set_all(self,val):
        for i in range(6): self._select(i,val)

    def _update_preview(self):
        lines=[s['value'] for s in self._selectors]
        try:
            tmap={(True,True,True):1,(False,True,True):2,(True,False,True):3,
                  (False,False,True):4,(True,True,False):5,(False,True,False):6,
                  (True,False,False):7,(False,False,False):8}
            def tri(l1,l2,l3): return tmap.get((l1%2==1,l2%2==1,l3%2==1),1)
            inf=tri(lines[0],lines[1],lines[2]); sup=tri(lines[3],lines[4],lines[5])
            hid=HEX_TABLE.get((sup,inf),1); moving=[i+1 for i,v in enumerate(lines) if v in (6,9)]
            mv=f"  Moving: {moving}" if moving else "  No moving lines"
            self._preview.setText(f"{HEX_CHARS.get(hid,'')} {hid}. {HEX_NAMES.get(hid,'')}{mv}")
        except Exception: self._preview.setText("—")

    def _accept(self):
        self.cast_accepted.emit([s['value'] for s in self._selectors]); self.close()


# ══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════
def main():
    app=QApplication(sys.argv)
    app.setApplicationName(APP_NAME); app.setApplicationVersion(APP_VER)
    _ukai_id=QFontDatabase.addApplicationFont(resource("ukai_yijing.ttf"))
    if _ukai_id<0: print("Warning: AR PL UKai CN font could not be loaded")
    _aoyagi_id=QFontDatabase.addApplicationFont(resource("aoyagi_yijing.ttf"))
    if _aoyagi_id<0:
        print("Warning: Aoyagi heading font could not be loaded")
    else:
        _fams=QFontDatabase.applicationFontFamilies(_aoyagi_id)
        global AOYAGI_FAMILY
        if _fams: AOYAGI_FAMILY=_fams[0]
        print(f"Aoyagi heading font family: {AOYAGI_FAMILY}")
    palette=QPalette()
    palette.setColor(QPalette.Window,QColor("#f8f8f6"))
    palette.setColor(QPalette.WindowText,QColor("#1a1a1a"))
    palette.setColor(QPalette.Base,QColor("#ffffff"))
    palette.setColor(QPalette.AlternateBase,QColor("#f0f0ee"))
    palette.setColor(QPalette.Text,QColor("#1a1a1a"))
    palette.setColor(QPalette.Button,QColor("#eeeeec"))
    palette.setColor(QPalette.ButtonText,QColor("#1a1a1a"))
    palette.setColor(QPalette.Highlight,QColor("#515150"))
    palette.setColor(QPalette.HighlightedText,QColor("#ffffff"))
    app.setPalette(palette)
    win=MainWindow(); win.show(); sys.exit(app.exec())

if __name__=="__main__":
    main()
