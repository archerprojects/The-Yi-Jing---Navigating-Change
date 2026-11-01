"""
The YiJing — Navigating Change
weighting.py — Factor weighting for the cast (no Qt; plain Python)

Version 1.1.0 — Monday 2 November 2026
GNU GPL v3

With weighting off nothing here is used and the cast keeps the classical odds.
With it on, the odds of the four line types are shifted, within fixed limits:
  direction  — the yin-yang cycle (time of day, season, moon phase) leans the
               odds toward the stage the moment is in;
  change     — the asker's state (mood and the research-weighted inputs) moves
               the share of moving lines (6 and 9) up or down.
The circadian model is ported from Cosmic Scout's cycles.py (same developer,
GPL-3.0). Astronomy is low-precision Meeus, accurate to well under a degree.
"""

import math
from datetime import datetime, timezone, date

# ══════════════════════════════════════════════════════════════════════════════
# THE TABLE — every default in one place (Journal → Factor Weighting)
# ══════════════════════════════════════════════════════════════════════════════
# (key, label, group, evidence, default, minimum, maximum, unit)
FACTORS = [
    ("time_of_day",   "Time of day",               "direction", "Our analogy to Zhu Xi's seasons",          1.0,  0, 1,   ""),
    ("season",        "Season and solar term",     "direction", "Zhu Xi, Zhuzi Yulei 137",                  1.0,  0, 1,   ""),
    ("moon_phase",    "Moon phase",                "direction", "Cantong qi, chapter 18",                   1.0,  0, 1,   ""),
    ("mood",          "Mood",                      "change",    "Your own report of your state",            1.0,  0, 1,   ""),
    ("sleep",         "Sleep last night",          "change",    "Strong — Palmer et al. 2021",              1.0,  0, 1,   ""),
    ("daylight",      "Daylight",                  "change",    "Strong — Golden et al. 2005; UK Biobank",  0.8,  0, 1,   ""),
    ("circadian",     "Body clock (circadian)",    "change",    "Moderate — Murray et al. 2009",            0.6,  0, 1,   ""),
    ("red_light",     "Red / near-infrared light", "change",    "Emerging — Ji et al. 2024",                0.4,  0, 1,   ""),
    ("weather",       "Weather (beyond light)",    "change",    "Small — Denissen et al. 2008",             0.25, 0, 1,   ""),
    ("menstrual",     "Menstrual cycle",           "change",    "Weak — Romans et al. 2012",                0.1,  0, 1,   ""),
    ("ultradian",     "Ultradian (~90 min)",       "change",    "Weak — waking rhythms vary",               0.1,  0, 1,   ""),
    ("lunar_gravity", "Lunar gravity",             "change",    "Weak — Wehr 2018",                         0.1,  0, 1,   ""),
    ("direction_share", "Direction's share of the shift", "limits", "Half direction, half change",          50,   0, 100, "%"),
    ("limit_subtle",  "Largest shift — Subtle",    "limits",    "Of each line type's classical odds",       15,   0, 100, "%"),
    ("limit_moderate","Largest shift — Moderate",  "limits",    "Of each line type's classical odds",       30,   0, 100, "%"),
    ("limit_strong",  "Largest shift — Strong",    "limits",    "Of each line type's classical odds",       50,   0, 100, "%"),
    ("floor",         "Floor",                     "limits",    "Lowest share of the classical odds kept",  50,   0, 100, "%"),
]
WEIGHT_DEFAULTS = {f[0]: f[4] for f in FACTORS}
STRENGTHS = ("Subtle", "Moderate", "Strong")

CLASSICAL = {
    "yarrow": {6: 1/16, 7: 5/16, 8: 7/16, 9: 3/16},
    "coin":   {6: 1/8,  7: 3/8,  8: 3/8,  9: 1/8},
}
LINE_TYPES = (6, 7, 8, 9)
# the four line types as stages of one cycle (fraction of a turn)
_STAGE = {7: 0.0, 9: 0.25, 8: 0.5, 6: 0.75}

LIGHT_TYPES = (("daylight", "Daylight outdoors"), ("screen", "Bright / screen (blue-rich)"),
               ("warm", "Warm / dim indoor"), ("red", "Red / near-infrared therapy"))
LIGHT_PERIODS = ("Morning", "Midday", "Afternoon", "Evening", "Night")


