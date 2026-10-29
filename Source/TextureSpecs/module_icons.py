"""rwtexturegen spec: item icons for the armor modifications and the mod's UI icons.

    pip install -e <rwtexturegen>
    python3 module_icons.py [--preview <png>] [--ui]   # writes Textures/ModularPowerArmor/Items (and /UI)

Installs Textures/ModularPowerArmor/Items/<Module>.png (64 px) and the two UI icons in
Textures/ModularPowerArmor/UI.

Every icon is drawn to the same standard as the neuromemetic regenerators and longjump
hydraulics icons (kept as they were drawn, and not rewritten by this script): one piece of
hardware standing upright, filling the same area of the canvas (about 46 x 56 px), lit from
above, with white armor faces, #ccc side faces and lower bands, near-black recesses, light
steel for rods and mechanisms, 2 px outer and 1 px inner outlines - and showing what the
module does: the exoframe a limb frame with its ram, the sensor array three optics, the second
heart a heart behind a porthole. Colour is limited to a few muted accents that name the part
(gel, heart, core, trefoil).
"""
import argparse
import math
import os

import numpy as np

from rwtex import geom as G
from rwtex.render import Bevel, Part, Scene, Split

WHITE = 'armor_white'
DARK = 'undersuit'
STEEL = 'steel_bright'
SHADING = lambda: [Bevel(1.0, 1.1), Split(at=0.8, tone='shade')]  # noqa: E731
FLAT = lambda: [Bevel(0.7, 0.8)]  # noqa: E731

# muted accents (the same tints as the worn art)
GEL = '#74906a'
GEL_LIGHT = '#a5bc98'
HEART = '#8e3530'
HEART_LIGHT = '#b6584e'
CORE = '#5f8796'
CORE_LIGHT = '#99b9c4'
AMBER = '#b58334'
URANIUM = {'name': 'mpa_icon_uranium', 'base': '#5a5e57', 'light': '#7c8178', 'shade': '#43473f', 'deep': '#2c2f29'}


def scene(name, size=64):
    s = Scene(size, name=name, outline=2.0 * size / 64, inner=1.0 * size / 64, light_angle=-90)
    s.meta['kind'] = 'item'
    return s


def part(s, name, ring, z, mat=WHITE, tone='base', shading=None, **kw):
    p = Part(name, ring, mat, z=z, mask=None, tone=tone, shading=SHADING() if shading is None else shading, **kw)
    s.add(p)
    return p


def bolt(p, x, y, r=1.2):
    p.fill(G.circle(x, y, r), 'undersuit.base')


def hexagon(cx, cy, r, rot=30):
    return G.poly([(cx + r * math.cos(math.radians(60 * i + rot)), cy + r * math.sin(math.radians(60 * i + rot))) for i in range(6)])


def _perp(v):
    return np.array([-v[1], v[0]])


def _unit(v):
    v = np.asarray(v, float)
    return v / max(float(np.hypot(v[0], v[1])), 1e-9)


