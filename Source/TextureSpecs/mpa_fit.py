"""Where modules go on each supported armor: measured silhouettes and the armor's footprint.

Everything here comes from armor_profiles.json (numbers measured from the armors' worn textures
by measure_profiles.py, no pixels) and from rwtexturegen's body and head templates and plate
layouts (rwtex/data). Positions are screen px in the module texture (256 px, k = 2), sizes in
px at 128 scaled by k.
"""
import json
import math
import os

import numpy as np

from rwtex import geom as G

PI = math.pi
HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, 'armor_profiles.json'), encoding='utf-8') as _f:
    PROFILES = json.load(_f)
V = PROFILES['v']
PHI = PROFILES['phi']

BODY_FITS = list(PROFILES['armors'])
HELMET_FITS = list(PROFILES['helmets'])
BODY_TYPES = ['Male', 'Female', 'Thin', 'Hulk', 'Fat']


def _load_layouts():
    import rwtex
    path = os.path.join(os.path.dirname(rwtex.__file__), 'data', 'armor_fit.json')
    with open(path, encoding='utf-8') as f:
        d = json.load(f)
    return d['layout'], d['variants']['recon']['layout']


MARINE_LAYOUT, RECON_LAYOUT = _load_layouts()
# Armors built like recon armor (slim, inside the body, recon plate heights); the rest follow marine armor.
RECON_BUILT = {'Recon', 'Locust', 'PrestigeRecon', 'Trooper', 'RoyalTrooper'}


# ----------------------------------------------------------------------------- body silhouettes

def body_profile(fit, bt):
    return PROFILES['armors'][fit]['bodies'][bt]


def edge(fit, bt, view, side, v0, v1):
    """Offset (px at 128) of the armor's coloured edge beyond the naked body silhouette over
    v0..v1, on the screen-left ('l') or screen-right ('r') side of a view. Rows where the edge
    jumps inward (a dark belt or undersuit counts as outline) are ignored."""
    arr = body_profile(fit, bt)[f'{view}_{side}']
    vals = [o for v, o in zip(V, arr) if o is not None and v0 - 1e-6 <= v <= v1 + 1e-6]
    if not vals:
        return 0.0
    hi = max(vals)
    return float(np.median([o for o in vals if o >= hi - 6.0]))


def screen_side(view, theta):
    """The side of the screen a point at ``theta`` (0 front, +pi/2 the pawn's right) shows on."""
    if view == 'south':
        return 'l' if math.sin(theta) > 0 else 'r'
    if view == 'north':
        return 'r' if math.sin(theta) > 0 else 'l'
    return 'r' if math.cos(theta) > 0 else 'l'


def body_ext(c, v):
    """(centre x, half extent) of the naked body silhouette at height v in this view."""
    f = c.form
    if c.dir == 'east':
        return f.d(v)
    if c.dir == 'north':
        return f._ext(f.N, f.y(v), f.y_sh, f.y_hip)
    return f.a(v)


def armor_x(c, fit, v, side, win=0.04, lo=-4.0, hi=8.0, lift=0.0):
    """Screen x of the armor's coloured edge (plus ``lift`` px at 128) at height v on one side."""
    cx, h = body_ext(c, v)
    off = min(max(edge(fit, c.bt, c.dir, side, v - win, v + win), lo), hi) + lift
    return cx + (-1 if side == 'l' else 1) * (h + off * c.k)


def shoulder_top(c, fit, side=None):
    """Screen y where the armor's shoulder starts (side 'l'/'r' for south/north)."""
    tops = body_profile(fit, c.bt)[f'{c.dir}_shoulder_top']
    y = tops[0] if c.dir == 'east' else tops[0 if side == 'l' else 1]
    f = c.form
    if y is None:
        return f.top + 2.0 * c.k
    return min(max(y * c.k, f.top), f.top + 10.0 * c.k)


def radius(c, px):
    """Radius factor (a function of v) that puts a surface patch ``px`` beyond the body
    silhouette in this view; ``px`` may itself be a function of v."""
    def r(v):
        o = px(v) if callable(px) else px
        return max(0.2, 1.0 + o * c.k / max(body_ext(c, v)[1], 1.0))
    return r


def vy(c, y):
    """Surface height v of screen row y."""
    return (y - c.form.top) / c.form.H


def layout(c, fit):
    """Landmarks of the armor on this body type, as screen rows (px) and scale factors.

    Heights come from the plate layout rwtexturegen measured on vanilla marine and recon armor
    for every body type (chest plate bottom, belt, tassets, back plate), so modules land on the
    same part of the armor whatever the body."""
    L = (RECON_LAYOUT if fit in RECON_BUILT else MARINE_LAYOUT)[c.bt]
    f = c.form
    k = c.k
    y_chest, y_belt = f.y(L['front_bot']), f.y(L['belt_front'])
    sv = (y_belt - f.top) / (45.0 * k)
    sh = f.a(0.5)[1] / (23.5 * k)
    return dict(
        top=f.top, bot=f.bot, H=f.H,
        sv=sv, sh=sh, sq=math.sqrt(max(sh, 0.3)),
        y_elbow=f.y(MARINE_LAYOUT[c.bt]['front_bot']),      # the arms are where they are, whatever the armor
        y_chest=y_chest, y_belt=y_belt,
        y_back=f.y(L['back_bot']), y_belt_back=f.y(L['belt_back']),
        y_tasset=min(f.y(L['tasset_bot']), f.bot),
        px=lambda n: n * sv ** 0.8 * k,
    )