def table_for(saved):
    """The defaults with a profile's saved values laid over them (bad values ignored)."""
    t = dict(WEIGHT_DEFAULTS)
    for key, _l, _g, _e, _d, lo, hi, _u in FACTORS:
        v = (saved or {}).get(key)
        if isinstance(v, (int, float)) and lo <= v <= hi:
            t[key] = float(v)
    return t


def is_default(table):
    return all(abs(table[k] - WEIGHT_DEFAULTS[k]) < 0.005 for k in WEIGHT_DEFAULTS)   # table shows 2 decimals


def _clamp(v, lo=-1.0, hi=1.0):
    return max(lo, min(hi, v))


# ══════════════════════════════════════════════════════════════════════════════
# ASTRONOMY (Meeus, low precision)
# ══════════════════════════════════════════════════════════════════════════════
_EPS = math.radians(23.4393)

def _jd(when):
    """Julian day of an aware datetime."""
    u = when.astimezone(timezone.utc)
    return 2440587.5 + u.timestamp() / 86400.0

def _sin(d): return math.sin(math.radians(d))
def _cos(d): return math.cos(math.radians(d))

def sun_longitude(when):
    """Apparent ecliptic longitude of the sun, degrees (0 = March equinox)."""
    T = (_jd(when) - 2451545.0) / 36525.0
    L0 = 280.46646 + 36000.76983 * T
    M = 357.52911 + 35999.05029 * T
    C = ((1.914602 - 0.004817 * T) * _sin(M) + 0.019993 * _sin(2 * M)
         + 0.000289 * _sin(3 * M))
    om = 125.04 - 1934.136 * T
    return (L0 + C - 0.00569 - 0.00478 * _sin(om)) % 360.0

def moon_state(when):
    """Moon longitude and latitude (deg), distance (km), declination (deg),
    and elongation from the sun (deg; 0 new, 180 full)."""
    T = (_jd(when) - 2451545.0) / 36525.0
    Lp = 218.3164477 + 481267.88123421 * T
    D = 297.8501921 + 445267.1114034 * T
    M = 357.5291092 + 35999.0502909 * T
    Mp = 134.9633964 + 477198.8675055 * T
    F = 93.2720950 + 483202.0175233 * T
    lon = (Lp + 6.289 * _sin(Mp) + 1.274 * _sin(2 * D - Mp) + 0.658 * _sin(2 * D)
           + 0.214 * _sin(2 * Mp) - 0.186 * _sin(M) - 0.114 * _sin(2 * F)) % 360.0
    lat = (5.128 * _sin(F) + 0.281 * _sin(Mp + F) + 0.278 * _sin(Mp - F)
           + 0.173 * _sin(2 * D - F))
    dist = (385000.56 - 20905.355 * _cos(Mp) - 3699.111 * _cos(2 * D - Mp)
            - 2955.968 * _cos(2 * D) - 569.925 * _cos(2 * Mp))
    dec = math.degrees(math.asin(_sin(lat) * math.cos(_EPS)
                                 + _cos(lat) * math.sin(_EPS) * _sin(lon)))
    elong = (lon - sun_longitude(when)) % 360.0
    return {"lon": lon, "lat": lat, "dist": dist, "dec": dec, "elong": elong}

def day_length(when, latitude):
    """Hours of daylight at a latitude on the date of `when`."""
    dec = math.asin(math.sin(_EPS) * _sin(sun_longitude(when)))
    x = -math.tan(math.radians(latitude)) * math.tan(dec)
    return 24.0 if x <= -1 else 0.0 if x >= 1 else 2 * math.degrees(math.acos(x)) / 15.0

SOLAR_TERMS = ["春分", "清明", "穀雨", "立夏", "小滿", "芒種", "夏至", "小暑", "大暑",
               "立秋", "處暑", "白露", "秋分", "寒露", "霜降", "立冬", "小雪", "大雪",
               "冬至", "小寒", "大寒", "立春", "雨水", "驚蟄"]