def tube(s, name, a, b, r, z, mat=WHITE, tone='base', side=True):
    """A cylinder seen side-on from a to b, its far side in shade like the canisters."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    n = _perp(_unit(b - a))
    if n[0] < 0:
        n = -n                                  # n points to screen right
    ring = G.poly([a - n * r, b - n * r, b + n * r, a + n * r])
    p = part(s, name, ring, z, mat, tone, shading=FLAT())
    if side:
        p.fill(G.poly([a + n * r * 0.45, b + n * r * 0.45, b + n * r * 1.1, a + n * r * 1.1]), 'shade')
    return p


def hose(s, name, pts, w, z, ribs=3.0):
    """A ribbed rubber hose along a few points."""
    pts = [np.asarray(p, float) for p in pts]
    path = []
    for p0, p1 in zip(pts[:-1], pts[1:]):
        for t in np.linspace(0, 1, 8, endpoint=False):
            path.append(p0 + (p1 - p0) * t)
    path.append(pts[-1])
    path = np.array(path)
    left, right = [], []
    for i in range(len(path)):
        t = path[min(i + 1, len(path) - 1)] - path[max(i - 1, 0)]
        n = _perp(_unit(t))
        left.append(path[i] + n * w / 2)
        right.append(path[i] - n * w / 2)
    p = part(s, name, G.poly(left + right[::-1]), z, DARK, shading=FLAT())
    L = 0.0
    nxt = ribs
    for i in range(1, len(path)):
        L += float(np.hypot(*(path[i] - path[i - 1])))
        if L >= nxt:
            n = _perp(_unit(path[i] - path[i - 1]))
            p.line([path[i] + n * w * 0.55, path[i] - n * w * 0.55], 0.7, 'deep')
            nxt += ribs
    return p


def hub(s, name, x, y, r, z):
    """Joint or motor hub seen end-on: a domed disc, dark ring, steel pin."""
    p = part(s, name, G.circle(x, y, r), z, WHITE, shading=FLAT())
    p.fill(G.circle(x, y, r * 0.66), 'undersuit.base')
    p.fill(G.circle(x, y, r * 0.42), 'steel_bright.base')
    p.fill(G.circle(x - r * 0.12, y - r * 0.14, r * 0.18), 'steel_bright.light')
    return p


def lens(p, x, y, r, tint):
    """An optic in a part: steel ring, dark glass with a faint tinted reflection, a glint."""
    p.fill(G.circle(x, y, r), 'steel_bright.base')
    p.fill(G.circle(x, y, r * 0.78), 'undersuit.deep')
    p.fill(G.circle(x + r * 0.12, y + r * 0.14, r * 0.5), tint)
    p.fill(G.circle(x + r * 0.04, y + r * 0.04, r * 0.48), 'undersuit.deep')
    p.fill(G.circle(x - r * 0.3, y - r * 0.3, r * 0.16), 'steel_bright.light')


# Every item icon is fitted to the same box: the regenerator and longjump icons' footprint.
BOX = (7.0, 3.0, 57.0, 60.0)


def standard(s, box=BOX):
    """Scale (never up) and move a finished icon so its outlined silhouette fits ``box``,
    centred across and standing on its bottom edge. Line widths stay as drawn, so every icon
    keeps the same outline weights."""
    from rwtex.render import Fill, Line
    x0, y0, x1, y1 = G.bbox([r for p in s.parts if p.silhouette for r in p.rings])
    ol = s.outline
    bx0, by0, bx1, by1 = box
    f = min(1.0, (bx1 - bx0 - 2 * ol) / (x1 - x0), (by1 - by0 - 2 * ol) / (y1 - y0))
    cx, cy = (x0 + x1) / 2, y1
    tx, ty = (bx0 + bx1) / 2, by1 - ol

    def tf(r):
        r = np.asarray(r, float)
        return np.stack([(r[:, 0] - cx) * f + tx, (r[:, 1] - cy) * f + ty], axis=1)
    for p in s.parts:
        p.rings = [tf(r) for r in p.rings]
        if p.clip:
            p.clip = [tf(r) for r in p.clip]
        for d in p.details:
            if isinstance(d, Line):
                d.pts = tf(d.pts)
            elif isinstance(d, Fill):
                d.rings = [tf(r) for r in d.rings]
    return s


# ----------------------------------------------------------------------------- module items

def icon_plating():
    s = scene('AdditionalPlating')
    # a second plate behind, offset up and right: the plates come as a set
    back = part(s, 'back', G.chamfer(G.poly([(22, 4), (54, 4), (58, 12), (58, 42), (22, 42)]), 3), 1, tone='shade',
                shading=[Bevel(1.0, 1.1, light_tone='base', shade_tone='deep')])
    bolt(back, 53, 9)
    bolt(back, 53, 37)
    front = G.chamfer(G.poly([(6, 14), (44, 14), (50, 22), (50, 50), (43, 59), (13, 59), (6, 50)]), 3)
    f = part(s, 'front', front, 2)
    f.fill(G.poly([(43, 14), (44, 14), (50, 22), (50, 50), (43, 59), (43, 59)]), 'shade')
    f.fill(G.rect(6, 52, 50, 59), 'shade')
    f.line([(7, 52), (49, 52)], 1.0, 'deep')
    # raised keel down the middle
    keel = part(s, 'keel', G.chamfer(G.poly([(21, 15), (35, 15), (33, 51), (23, 51)]), 1.5), 3, tone='light', shading=FLAT())
    keel.fill(G.rect(32, 15, 35, 51), 'shade')
    for i, y in enumerate((24, 27, 30)):
        keel.fill(G.rect(25, y, 30 if i % 2 == 0 else 28, y + 1.2), 'deep')
    # brackets clamping the top edge
    for x in (13, 41):
        br = part(s, f'clamp{x}', G.chamfer(G.rect(x - 3, 10, x + 3, 19), 1), 4, STEEL, shading=FLAT())
        bolt(br, x, 15.5, 1.1)
    for x, y in ((11, 45), (40, 45)):
        bolt(f, x, y, 1.4)
    return s


def icon_uranium():
    s = scene('UraniumPlating')
    back = part(s, 'back', G.chamfer(G.poly([(22, 4), (54, 4), (58, 12), (58, 42), (22, 42)]), 3), 1, URANIUM, tone='shade',
                shading=[Bevel(1.0, 1.1, light_tone='base', shade_tone='deep')])
    back.line([(23, 6), (56, 6)], 1.4, WHITE + '.shade')
    bolt(back, 53, 37)
    front = G.chamfer(G.poly([(5, 13), (45, 13), (51, 21), (51, 51), (44, 60), (12, 60), (5, 51)]), 3)
    f = part(s, 'front', front, 2, URANIUM)
    # white trim frame round the slab (it takes the armor's colour when worn)
    f.details.append(__import__('rwtex.render', fromlist=['Line']).Line(G.offset(front, -1.6), 2.2, WHITE + '.base', closed=True))
    f.fill(G.rect(5, 53, 51, 60), 'deep')
    f.line([(19, 16), (19, 52)], 1.4, 'deep')
    f.line([(37, 16), (37, 52)], 1.4, 'deep')
    keel = part(s, 'keel', G.chamfer(G.poly([(20, 15), (36, 15), (34, 52), (22, 52)]), 1.5), 3, URANIUM, tone='light', shading=FLAT())
    keel.fill(G.circle(28, 32, 6.0), AMBER)
    for i in range(3):
        a0, a1 = math.radians(-90 + 120 * i - 30), math.radians(-90 + 120 * i + 30)
        keel.fill(G.poly([(28, 32)] + [(28 + 5.0 * math.cos(a), 32 + 5.0 * math.sin(a)) for a in np.linspace(a0, a1, 6)]), 'undersuit.deep')
    keel.fill(G.circle(28, 32, 2.0), AMBER)
    keel.fill(G.circle(28, 32, 1.1), 'undersuit.deep')
    for x, y in ((10, 19), (46, 19), (10, 47), (46, 47)):
        bolt(f, x, y, 1.4)
    return s


def icon_ablative():
    s = scene('AblativeShielding')
    # a backing plate tiled with ceramic hexes; one tile shot away, one cracked
    backing = part(s, 'backing', G.chamfer(G.poly([(10, 4), (54, 4), (58, 14), (58, 50), (52, 60), (12, 60), (6, 50), (6, 14)]), 3), 1,
                   STEEL, tone='shade', shading=[Bevel(0.9, 1.0, light_tone='base', shade_tone='deep')])
    r = 7.6
    tiles = [(17, 14), (32, 14), (47, 14), (24.5, 27), (39.5, 27), (17, 40), (32, 40), (47, 40), (24.5, 53), (39.5, 53)]
    for i, (x, y) in enumerate(tiles):
        if i == 4:
            backing.fill(hexagon(x, y, r - 0.6, 0), 'undersuit.base')
            backing.line([(x - 3, y - 2), (x, y + 1), (x + 2, y - 3)], 0.8, 'deep')
            for dx, dy in ((-4, 3), (3, 4)):
                backing.fill(G.poly([(x + dx, y + dy), (x + dx + 2.0, y + dy + 0.6), (x + dx + 0.8, y + dy + 2.0)]), 'steel_bright.base')
            continue
        t = part(s, f'tile{i}', hexagon(x, y, r - 0.6, 0), 2 + i * 0.01, tone='base' if i % 3 else 'light',
                 shading=[Bevel(0.8, 1.0), Split(at=0.72, tone='shade')])
        t.fill(hexagon(x, y, r * 0.42, 0), 'shade')
        if i == 6:
            t.line([(x - 5, y - 3), (x - 1, y), (x + 1, y + 4), (x + 4, y + 5)], 0.9, 'undersuit.base')
    return s


def icon_servos():
    s = scene('BiogelServos')
    # a servo motor (end-on, its drive hub facing us) driving two biogel muscle sleeves that
    # splay up and out from it, clamped at both ends
    gel = {'name': 'mpa_icon_gel', 'base': GEL, 'light': GEL_LIGHT}
    for i, (a, b) in enumerate((((25, 36), (16, 6)), ((39, 36), (48, 6)))):
        a_, b_ = np.asarray(a, float), np.asarray(b, float)
        u = _unit(b_ - a_)
        n = _perp(u)
        r = 6.2
        sl = tube(s, f'sleeve{i}', a_, b_, r, 1 + i * 0.01, mat=gel, side=False)
        for t in (0.3, 0.5, 0.7):
            q = a_ + (b_ - a_) * t
            sl.line([q + n * r * 0.92, q - n * r * 0.92], 1.0, '#52684a')
        hl = n if n[0] < 0 else -n
        sl.line([a_ + (b_ - a_) * 0.15 + hl * r * 0.45, a_ + (b_ - a_) * 0.85 + hl * r * 0.45], 1.2, GEL_LIGHT)
        for t in (0.04, 0.96):
            q = a_ + (b_ - a_) * t
            part(s, f'clamp{i}{t}', G.poly([q - u * 2.0 - n * (r + 1.4), q + u * 2.0 - n * (r + 1.4), q + u * 2.0 + n * (r + 1.4),
                                            q - u * 2.0 + n * (r + 1.4)]), 1.5 + i * 0.01, STEEL, shading=FLAT())
    drum = part(s, 'drum', G.chamfer(G.rect(15, 28, 49, 60), 7), 3)
    drum.fill(G.rect(15, 54, 49, 60), 'shade')
    drum.fill(G.rect(43, 28, 49, 60), 'shade')
    for i in range(4):
        a = math.radians(45 + 90 * i)
        drum.line([(32 + math.cos(a) * 12, 44 + math.sin(a) * 12), (32 + math.cos(a) * 17, 44 + math.sin(a) * 17)], 1.6, 'undersuit.base')
    hub(s, 'hub', 32, 44, 9.0, 4)
    for i in range(4):
        a = math.radians(i * 90)
        part(s, f'hub_bolt{i}', G.circle(32 + math.cos(a) * 6.4, 44 + math.sin(a) * 6.4, 1.1), 4.1, DARK, shading=[])
    return s


def icon_bionic_sync():
    s = scene('BionicSynchronization')
    # a spinal interface block with three armored plugs, their cables fanning out down to
    # connectors
    for i, (x0, x1) in enumerate(((20, 10), (32, 32), (44, 54))):
        hose(s, f'cable{i}', [(x0, 20), (x0 + (x1 - x0) * 0.3, 34), (x1, 48)], 6.0, 1 + i * 0.01)
        c = part(s, f'connector{i}', G.chamfer(G.rect(x1 - 4.5, 47, x1 + 4.5, 59), 1.5), 2 + i * 0.01, STEEL, shading=FLAT())
        c.fill(G.rect(x1 - 4.5, 55, x1 + 4.5, 59), 'deep')
        c.line([(x1 - 4.5, 51), (x1 + 4.5, 51)], 0.8, 'deep')
    block = part(s, 'block', G.chamfer(G.poly([(10, 6), (54, 6), (58, 13), (54, 24), (10, 24), (6, 13)]), 2), 3)
    block.fill(G.rect(6, 19, 58, 24), 'shade')
    block.fill(G.rect(26, 4, 38, 8), 'shade')
    for x in (20, 32, 44):
        block.fill(G.circle(x, 14, 4.6), 'undersuit.base')
        block.fill(G.circle(x, 14, 3.2), 'steel_bright.base')
        block.fill(G.circle(x - 0.7, 13.2, 1.2), 'steel_bright.light')
    return s


def icon_subpersona():
    s = scene('AuxiliarySubpersona')
    # three subcore cartridges slotted into a processor case, one pulled half out
    for i, (x, top) in enumerate(((16, 15), (32, 4), (48, 12))):
        c = part(s, f'cart{i}', G.chamfer(G.rect(x - 6, top, x + 6, 40), 1.5), 1 + i * 0.01, STEEL, shading=FLAT())
        c.fill(G.rect(x + 2.6, top + 2, x + 6, 40), 'shade')
        c.fill(G.rect(x - 4, top + 6, x + 4, top + 13), 'armor_white.base')
        c.line([(x - 3, top + 8.5), (x + 2, top + 8.5)], 0.8, 'deep')
        c.line([(x - 3, top + 10.5), (x + 0.5, top + 10.5)], 0.8, 'deep')
        tab = part(s, f'tab{i}', G.chamfer(G.rect(x - 3.5, top - 3, x + 3.5, top + 2), 1), 1.5 + i * 0.01, DARK, shading=FLAT())
        tab.fill(G.rect(x - 1.6, top - 1.6, x + 1.6, top + 0.2), 'steel_bright.base')
    case = part(s, 'case', G.chamfer(G.rect(6, 30, 58, 60), 3), 2)
    case.fill(G.rect(6, 30, 58, 35), 'shade')
    for x in range(10, 56, 4):
        case.line([(x, 31), (x, 34)], 0.9, 'deep')
    case.fill(G.rect(51, 35, 58, 60), 'shade')
    case.fill(G.rect(6, 54, 58, 60), 'shade')
    for x in (16, 32, 48):
        case.fill(G.rect(x - 6.5, 35, x + 6.5, 38), 'undersuit.base')
        case.fill(G.rect(x - 2, 44, x + 2, 47), AMBER)
    bolt(case, 10, 50, 1.3)
    bolt(case, 54, 50, 1.3)
    return s


def icon_exoframe():
    s = scene('Exoframe')
    # the exoskeleton itself: a shoulder yoke with its actuators, a segmented spine, the hip
    # frame and two legs with knee joints and feet
    for i, side in enumerate((-1, 1)):
        xh = 32 + side * 13
        for j, (a, b, w) in enumerate((((xh, 42), (xh + side * 2, 51), 2.6), ((xh + side * 2, 51), (xh + side * 1, 59), 2.4))):
            a_, b_ = np.asarray(a, float), np.asarray(b, float)
            n = _perp(_unit(b_ - a_))
            part(s, f'leg{i}{j}', G.poly([a_ - n * w, b_ - n * w, b_ + n * w, a_ + n * w]), 1 + j * 0.01, STEEL, shading=FLAT())
        part(s, f'knee{i}', G.rounded(G.rect(xh + side * 2 - 4.2, 48.5, xh + side * 2 + 4.2, 53.5), 2), 1.6, STEEL, tone='shade',
             shading=FLAT())
        foot = part(s, f'foot{i}', G.chamfer(G.rect(xh + side * 1 - 5, 57, xh + side * 1 + 5, 61), 1), 1.7, WHITE, shading=FLAT())
        foot.fill(G.rect(xh + side * 1 - 5, 59.5, xh + side * 1 + 5, 61), 'shade')
    for k in range(5):
        y = 13 + k * 5.4
        v = part(s, f'vert{k}', G.chamfer(G.rect(27, y, 37, y + 4.2), 1.2), 2 + k * 0.01, STEEL, shading=FLAT())
        v.fill(G.rect(27, y + 3, 37, y + 4.2), 'shade')
    yoke = part(s, 'yoke', G.rounded(G.rect(10, 7, 54, 12.5), 2), 3, STEEL, shading=FLAT())
    yoke.fill(G.rect(10, 10.5, 54, 12.5), 'shade')
    hip = part(s, 'hipframe', G.rounded(G.rect(14, 38, 50, 43.5), 2), 3, STEEL, shading=FLAT())
    hip.fill(G.rect(14, 41.5, 50, 43.5), 'shade')
    for x in (20, 26, 38, 44):
        bolt(hip, x, 40.5, 0.9)
    for i, (cx, cy, w, h) in enumerate(((9, 9.5, 8, 9), (55, 9.5, 8, 9), (13, 40.5, 7, 8), (51, 40.5, 7, 8))):
        a = part(s, f'act{i}', G.chamfer(G.rect(cx - w, cy - h, cx + w, cy + h), 2.5), 4)
        a.fill(G.rect(cx - w, cy + h * 0.45, cx + w, cy + h), 'shade')
        # the joint's axle runs left-right: a barrel through the housing
        a.fill(G.rect(cx - w, cy - 1.8, cx + w, cy + 1.8), 'undersuit.base')
        a.fill(G.rect(cx - w, cy - 1.0, cx + w, cy - 0.2), 'steel_bright.base')
    return s


def icon_rigidity():
    s = scene('RigidityMatrix')
    # two lattice guard plates hanging from a lock bar, splayed a little, a lock housing between
    for i, (cx, ang) in enumerate(((19, 5), (45, -5))):
        ring = G.rotate(G.chamfer(G.poly([(cx - 10, 14), (cx + 10, 14), (cx + 8, 60), (cx - 8, 60)]), 2.5), ang, cx, 14)
        p = part(s, f'plate{i}', ring, 1 + i * 0.01)
        p.fill(G.rotate(G.rect(cx - 9, 54, cx + 9, 60), ang, cx, 14), 'shade')
        win = G.rotate(G.chamfer(G.rect(cx - 6, 21, cx + 6, 51), 1.2), ang, cx, 14)
        p.fill(win, 'undersuit.base')
        for j in range(-1, 4):
            y = 21 + j * 10
            for xa, xb in ((cx - 6, cx + 6), (cx + 6, cx - 6)):
                a_ = G.rotate(G.P((xa, max(21, y))), ang, cx, 14)[0]
                b_ = G.rotate(G.P((xb, min(51, y + 12))), ang, cx, 14)[0]
                p.line([a_, b_], 1.5, 'steel_bright.base')
        p.details.append(__import__('rwtex.render', fromlist=['Line']).Line(win, 1.0, 'steel_bright.light', closed=True))
    bar = part(s, 'bar', G.rounded(G.rect(5, 10, 59, 17), 3), 2, STEEL, shading=FLAT())
    bar.fill(G.rect(5, 14.5, 59, 17), 'shade')
    for x in (9, 55):
        bolt(bar, x, 13.5, 1.5)
    lock = part(s, 'lock', G.chamfer(G.rect(25, 4, 39, 24), 2), 3)
    lock.fill(G.rect(34, 4, 39, 24), 'shade')
    for i in range(3):
        y = 15 + i * 2.6
        lock.line([(28, y), (32, y + 1.6), (36, y)], 1.0, 'undersuit.base')
    bolt(lock, 32, 9, 1.5)
    return s


def icon_second_heart():
    s = scene('SecondHeart')
    # an armored life-support drum: the heart behind a porthole, arterial hoses arching out of
    # the top, subcore cartridges in the rim
    hose(s, 'artery_l', [(22, 18), (14, 6), (6, 14), (8, 34)], 5.5, 1)
    hose(s, 'artery_r', [(42, 18), (50, 6), (58, 14), (56, 34)], 5.5, 1.01)
    drum = part(s, 'drum', G.chamfer(G.rect(11, 14, 53, 60), 7), 2)
    drum.fill(G.rect(11, 14, 53, 21), 'shade')
    drum.fill(G.rect(46, 21, 53, 60), 'shade')
    drum.fill(G.rect(11, 55, 53, 60), 'shade')
    for x in (22, 32, 42):
        drum.fill(G.rect(x - 3, 15, x + 3, 20), 'undersuit.base')
        drum.fill(G.rect(x - 2, 16, x + 2, 18), 'steel_bright.base')
    drum.fill(G.circle(31, 38, 13), 'steel_bright.base')
    drum.fill(G.circle(31, 38, 10.6), 'undersuit.deep')
    pts = []
    for t in np.linspace(0, 2 * math.pi, 40):
        hx = 16 * math.sin(t) ** 3
        hy = -(13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t))
        pts.append((31 + hx / 17 * 7.0, 39 + hy / 17 * 7.0))
    drum.fill(G.poly(pts), HEART)
    drum.fill(G.ellipse(28, 36, 2.4, 2.0), HEART_LIGHT)
    for i in range(6):
        a = math.radians(i * 60 + 30)
        drum.fill(G.circle(31 + math.cos(a) * 11.8, 38 + math.sin(a) * 11.8, 0.9), 'undersuit.base')
    return s


def icon_second_mind():
    s = scene('SecondMind')
    # a persona core in an armored housing: the core behind a hex port, cooling fins either
    # side, a data cable out of the bottom
    hose(s, 'data', [(40, 52), (46, 58), (56, 58)], 5.0, 0.5)
    for side in (-1, 1):
        for i, y in enumerate((14, 21, 28, 35, 42)):
            x0, x1 = (4, 14) if side < 0 else (50, 60)
            part(s, f'fin{side}{i}', G.rounded(G.rect(x0, y, x1, y + 4), 1.2), 1 + i * 0.01, STEEL, tone='shade',
                 shading=[Bevel(0.6, 0.7, shade_tone='deep')])
    body = part(s, 'body', G.chamfer(G.rect(11, 4, 53, 58), 8), 2)
    body.fill(G.rect(46, 4, 53, 58), 'shade')
    body.fill(G.rect(11, 52, 53, 58), 'shade')
    for x in range(20, 46, 5):
        body.fill(G.rect(x, 8, x + 2.4, 13), 'undersuit.base')
    body.fill(hexagon(31, 32, 15), 'steel_bright.base')
    body.fill(hexagon(31, 32, 12.4), 'undersuit.deep')
    body.fill(G.circle(31, 32, 8.4), '#41616c')
    body.fill(G.circle(31, 32, 5.8), CORE)
    body.fill(G.circle(31, 32, 2.8), CORE_LIGHT)
    body.fill(G.circle(28.5, 29.5, 1.3), '#dfeaee')
    return s


def icon_sensor_array():
    s = scene('SensorArray')
    # a sensor pod: three optics stacked behind a hood - thermal, visible and ultraviolet - a
    # mounting bracket and its loom
    hose(s, 'loom', [(50, 40), (56, 48), (54, 58)], 5.0, 0.5)
    br = part(s, 'bracket', G.chamfer(G.rect(40, 16, 56, 44), 2), 1, STEEL, shading=FLAT())
    br.fill(G.rect(51, 16, 56, 44), 'shade')
    for y in (21, 39):
        bolt(br, 50, y, 1.4)
    pod = part(s, 'pod', G.chamfer(G.poly([(12, 4), (40, 4), (46, 12), (46, 60), (12, 60)]), 3), 2)
    pod.fill(G.rect(40, 12, 46, 60), 'shade')
    pod.fill(G.rect(12, 4, 46, 11), 'light')
    pod.line([(13, 11), (45, 11)], 1.0, 'deep')
    pod.fill(G.chamfer(G.rect(15, 13, 38, 57), 2), 'undersuit.base')
    lens(pod, 26.5, 21, 5.6, '#6e5a32')
    lens(pod, 26.5, 35.5, 7.4, '#3f5d64')
    lens(pod, 26.5, 50, 5.6, '#4e4a64')
    return s


def icon_stress_dampener():
    s = scene('StressDampener')
    # an emitter dome on a base plate with three stub antennas round it
    for i, (x0, x1, top) in enumerate(((17, 13, 8), (32, 32, 3), (47, 51, 8))):
        part(s, f'stub{i}', G.poly([(x0 - 1.3, 30), (x0 + 1.3, 30), (x1 + 1.1, top + 2), (x1 - 1.1, top + 2)]), 1 + i * 0.01, STEEL,
             shading=FLAT())
        part(s, f'tip{i}', G.circle(x1, top + 1, 2.6), 1.5 + i * 0.01, DARK, shading=FLAT())
    base = part(s, 'base', G.chamfer(G.poly([(8, 46), (56, 46), (60, 54), (56, 60), (8, 60), (4, 54)]), 2), 2, STEEL, shading=FLAT())
    base.fill(G.rect(4, 55, 60, 60), 'shade')
    for x in (11, 53):
        bolt(base, x, 51, 1.4)
    dome = part(s, 'dome', G.poly([(10, 48)] + [(32 + 22 * math.cos(a), 48 - 24 * math.sin(a)) for a in np.linspace(0, math.pi, 24)][::-1]
                               + [(54, 48)]), 3)
    dome.fill(G.rect(10, 44, 54, 48), 'shade')
    dome.fill(G.ellipse(32, 35, 8.0, 7.0), 'steel_bright.base')
    dome.fill(G.ellipse(32, 35, 6.0, 5.2), 'undersuit.deep')
    dome.fill(G.ellipse(32, 36, 3.2, 2.6), '#4e4a64')
    dome.fill(G.ellipse(29.5, 33, 1.4, 1.1), 'steel_bright.light')
    return s


def icon_uplink():
    s = scene('TargetingUplink')
    # a laser rangefinder: a housing with a big lens, a sight slot, a whip antenna on a sprung
    # base, a mounting bracket
    part(s, 'whip', G.poly([(42.3, 26), (43.7, 26), (44.6, 5), (43.4, 5)]), 1, STEEL, shading=FLAT())
    part(s, 'whip_tip', G.circle(44, 4.6, 2.2), 1.2, DARK, shading=FLAT())
    base = part(s, 'whip_base', G.chamfer(G.rect(38, 20, 49, 29), 1.5), 1.5, DARK, shading=FLAT())
    for y in (22.5, 25.5):
        base.line([(39, y), (48, y)], 0.8, 'light')
    mount = part(s, 'mount', G.chamfer(G.rect(14, 52, 50, 60), 1.5), 1.8, STEEL, shading=FLAT())
    for x in (18, 46):
        bolt(mount, x, 56, 1.4)
    h = part(s, 'housing', G.chamfer(G.poly([(6, 28), (52, 28), (58, 34), (58, 54), (6, 54)]), 3), 2)
    h.fill(G.rect(51, 34, 58, 54), 'shade')
    h.fill(G.rect(6, 49, 58, 54), 'shade')
    h.fill(G.rect(34, 33, 47, 37), 'undersuit.base')
    for x in (37, 41, 45):
        h.line([(x, 41), (x, 46)], 1.2, 'undersuit.base')
    lens(h, 19, 40, 9.0, '#6b3430')
    return s


def icon_thermal():
    s = scene('ThermalRegulator')
    # a heat exchanger: a finned radiator block with a fan, coolant lines with couplings
    for i, x in enumerate((16, 48)):
        hose(s, f'line{i}', [(x, 16), (x + (6 if x < 32 else -6), 6), (32, 5)], 5.0, 0.5 + i * 0.01)
        part(s, f'coupling{i}', G.chamfer(G.rect(x - 4, 11, x + 4, 17), 1), 1.5 + i * 0.01, STEEL, shading=FLAT())
    part(s, 'manifold', G.chamfer(G.rect(27, 2, 37, 9), 1.5), 0.8, STEEL, shading=FLAT())
    r = part(s, 'radiator', G.chamfer(G.rect(6, 15, 58, 60), 3), 2)
    r.fill(G.rect(51, 15, 58, 60), 'shade')
    r.fill(G.rect(6, 55, 58, 60), 'shade')
    for i in range(5):
        x = 10 + i * 4.0
        r.fill(G.rounded(G.rect(x, 20, x + 2.2, 51), 1.0), 'undersuit.base')
    r.fill(G.circle(40, 36, 12), 'steel_bright.base')
    r.fill(G.circle(40, 36, 10.2), 'undersuit.deep')
    for j in range(5):
        a = math.radians(j * 72 + 15)
        r.fill(G.poly([(40, 36), (40 + 9.4 * math.cos(a), 36 + 9.4 * math.sin(a)), (40 + 8.6 * math.cos(a + 0.75), 36 + 8.6 * math.sin(a + 0.75))]),
               'steel_bright.shade')
    r.fill(G.circle(40, 36, 3.2), 'steel_bright.light')
    return s


def icon_regenerators():
    s = scene('NeuromemeticRegenerators')
    # a mounting plate with two canisters on it, splayed a little
    plate_ = part(s, 'plate', G.chamfer(G.poly([(14, 46), (50, 46), (54, 58), (10, 58)]), 2.5), 1, tone='shade',
                  shading=[Bevel(0.9, 1.0, light_tone='base', shade_tone='deep')])
    bolt(plate_, 16, 53)
    bolt(plate_, 48, 53)
    for i, (cx, ang) in enumerate(((21.5, -7), (42.5, 7))):
        body = G.rotate(G.rounded(G.rect(cx - 8, 8, cx + 8, 50), 4.5), ang, cx, 48)
        c = part(s, f'canister{i}', body, 2 + i * 0.01)
        detail = [
            (G.rect(cx - 8, 8, cx + 8, 13), 'shade'),
            (G.rect(cx - 8, 43, cx + 8, 50), 'undersuit.base'),
            (G.rounded(G.rect(cx - 3.2, 19, cx + 3.2, 37), 1.2), 'undersuit.base'),
            (G.rect(cx - 2.0, 21, cx + 0.2, 26), 'undersuit.light'),
            (G.rect(cx + 4.5, 13, cx + 8, 43), 'shade'),
        ]
        for ring, tone in detail:
            c.fill(G.rotate(ring, ang, cx, 48), tone)
        cap = part(s, f'cap{i}', G.rotate(G.ellipse(cx, 8.5, 6.5, 3.2), ang, cx, 48), 3 + i * 0.01, tone='light',
                   shading=[Bevel(0.6, 0.7)])
        cap.fill(G.rotate(G.ellipse(cx, 8.5, 2.4, 1.2), ang, cx, 48), 'undersuit.base')
    return s


def icon_longjump():
    s = scene('LongjumpHydraulics')
    # two hydraulic pistons side by side, each a cylinder over a polished rod with pivot eyes
    for i, (x, ang) in enumerate(((22, -10), (42, 10))):
        rod = part(s, f'rod{i}', G.rotate(G.rect(x - 2.6, 30, x + 2.6, 54), ang, x, 32), 1 + i * 0.01, mat='steel_bright',
                   shading=[Bevel(0.6, 0.6)])
        rod.line([G.rotate(G.P((x - 0.8, 32)), ang, x, 32)[0], G.rotate(G.P((x - 0.8, 52)), ang, x, 32)[0]], 0.8, 'light')
        eye = part(s, f'eye_low{i}', G.rotate(G.circle(x, 55, 4.4), ang, x, 32), 1.2 + i * 0.01, tone='shade',
                   shading=[Bevel(0.6, 0.6)])
        eye.fill(G.rotate(G.circle(x, 55, 1.8), ang, x, 32), 'undersuit.base')
        cyl = part(s, f'cylinder{i}', G.rotate(G.rounded(G.rect(x - 7, 11, x + 7, 36), 3), ang, x, 32), 2 + i * 0.01)
        for ring, tone in ((G.rect(x + 3.5, 12, x + 7, 33), 'shade'), (G.rect(x - 7, 31, x + 7, 36), 'undersuit.base'),
                           (G.rect(x - 7, 15, x + 7, 17), 'shade')):
            cyl.fill(G.rotate(ring, ang, x, 32), tone)
        eye_t = part(s, f'eye_top{i}', G.rotate(G.circle(x, 9, 4.6), ang, x, 32), 2.5 + i * 0.01, tone='shade',
                     shading=[Bevel(0.6, 0.6)])
        eye_t.fill(G.rotate(G.circle(x, 9, 2.0), ang, x, 32), 'undersuit.base')
    return s


ICONS = [icon_plating, icon_ablative, icon_servos, icon_bionic_sync, icon_subpersona, icon_exoframe, icon_sensor_array,
         icon_stress_dampener, icon_uplink, icon_thermal, icon_regenerators, icon_uranium, icon_rigidity, icon_second_heart,
         icon_second_mind, icon_longjump]
# Kept exactly as they were drawn: never written by this script.
KEEP = {'NeuromemeticRegenerators', 'LongjumpHydraulics'}


# ----------------------------------------------------------------------------- UI icons

def ui_modify_armor():
    """Gizmo: a chest plate with a wrench across it."""
    s = scene('ModifyArmor')
    shell = part(s, 'shell', G.chamfer(G.poly([(8, 10), (24, 6), (40, 6), (56, 10), (54, 34), (44, 56), (20, 56), (10, 34)]), 4), 1)
    shell.fill(G.ellipse(32, 11, 9, 5), 'undersuit.base')
    shell.line([(14, 32), (50, 32)], 1.0, 'shade')
    w = [(13, 55), (37, 31), (35, 25), (41, 17), (49, 16), (45, 21), (47, 26), (52, 25), (53, 18), (57, 23), (55, 31), (47, 35), (41, 34),
         (18, 59)]
    part(s, 'wrench', G.poly(w), 2, mat='steel_bright', shading=[Bevel(0.9, 1.0)])
    return s


def ui_category():
    """Thing category: a small module with a dark slot."""
    s = scene('ModuleCategory', size=32)
    body = part(s, 'body', G.chamfer(G.rect(4, 7, 28, 26), 3), 1, shading=[Bevel(0.6, 0.6), Split(at=0.8, tone='shade')])
    body.fill(G.rect(9, 12, 23, 17), 'undersuit.base')
    return s


def build_ui(spec):
    return [ui_modify_armor(), ui_category()]



SPEC = {
    'name': 'MPA_ModuleIcons',
    'output': {'dir': 'output/MPA_ModuleIcons', 'tex_root': 'ModularPowerArmor/Items', 'mask': False, 'svg': False},
    'items': [{'name': 'MPA_UIIcons', '_build': build_ui, 'output': {'tex_root': 'ModularPowerArmor/UI'}}],
}


def build(spec):
    return [standard(s) for s in (fn() for fn in ICONS) if s.name not in KEEP]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--preview', default='', help='write a contact sheet of all item icons here instead of installing')
    ap.add_argument('--ui', action='store_true', help='also write the UI icons')
    a = ap.parse_args()
    root = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'Textures', 'ModularPowerArmor'))
    if a.preview:
        from PIL import Image
        imgs = [(fn().name, fn) for fn in ICONS]
        sheet = Image.new('RGBA', (8 * 72, 2 * 72), (80, 76, 64, 255))
        for i, (name, fn) in enumerate(imgs):
            img = Image.open(os.path.join(root, 'Items', name + '.png')) if name in KEEP else standard(fn()).render()
            sheet.alpha_composite(img.convert('RGBA'), ((i % 8) * 72 + 4, (i // 8) * 72 + 4))
        sheet.save(a.preview)
        return
    for sc in build(None):
        sc.render().save(os.path.join(root, 'Items', sc.name + '.png'))
    if a.ui:
        for sc in build_ui(None):
            sc.render().save(os.path.join(root, 'UI', sc.name + '.png'))


if __name__ == '__main__':
    main()