def _close(vals, r=2):
    """1D morphological closing of per-row offsets: fills the inward dips where a dark belt or
    undersuit band was measured as outline (it is still opaque armor)."""
    n = len(vals)
    idx = [i for i in range(n) if vals[i] is not None]
    if not idx:
        return vals
    out = list(vals)
    for i in idx:
        left = [vals[j] for j in range(max(0, i - r), i) if vals[j] is not None]
        right = [vals[j] for j in range(i + 1, min(n, i + r + 1)) if vals[j] is not None]
        if left and right:
            out[i] = max(vals[i], min(max(left), max(right)))
    return out


def body_footprint(c, fit, grow=1.0):
    """The armor's opaque area in this view as a polygon (canvas px), from the per-row
    measurements, grown by ``grow`` px at 128 so seams never fall outside it."""
    k = c.k
    prof = body_profile(fit, c.bt)
    ls, rs = _close(prof[f'{c.dir}_l']), _close(prof[f'{c.dir}_r'])
    top, bot = prof[f'{c.dir}_top_px'], prof[f'{c.dir}_bot_px']
    if top is None:
        return []
    left, right = [], []
    for v, ol, orr in zip(V, ls, rs):
        if ol is None or orr is None:
            continue
        cx, h = body_ext(c, v)
        y = c.form.y(v)
        left.append((cx - h - ol * k, y))
        right.append((cx + h + orr * k, y))
    if len(left) < 2:
        return []
    y_top, y_bot = top * k, bot * k
    # extend to the measured top and bottom rows
    left = [(left[0][0], min(left[0][1], y_top))] + left + [(left[-1][0], max(left[-1][1], y_bot))]
    right = [(right[0][0], min(right[0][1], y_top))] + right + [(right[-1][0], max(right[-1][1], y_bot))]
    left = [(x, min(max(y, y_top), y_bot)) for x, y in left]
    right = [(x, min(max(y, y_top), y_bot)) for x, y in right]
    ring = G.poly(left + right[::-1])
    if grow:
        ring = G.offset(ring, grow * k)
    return [ring]


# ----------------------------------------------------------------------------- helmets

def helm_profile(fit):
    return PROFILES['helmets'][fit]


def helm_rows(fit, view):
    return helm_profile(fit)[f'{view}_rows']


def helm_side(fit, view, side, ph0, ph1, lo=0.8, hi=1.3):
    """Radius factor of the helmet's side (or, east, its back 'l' / front 'r') between two
    latitudes, from the per-row measurement."""
    vals = [r[0 if side == 'l' else 1] for p, r in zip(PHI, helm_rows(fit, view))
            if r is not None and ph0 - 1e-6 <= p <= ph1 + 1e-6]
    if not vals:
        return 1.0
    return min(max(float(np.median(vals)), lo), hi)


def head_edge_x(c, fit, side, ph, r_side):
    hf = c.form
    w = hf.rx * max(math.cos(ph), 0.2) * r_side
    return hf.cx + (-w if side == 'l' else w)


def head_y(c, ph, r=1.0):
    hf = c.form
    return hf.cy - math.sin(ph) * hf.ry * 0.92 * r


def helm_top_y(c, fit):
    """Screen row of the top of the helmet's coloured area."""
    hf = c.form
    top = helm_profile(fit)[c.dir]['top']
    return hf.cy - hf.ry * 0.92 * top


def helm_bottom_y(c, fit):
    hf = c.form
    bottom = helm_profile(fit)[c.dir]['bottom']
    return hf.cy + hf.ry * 0.92 * bottom


def helmet_footprint(c, fit, grow=1.0):
    """The helmet's coloured area in this view as a polygon (canvas px), from the per-row
    measurement at the head latitudes, grown by ``grow`` px at 128."""
    hf = c.form
    k = c.k
    rows = helm_rows(fit, c.dir)
    y_top, y_bot = helm_top_y(c, fit), helm_bottom_y(c, fit)
    left, right = [], []
    for ph, r in sorted(zip(PHI, rows), key=lambda t: -t[0]):      # top to bottom
        if r is None:
            continue
        y = hf.cy - math.sin(ph) * hf.ry * 0.92
        if y < y_top or y > y_bot:
            continue
        w = hf.rx * max(math.cos(ph), 0.2)
        left.append((hf.cx - r[0] * w, y))
        right.append((hf.cx + r[1] * w, y))
    if len(left) < 2:
        return []
    # the crown and the chin are single extreme points, not flat edges
    x_top = (left[0][0] + right[0][0]) / 2
    x_bot = (left[-1][0] + right[-1][0]) / 2
    ring = G.poly([(x_top, y_top)] + left + [(x_bot, y_bot)] + right[::-1])
    if grow:
        ring = G.offset(ring, grow * k)
    return [ring]