def solar_term(when):
    """The solar term most recently begun (terms every 15°, 春分 at 0°)."""
    return SOLAR_TERMS[int(sun_longitude(when) // 15) % 24]

def season_name(when, south=False):
    lam = (sun_longitude(when) + (180.0 if south else 0.0)) % 360.0
    # Chinese seasons begin at 立春 (315°), 立夏 (45°), 立秋 (135°), 立冬 (225°)
    if lam >= 315 or lam < 45: return "Spring"
    if lam < 135: return "Summer"
    if lam < 225: return "Autumn"
    return "Winter"

def tide(when):
    """Relative lunisolar tidal strength, 0 (neap at apogee) .. 1 (spring at perigee)."""
    m = moon_state(when)
    M = (384400.0 / m["dist"]) ** 3          # lunar tide, 1 at mean distance
    S = 0.46                                  # solar tide relative to the mean lunar one
    amp = math.sqrt(M * M + S * S + 2 * M * S * _cos(2 * m["elong"]))
    lo = (384400.0 / 406700.0) ** 3 - S
    hi = (384400.0 / 356400.0) ** 3 + S
    return _clamp((amp - lo) / (hi - lo), 0.0, 1.0), m


# ══════════════════════════════════════════════════════════════════════════════
# CIRCADIAN — ported from Cosmic Scout cycles.py
# ══════════════════════════════════════════════════════════════════════════════
_T_AMP = {"young": 1.00, "prime": 0.85, "middle": 0.62, "older": 0.40}
_MEL_AMP = {"young": 1.00, "prime": 0.92, "middle": 0.78, "older": 0.60}
_PHASE_SHIFT = {"young": +0.6, "prime": 0.0, "middle": -0.4, "older": -0.9}

def age_bracket(age):
    if age is None: return "prime"
    if age < 30: return "young"
    if age < 45: return "prime"
    if age < 60: return "middle"
    return "older"

def age_from_dob(dob, today=None):
    try:
        b = datetime.strptime(dob, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None
    t = today or date.today()
    return t.year - b.year - ((t.month, t.day) < (b.month, b.day))

def light_multiplier(profile):
    """0.4 .. 1.0 scaling of the night (melatonin) signal from the light habits."""
    sun = {"<1": 0.0, "1-3": 0.5, "3+": 1.0}.get(profile.get("sun_hours"), 0.5)
    eve = {"bright": 0.0, "moderate": 0.5, "dark": 1.0}.get(profile.get("evening_light"), 0.5)
    reg = {"irregular": 0.0, "somewhat": 0.5, "consistent": 1.0}.get(profile.get("sleep_regular"), 0.5)
    return round(0.4 + 0.6 * (0.30 * sun + 0.40 * eve + 0.30 * reg), 3)

def _alertness(h):
    """Wake-anchored alertness: peak ~5 h after waking, post-lunch dip ~7 h."""
    return (math.cos(2 * math.pi * (h - 5.0) / 24.0)
            - 0.40 * math.exp(-((h - 7.0) ** 2) / (2 * 1.3 ** 2)))

def circadian_activation(hours_awake, profile, age):
    """Mean of the body-clock drivers, -1 (biological night) .. +1 (daytime high)."""
    br = age_bracket(age)
    hs = hours_awake - _PHASE_SHIFT[br]
    cyc = lambda peak: math.cos(2 * math.pi * (hs - peak) / 24.0)
    drivers = [
        _clamp(_alertness(hs)),
        cyc(1.0),                                              # cortisol, morning peak
        0.9 * cyc(10.0),                                       # body temperature, late afternoon
        -_MEL_AMP[br] * light_multiplier(profile) * cyc(16.0), # melatonin, biological night
    ]
    if profile.get("sex") == "male":
        drivers.append(_T_AMP[br] * cyc(0.5))                  # daily testosterone
    return _clamp(sum(drivers) / len(drivers))


# ══════════════════════════════════════════════════════════════════════════════
# INPUT DEFAULTS
# ══════════════════════════════════════════════════════════════════════════════
def light_from_habits(profile):
    """A typical day's light grid (minutes per period) from the profile's habits."""
    day = {"<1": [10, 15, 10, 0, 0], "1-3": [30, 45, 45, 0, 0],
           "3+": [60, 60, 60, 15, 0]}.get(profile.get("sun_hours"), [30, 45, 45, 0, 0])
    scr = {"bright": [0, 0, 60, 120, 30], "moderate": [0, 0, 60, 90, 15],
           "dark": [0, 0, 60, 30, 0]}.get(profile.get("evening_light"), [0, 0, 60, 90, 15])
    return {"daylight": list(day), "screen": list(scr),
            "warm": [0, 0, 0, 60, 0], "red": [0, 0, 0, 0, 0]}


# ══════════════════════════════════════════════════════════════════════════════
# THE MODEL
# ══════════════════════════════════════════════════════════════════════════════
_MOOD_X = {"Calm": -1.0, "Focused": -0.6, "Energised": 0.3, "Tired": 0.4,
           "Unwell": 0.6, "Scattered": 0.8, "Restless": 1.0}
_WEATHER_X = {"Sunny": -0.3, "Mild": -0.3, "Dry": 0.0, "Cloudy": 0.1, "Snowing": 0.1,
              "Rainy": 0.2, "Cold": 0.2, "Humid": 0.2, "Windy": 0.3, "Hot": 0.3}
_WEATHER_LIGHT = {"Sunny": 1.0, "Hot": 1.0, "Dry": 1.0, "Mild": 0.9, "Windy": 0.8,
                  "Cold": 0.8, "Humid": 0.8, "Cloudy": 0.5, "Snowing": 0.4, "Rainy": 0.3}

def _weather_words(weather):
    return [w.split()[-1] for w in (weather or [])]

def _hours_since(woke, when):
    try:
        hh, mm = (int(p) for p in woke.split(":"))
    except (AttributeError, ValueError):
        return None
    return ((when.hour + when.minute / 60.0) - (hh + mm / 60.0)) % 24.0

def compute(inputs, table, when=None):
    """Everything the weighted cast needs, and everything the journal records.

    inputs: strength, slept (h), woke ("HH:MM"), light {type: [5 periods]},
            mood, weather [..], cycle_day, cycle_length, profile {..}.
    Returns {"odds": {"yarrow": {6..9}, "coin": {6..9}}, "direction": {..},
             "state": s, "factors": {key: x}, "now": {..}}.
    """
    when = when or datetime.now().astimezone()
    prof = inputs.get("profile") or {}
    lat = prof.get("current_lat")
    have_loc = isinstance(lat, (int, float))
    lat = lat if have_loc else 40.0
    south = lat < 0

    # ── direction: the yin-yang cycle ────────────────────────────────────────
    hour = when.hour + when.minute / 60.0
    lam = sun_longitude(when)
    tide_x, moon = tide(when)
    phases = {
        "time_of_day": ((hour - 6.0) / 24.0) % 1.0,                    # dawn young yang
        "season": ((lam + (180.0 if south else 0.0)) / 360.0) % 1.0,   # equinox young yang
        "moon_phase": (moon["elong"] / 360.0 - 0.25) % 1.0,            # first quarter young yang
    }
    wsum = sum(table[k] for k in phases) or 1.0
    direction = {k: sum(table[f] * math.cos(2 * math.pi * (phases[f] - _STAGE[k]))
                        for f in phases) / wsum for k in LINE_TYPES}

    # ── change: the asker's state ────────────────────────────────────────────
    x = {}
    if inputs.get("mood") in _MOOD_X:
        x["mood"] = _MOOD_X[inputs["mood"]]
    slept = inputs.get("slept")
    if isinstance(slept, (int, float)) and slept > 0:
        x["sleep"] = _clamp((7.5 - slept) / 3.0)
    words = _weather_words(inputs.get("weather"))
    wl = [_WEATHER_LIGHT[w] for w in words if w in _WEATHER_LIGHT]
    wscale = sum(wl) / len(wl) if wl else 0.8
    light = inputs.get("light") or light_from_habits(prof)
    g = lambda t, i: float((light.get(t) or [0] * 5)[i] or 0)
    daylen = day_length(when, lat)
    D = (g("daylight", 0) + g("daylight", 1) + g("daylight", 2) + 0.5 * g("daylight", 3)) * wscale \
        + 0.25 * g("screen", 0)
    night_blue = 0.5 * g("screen", 3) + g("screen", 4)
    x["daylight"] = _clamp(0.6 * _clamp((120.0 - D) / 120.0)
                           + 0.25 * _clamp(night_blue / 120.0, 0.0, 1.0)
                           + 0.15 * _clamp((12.0 - daylen) / 4.0))
    red = g("red", 0) + 0.7 * (g("red", 1) + g("red", 2)) + g("red", 3) + g("red", 4)
    x["red_light"] = -_clamp(red / 20.0, 0.0, 1.0)
    wx = [_WEATHER_X[w] for w in words if w in _WEATHER_X]
    if wx:
        x["weather"] = _clamp(sum(wx) / len(wx))
    h = _hours_since(inputs.get("woke"), when)
    age = age_from_dob(prof.get("dob"), when.date())
    if h is not None:
        x["circadian"] = -circadian_activation(h, prof, age)
        x["ultradian"] = -0.85 * math.cos(2 * math.pi * ((h * 60.0) % 90.0) / 90.0)
    x["lunar_gravity"] = 2.0 * tide_x - 1.0
    cd, cl = inputs.get("cycle_day"), inputs.get("cycle_length")
    if prof.get("sex") == "female" and prof.get("cycle_tracking") and cd and cl:
        phase_x = 0.5 if (cd <= 2 or cd > cl - 5) else 0.0
        x["menstrual"] = _clamp(phase_x + 0.25 * x["lunar_gravity"])
    used = {k: v for k, v in x.items() if table.get(k, 0) > 0}
    tw = sum(table[k] for k in used)
    state = _clamp(sum(table[k] * v for k, v in used.items()) / tw) if tw else 0.0

    # ── odds ─────────────────────────────────────────────────────────────────
    lim = table["limit_" + inputs.get("strength", "Moderate").lower()] / 100.0
    floor = table["floor"] / 100.0
    share = table["direction_share"] / 100.0
    odds = {}
    for method, p0 in CLASSICAL.items():
        p = {}
        for k in LINE_TYPES:
            ch = state if k in (6, 9) else -state
            p[k] = p0[k] * (1.0 + lim * _clamp(share * direction[k] + (1 - share) * ch))
        for _ in range(25):                     # hold every type within its limits
            s = sum(p.values())
            p = {k: v / s for k, v in p.items()}
            p = {k: min(max(v, p0[k] * max(1.0 - lim, floor)), p0[k] * (1.0 + lim))
                 for k, v in p.items()}
        s = sum(p.values())
        odds[method] = {k: v / s for k, v in p.items()}

    now = {
        "time": when.strftime("%H:%M"), "part_of_day": part_of_day(hour),
        "season": season_name(when, south), "solar_term": solar_term(when), "south": south,
        "day_length": round(daylen, 2), "location_set": have_loc,
        "moon_elongation": round(moon["elong"], 1), "moon_distance_km": round(moon["dist"]),
        "tide": round(tide_x, 3), "tide_text": tide_text(tide_x, moon),
    }
    return {"odds": odds, "direction": {k: round(v, 4) for k, v in direction.items()},
            "state": round(state, 4), "factors": {k: round(v, 4) for k, v in x.items()},
            "now": now}

def part_of_day(hour):
    names = [(4, "Night"), (7, "Dawn"), (11, "Morning"), (13, "Noon"), (17, "Afternoon"),
             (20, "Dusk"), (23, "Evening")]
    for end, name in names:
        if hour < end:
            return name
    return "Midnight"

def tide_text(t, moon):
    kind = "Spring tide" if abs(_cos(moon["elong"])) > 0.7 else \
           "Neap tide" if abs(_cos(moon["elong"])) < 0.3 else "Mid tide"
    near = " · near perigee" if moon["dist"] < 370000 else \
           " · near apogee" if moon["dist"] > 400000 else ""
    return kind + near

def now_text(now, moon_name):
    dl = now["day_length"]
    hh, mm = int(dl), int(round((dl - int(dl)) * 60))
    if mm == 60:
        hh, mm = hh + 1, 0
    loc = "" if now["location_set"] else " · no location (north assumed)"
    term = now["solar_term"] + (" (northern calendar)" if now.get("south") else "")
    return (f"{now['part_of_day']} · {moon_name} · {now['season']}, {term} · "
            f"{hh} h {mm:02d} daylight · {now['tide_text']}{loc}")


# ══════════════════════════════════════════════════════════════════════════════
# DRAWING A LINE
# ══════════════════════════════════════════════════════════════════════════════
def draw_line(rng, odds):
    r = rng.random(); acc = 0.0
    for k in LINE_TYPES:
        acc += odds[k]
        if r < acc:
            return k
    return 8

def coin_faces(rng, value):
    """Three coin faces (2 yin, 3 yang) that sum to the line value."""
    threes = value - 6
    faces = [3] * threes + [2] * (3 - threes)
    rng.shuffle(faces)
    return faces

def yarrow_plan(rng, value):
    """Division outcomes (2 or 3 each) summing to the line value, chosen with the
    classical chances of each division (first 3/4 for a 3, later 1/2)."""
    patterns = [(a, b, c) for a in (2, 3) for b in (2, 3) for c in (2, 3) if a + b + c == value]
    weights = [(0.75 if p[0] == 3 else 0.25) * 0.5 * 0.5 for p in patterns]
    r = rng.random() * sum(weights); acc = 0.0
    for p, w in zip(patterns, weights):
        acc += w
        if r < acc:
            return list(p)
    return list(patterns[-1])
