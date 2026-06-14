"""
The YiJing — Navigating Change
hexfig.py — SVG hexagram figure generator

Version 2.8.9
GNU GPL v3
"""

_TRIGRAM_LINES = {
    1: [7, 7, 7],  # Heaven  all yang
    2: [8, 7, 7],  # Lake    yin,yang,yang
    3: [7, 8, 7],  # Fire    yang,yin,yang
    4: [8, 8, 7],  # Thunder yin,yin,yang
    5: [7, 7, 8],  # Wind    yang,yang,yin
    6: [8, 7, 8],  # Water   yin,yang,yin
    7: [7, 8, 8],  # Mountain yang,yin,yin
    8: [8, 8, 8],  # Earth   all yin
}

_HEX_TABLE = {}
_RAW = [
    (1,1,1),(2,8,8),(3,6,4),(4,7,6),(5,6,1),(6,1,6),(7,6,8),(8,8,6),
    (9,5,1),(10,1,2),(11,8,1),(12,1,8),(13,1,3),(14,3,1),(15,8,7),(16,4,8),
    (17,2,4),(18,7,5),(19,8,2),(20,5,8),(21,3,4),(22,7,3),(23,7,8),(24,8,4),
    (25,1,4),(26,7,1),(27,7,4),(28,2,5),(29,6,6),(30,3,3),(31,2,7),(32,4,5),
    (33,1,7),(34,4,1),(35,3,8),(36,8,3),(37,5,3),(38,3,2),(39,6,7),(40,4,6),
    (41,7,2),(42,5,4),(43,2,1),(44,1,5),(45,2,8),(46,8,5),(47,2,6),(48,6,5),
    (49,2,3),(50,3,5),(51,4,4),(52,7,7),(53,5,7),(54,4,2),(55,4,3),(56,3,7),
    (57,5,5),(58,2,2),(59,5,6),(60,6,2),(61,5,2),(62,4,7),(63,6,3),(64,3,6),
]
for _hid, _sup, _inf in _RAW:
    _HEX_TABLE[_hid] = (_sup, _inf)


def hex_lines(hex_id):
    sup_id, inf_id = _HEX_TABLE.get(hex_id, (1, 1))
    return _TRIGRAM_LINES[inf_id] + _TRIGRAM_LINES[sup_id]


def hex_svg(hex_id, size=28):
    """
    Return an inline SVG string showing the hexagram figure.
    Designed to sit inline — vertical-align:middle — next to title text.
    """
    lines  = hex_lines(hex_id)
    w      = int(size * 1.4)
    h      = size
    tri_gap  = max(2, size // 10)
    line_h   = max(2, size // 9)
    gap      = max(1, size // 14)
    break_w  = max(3, size // 9)
    pad_x    = 1
    colour   = "#1a1a1a"

    total_line_h = 6 * line_h + 4 * gap + tri_gap
    start_y = max(0, (h - total_line_h) // 2)

    rects = []
    y = start_y + total_line_h

    for i in range(6):
        y -= line_h
        lv = lines[i]
        if lv == 7:
            rects.append(
                f'<rect x="{pad_x}" y="{y}" '
                f'width="{w - 2*pad_x}" height="{line_h}" '
                f'fill="{colour}"/>')
        else:
            bar_w = (w - 2*pad_x - break_w) // 2
            rects.append(
                f'<rect x="{pad_x}" y="{y}" '
                f'width="{bar_w}" height="{line_h}" '
                f'fill="{colour}"/>')
            rects.append(
                f'<rect x="{pad_x + bar_w + break_w}" y="{y}" '
                f'width="{bar_w}" height="{line_h}" '
                f'fill="{colour}"/>')
        if i == 2:
            y -= tri_gap
        elif i < 5:
            y -= gap

    body = "\n  ".join(rects)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" '
        f'style="display:inline-block;vertical-align:middle;'
        f'margin-right:6px;">'
        f'\n  {body}\n'
        f'</svg>'
    )


def inject_hex_figure(html, hex_id, size=28):
    """
    Inject SVG figure inline inside <p class="title">, as the first child.
    The figure, Chinese character, and title text all sit on one line.
    """
    import re
    svg = hex_svg(hex_id, size)

    # Match opening <p class="title"> tag (with optional other attrs, single or double quotes)
    pattern = re.compile(
        r'(<p\s+class=["\']title["\'][^>]*>)', re.IGNORECASE)

    def insert_svg(m):
        return m.group(1) + svg

    modified, n = pattern.subn(insert_svg, html, count=1)
    if n == 0:
        return html
    return modified
