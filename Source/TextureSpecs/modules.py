"""Worn art for the armor modifications: 256 px with CutoutComplex masks, fitted to every armor.

    pip install -e <rwtexturegen>
    python3 build_art.py [--modules A,B] [--fits X,Y]

Every modification that shows on the pawn gets one texture set per armor fit, each texture with
its mask (red = dyed with the armor's colour):

    body    Textures/ModularPowerArmor/Worn/Body/<Module>_<Fit>/<Module>_<Fit>_<BodyType>_<dir>[m].png
    helmet  Textures/ModularPowerArmor/Worn/Head/<Module>_<Fit>/<Module>_<Fit>_<dir>[m].png

The render nodes ask for ModularPowerArmor/Worn/Body/<Module>_{fit}/<Module>_{fit}, where the
mod fills in the fit of the armor piece the module is installed in (see MPA_ArmorTargets.xml).

Look and construction: mpa_kit.py. Placement from the measured armors: mpa_fit.py. Modules may
overlap one another; their render nodes' layerFraction (Module.layer, mirrored in the defs)
draws them in a fixed order, low to high:

    body    exoframe, rigidity matrix, longjump hydraulics, biogel servos, thermal regulator,
            plating / uranium plating, regenerators, second heart, subpersona
    helmet  plating / uranium plating, neural link, stress dampener, subpersona, second mind,
            regenerators, sensor array, targeting uplink

Apart from the plating, every module is built like the vanilla armor itself (see vanilla-style
parts below): a few big plates with flat faces, chamfers, dark recesses and black outlines.
Joints are drawn the way their axis faces each view: the exoframe's hip and knee pivots, the
elbow servos and the longjump rams' heel pivots turn about the pawn's left-right axis, so they
are round caps only from the side, and housings or barrels from the front and back.
"""
import math

import numpy as np

import mpa_fit as F
from mpa_kit import AMBER, CYAN, DARK, FRAME, GEL, GLASS, RED, SHELL, VIOLET, Kit, _mat, perp, render, render_mask, setup, unit
from rwtex import geom as G
from rwtex.archetypes.apparel import armor, helmet
from rwtex.form import TILT
from rwtex.render import Line

PI = math.pi
SIZE = 256

# Uranium-ceramic composite: dark, untinted; the plates' trim frames are dyed.
URAN = _mat('mpa_uranium', '#5a5e57', light='#7c8178', shade='#43473f', deep='#2c2f29', line='#181a16')


# ============================================================================= registry and options

class Module:
    def __init__(self, name, slot, fn, dirs, layer):
        self.name, self.slot, self.fn, self.dirs, self.layer = name, slot, fn, dirs, layer


REGISTRY = {}


def register(name, slot, dirs=('south', 'east', 'north'), layer=0.5):
    def deco(fn):
        REGISTRY[(slot, name)] = Module(name, slot, fn, tuple(dirs), layer)
        return fn
    return deco


def module(slot, name):
    return REGISTRY[(slot, name)]


def modules(slot):
    return [m for (s, _), m in REGISTRY.items() if s == slot]


# Per-armor adjustments, {fit: {module: {option: value}}}; 'skip' lists the views a module is left
# out of on an armor (where it would sit on one of the armor's own features). Shoulder plates
# only go on plain shoulders, so wings, gold trim, pauldrons and the grenadier's launcher stay
# visible; armors with something on the upper back show the regenerator tanks from behind only.
FITS = {
    # bulky armors: the frame and the elbow servos follow the armor's real edge (edge_hi, px at
    # 128 past the body)
    'Cataphract': {'edge_hi': 14.0, 'Regenerators': {'skip': ('east',)}},
    'PrestigeMarine': {'edge_hi': 12.0, 'Plating': {'caps': ()}, 'UraniumPlating': {'caps': ()},
                       'Exoframe': {'under': {1: 0.4, -1: 0.4}}},
    'Locust': {'edge_hi': 10.0, 'Plating': {'caps': ()}, 'UraniumPlating': {'caps': ()}, 'Regenerators': {'skip': ('east',)}},
    # wings, launchers, pauldrons and trim over the shoulders: the exoframe's shoulder goes under
    # them and its arm strut comes out below them ('under': {pawn side: surface height})
    'Grenadier': {'Plating': {'caps': (1,)}, 'UraniumPlating': {'caps': (1,)}, 'Regenerators': {'skip': ('east',)},
                  'Exoframe': {'under': {-1: 0.42}}},
    'Phoenix': {'Plating': {'caps': ()}, 'UraniumPlating': {'caps': ()}, 'Regenerators': {'skip': ('east',)},
                'Exoframe': {'under': {1: 0.52, -1: 0.52}}},
    'PrestigeRecon': {'Plating': {'caps': ()}, 'UraniumPlating': {'caps': ()}},
    'PrestigeCataphract': {'edge_hi': 14.0, 'Plating': {'caps': ()}, 'UraniumPlating': {'caps': ()}, 'Regenerators': {'skip': ('east',)},
                           'Exoframe': {'under': {1: 0.52, -1: 0.52}}},
    'Siegebreaker': {'edge_hi': 8.0, 'Plating': {'caps': ()}, 'UraniumPlating': {'caps': ()}, 'Regenerators': {'skip': ('east',)},
                     'Exoframe': {'under': {1: 0.46, -1: 0.46}}},
    'RoyalSiegebreaker': {'edge_hi': 12.0, 'Plating': {'caps': ()}, 'UraniumPlating': {'caps': ()}, 'Regenerators': {'skip': ('east',)},
                          'Exoframe': {'under': {1: 0.44, -1: 0.44}}},
    # the chest carries the eagle: plating keeps to the shoulders
    'RoyalTrooper': {'Plating': {'chest': False}, 'UraniumPlating': {'chest': False}},
    'Privateer': {'Plating': {'caps': (-1,)}, 'UraniumPlating': {'caps': (-1,)}, 'Exoframe': {'under': {1: 0.38}}},
}

# The great-helm faceplate fitted to the siegebreaker helmets, smaller and flatter-faced than the
# cataphract's: the joint closer to the face, narrower plates, a shorter chin (see HELM). Like the
# helmet's own face it carries forward-facing cameras, a cluster of three on the left side of the
# face ('cams', one of CAMS).
SIEGE_HELM = dict(style='helm', ridge=1.0, reach=0.85, slope=1.0, v=(0.95, -0.92), back=(0.2, -0.88), cams='block')

# Per-helmet adjustments, {fit: {module: {option: value}}}. The targeting uplink and the sensor
# array share one side of the helmet ('side', the pawn's right by default), the second mind and
# the subpersona the other.
HELMS = {
    # the helmet's own antenna (recon, royal trooper), fins or side plates do the whip's job;
    # tall crests push the crown dampener onto the back of the dome
    'Recon': {'TargetingUplink': {'mast': False}},
    'PrestigeMarine': {'TargetingUplink': {'mast': False}, 'StressDampener': {'at': 'back'}},
    'PrestigeRecon': {'TargetingUplink': {'mast': False}},
    # cataphract and siegebreaker helmets take a great-helm faceplate over the whole front, in
    # composite or in uranium (its 'variant' picks one of HELM_VARIANTS)
    'Cataphract': {'Plating': {'style': 'helm'}, 'UraniumPlating': {'style': 'helm'}},
    'PrestigeCataphract': {'StressDampener': {'at': 'back'}, 'Plating': {'style': 'helm'}, 'UraniumPlating': {'style': 'helm'}},
    'Siegebreaker': {'TargetingUplink': {'mast': False}, 'Plating': SIEGE_HELM, 'UraniumPlating': SIEGE_HELM},
    'RoyalSiegebreaker': {'TargetingUplink': {'mast': False}, 'Plating': SIEGE_HELM, 'UraniumPlating': SIEGE_HELM},
    'RoyalTrooper': {'TargetingUplink': {'mast': False}, 'StressDampener': {'at': 'back'}},
}


def opts(fit, name, **defaults):
    defaults.update(FITS.get(fit, {}).get(name, {}))
    return defaults


def edge_hi(fit):
    """How far past the body (px at 128) lateral modules follow this armor's edge."""
    return FITS.get(fit, {}).get('edge_hi', 6.0)


def hopts(fit, name, **defaults):
    defaults.update(HELMS.get(fit, {}).get(name, {}))
    return defaults


def column_side(fit, name):
    """Pawn side (+1 right, -1 left) of a side-mounted helmet module."""
    s = HELMS.get(fit, {}).get('side', 1)
    return s if name in ('TargetingUplink', 'SensorArray') else -s


# ============================================================================= scene building

def body_scene(name, fit, bt, d):
    """(scene, footprint) of a body module on one armor fit, body type and view."""
    mod = module('body', name)
    out = {}

    def design(c):
        setup(c.scene, c.k)
        out['fp'] = F.body_footprint(c, fit)
        if d in opts(fit, name, skip=()).get('skip', ()):
            return
        mod.fn(Kit(c, out['fp']), c, fit)
    s = armor('spacer', size=SIZE, name=f'{name}_{fit}', ground=False, mask_roles=(), design_fn=design, body_types=[bt],
              dirs=(d,))
    return s.scenes[f'{bt}_{d}'], out['fp']


def head_scene(name, fit, d):
    mod = module('head', name)
    out = {}

    def design(c):
        setup(c.scene, c.k)
        out['fp'] = F.helmet_footprint(c, fit)
        if d in hopts(fit, name, skip=()).get('skip', ()):
            return
        mod.fn(Kit(c, out['fp']), c, fit)
    s = helmet('spacer', size=SIZE, name=f'{name}_{fit}', ground=False, mask_roles=(), design_fn=design, dirs=(d,))
    return s.scenes[d], out['fp']


def render_module(slot, name, fit, d, bt='Male'):
    """(rgba, mask) images, or (None, None) when the module shows nothing in this view."""
    if d not in module(slot, name).dirs:
        return None, None
    sc, fp = body_scene(name, fit, bt, d) if slot == 'body' else head_scene(name, fit, d)
    if not sc.parts:
        return None, None
    return render(sc, fp), render_mask(sc)


# ============================================================================= body helpers

def X(c, fit, y, side, lift=0.0, lo=-1.5, hi=6.0, win=0.03):
    """Screen x of the armor's edge at screen row y on one side, ``lift`` px at 128 outside."""
    return F.armor_x(c, fit, F.vy(c, y), side, win=win, lo=lo, hi=hi, lift=lift)


def surf(K, c, name, poly_tv, r, z, mat=SHELL, bevel=1.1, tol=0.35, **kw):
    """A plate on the torso form: (theta, v) polygon projected with the 3/4 perspective."""
    ring = c.form.ring(c.dir, poly_tv, r)
    if len(ring) < 3:
        return None
    ring = G.simplify_ring(ring, tol * c.k)
    return K.block(name, ring, z, mat, bevel=bevel, **kw)


def sP(c, theta, v, r=1.0):
    return c.form.P(c.dir, theta, v, r(v) if callable(r) else r)


def front_sides(c):
    """(screen side, pawn side) pairs for south and north."""
    return [(F.screen_side(c.dir, s * PI / 2), s) for s in (1, -1)]


def chest_rows(c, fit):
    """Top and bottom row of the visible chest (south): below the helmet's chin, above the belt."""
    lay = F.layout(c, fit)
    y0 = c.form.top + 0.21 * c.form.H
    y1 = lay['y_chest'] - 2.0 * c.k
    return y0, y1, lay


def back_rows(c, fit):
    """Rows of the upper back (north) clear of the helmet."""
    f = c.form
    lay = F.layout(c, fit)
    return f.top + 0.2 * f.H, lay['y_back'], lay


# ============================================================================= shared parts

def bracket_over(K, c, name, x, y_top, h, z, w=2.2):
    """A gunmetal hook bracket clamping a plate's top edge to the armor."""
    k = c.k
    p = K.block(name, G.chamfer(G.rect(x - w * k, y_top - h * k * 0.45, x + w * k, y_top + h * k * 0.55), 0.7 * k), z, FRAME, bevel=0.6)
    if p is not None:
        K.bolt(p, x, y_top + h * k * 0.2, 0.85 * k)
    return p


def trefoil(K, p, x, y, R):
    """Small radiation trefoil stencil."""
    for i in range(3):
        a0 = math.radians(-90 + 120 * i - 30)
        a1 = math.radians(-90 + 120 * i + 30)
        pts = [(x, y)] + [(x + R * math.cos(a), y + R * math.sin(a)) for a in np.linspace(a0, a1, 6)]
        p.fill(G.poly(pts), f'{DARK.name}.base', mask=None)
    p.fill(G.circle(x, y, R * 0.42), 'base')
    p.fill(G.circle(x, y, R * 0.26), f'{DARK.name}.base', mask=None)


# ============================================================================= vanilla-style parts
#
# Everything but the plating is built like vanilla power armor: a few big plates with flat faces
# (white, #ccc on the back), chamfer facets, dark recesses and black outlines - no small hardware.

GREY = _mat('mpa_grey', '#a3a3a3', light='#bababa', shade='#848484', deep='#626262', line='#3c3c3c')


def plate_tone(c):
    """Face tone of a plate turned to the camera: white, but #ccc for the whole back view."""
    return 'shade' if c.dir == 'north' else 'base'


def vplate(K, c, name, ring, z, mat=SHELL, tone=None, bevel=1.3):
    return K.block(name, ring, z, mat, tone=tone or plate_tone(c), bevel=bevel)


def side_face(p, ring_pts_outer, ring_pts_inner, tone='shade'):
    """Fill the band between two edges of a strip (its side face)."""
    p.fill(G.poly(list(ring_pts_outer) + list(ring_pts_inner)[::-1]), tone)


def recess(p, ring):
    p.fill(ring, f'{DARK.name}.base', mask=None)


def strip(K, c, name, pts, w, sgn, z, mat=SHELL, side=0.4):
    """A plate strip along the edge of the silhouette: ``pts`` is its outer edge (top to
    bottom), the strip is ``w`` wide inward (screen sign ``-sgn``); its outer ``side`` share is
    the side face, turned away from the camera."""
    inner = [(x - sgn * w, y) for x, y in pts]
    p = vplate(K, c, name, G.chamfer(G.poly(list(pts) + inner[::-1]), min(1.4 * c.k, w * 0.35)), z, mat)
    if p is not None and side > 0:
        mid = [(x - sgn * w * side, y) for x, y in pts]
        side_face(p, pts, mid, 'deep' if c.dir == 'north' else 'shade')
    return p


def path_strip(K, c, name, pts, w, z, mat=GREY):
    """A strip of width ``w`` along a polyline (a frame member seen from the side)."""
    P = np.asarray(pts, float)
    left, right = [], []
    for i in range(len(P)):
        if i == 0:
            t = P[1] - P[0]
        elif i == len(P) - 1:
            t = P[-1] - P[-2]
        else:
            t = unit(P[i + 1] - P[i]) + unit(P[i] - P[i - 1])
        n = perp(unit(t))
        left.append(P[i] + n * w / 2)
        right.append(P[i] - n * w / 2)
    p = vplate(K, c, name, G.chamfer(G.poly(left + right[::-1]), w * 0.3), z, mat)
    if p is not None:
        # lower half of the member in shade
        lo = [q for q in (left if left[0][1] > right[0][1] else right)]
        mid = [(a + b) / 2 for a, b in zip(left, right)]
        side_face(p, lo, mid, 'shade')
    return p


def hub_cap(K, c, name, x, y, r, z, mat=SHELL):
    """A joint cap seen end-on (from the side): round plate, dark ring, small centre."""
    p = K.block(name, G.circle(x, y, r), z, mat, tone=plate_tone(c), bevel=1.0)
    if p is not None:
        p.fill(G.circle(x, y, r * 0.62), f'{DARK.name}.base', mask=None)
        p.fill(G.circle(x, y, r * 0.36), f'{GREY.name}.base', mask=None)
    return p


def simple_canister(K, c, name, base, tip, r, z, window=True):
    """A canister: a white cylinder with its far side in shade, a dark collar at the mount and a
    window onto the fluid."""
    k = c.k
    base, tip = np.asarray(base, float), np.asarray(tip, float)
    ax = unit(tip - base)
    n = perp(ax)
    if n[0] < 0:
        n = -n
    L = float(np.hypot(*(tip - base)))
    ring = G.rounded(G.poly([base - n * r, tip - n * r, tip + n * r, base + n * r]), [0.6 * k, r * 0.9, r * 0.9, 0.6 * k])
    p = vplate(K, c, name, ring, z, bevel=0.0)
    if p is None:
        return p
    p.fill(G.poly([base + n * r * 0.35, tip + n * r * 0.35, tip + n * r * 1.2, base + n * r * 1.2]), 'deep' if c.dir == 'north' else 'shade')
    p.fill(G.poly([base - n * r * 1.2 - ax * k, base + ax * 3.0 * k - n * r * 1.2, base + ax * 3.0 * k + n * r * 1.2, base + n * r * 1.2 - ax * k]),
           f'{DARK.name}.base', mask=None)
    if window:
        a, b = base + ax * L * 0.36, base + ax * L * 0.78
        p.fill(G.poly([a - n * r * 0.38, b - n * r * 0.38, b + n * r * 0.28, a + n * r * 0.28]), f'{DARK.name}.deep', mask=None)
        p.fill(G.poly([a + ax * 1.0 * k - n * r * 0.22, b - ax * 1.0 * k - n * r * 0.22, b - ax * 1.0 * k + n * r * 0.1,
                       a + ax * 1.0 * k + n * r * 0.1]), f'{GEL.name}.base', mask=None)
    return p


# ============================================================================= body: exoframe

@register('Exoframe', 'body', layer=0.08)
def exoframe(K, c, fit):
    """Load-bearing exoframe, built like the armor: a frame on the back with a yoke over the
    shoulders and a hip belt, big actuators on the hips, and struts down the outside of the
    legs to the knees and feet, so the load goes into the ground. From the front only the yoke's
    ends on the shoulders, the hip actuators and the leg struts show; the back frame shows from
    behind and, edge-on, from the side."""
    k = c.k
    f = c.form
    lay = F.layout(c, fit)
    sq = lay['sq']
    y_hip = lay['y_belt'] + 2.5 * k
    y_bot = f.bot - 2.0 * k
    y_knee = y_hip + (y_bot - y_hip) * 0.55
    if c.dir == 'east':
        _exoframe_side(K, c, fit, lay, y_hip, y_knee, y_bot)
        return
    back = c.dir == 'north'
    hi = edge_hi(fit)
    under = opts(fit, 'Exoframe', under={})['under']
    hips, caps = {}, {}
    for side, s in front_sides(c):
        sgn = -1 if side == 'l' else 1

        def ex(y, lift):
            return X(c, fit, y, side, lift=lift, hi=hi)
        # leg strut from the hip actuator down to the foot, along the outside of the leg
        strip(K, c, f'strut{side}', [(ex(y, 1.0), y) for y in np.linspace(y_hip, y_bot - 1.0 * k, 6)], 4.0 * k, sgn, 2, GREY)
        fx0, fx1 = sorted((ex(y_bot, 1.0) + sgn * 0.6 * k, ex(y_bot, 1.0) - sgn * 7.0 * k))
        vplate(K, c, f'foot{side}', G.chamfer(G.rect(fx0, y_bot - 1.6 * k, fx1, y_bot + 1.6 * k), 0.8 * k), 2.2, GREY)
        _housing(K, c, f'knee{side}', ex(y_knee, 1.0), y_knee, sgn, 6.0 * k, 6.0 * k, 3)
        hips[side] = _housing(K, c, f'hip{side}', ex(y_hip, 1.0), y_hip, sgn, 8.5 * k * sq ** 0.5, 11.0 * k, 4)
        # the yoke's end over the shoulder (hidden under a wing or a pauldron)
        if s not in under:
            caps[side] = _yoke_cap(K, c, fit, side, sgn, 4.5)
    if not back:
        return
    cx = F.body_ext(c, F.vy(c, (lay['top'] + y_hip) / 2))[0]
    y_sh = yoke_y(c) + 2.0 * k
    # back frame: a spine column from the yoke to the hip belt
    hw = 4.0 * k * sq
    sp = vplate(K, c, 'spine', G.chamfer(G.rect(cx - hw, y_sh - 2.0 * k, cx + hw, y_hip - 2.0 * k), 1.6 * k), 2.6)
    if sp is not None:
        sp.fill(G.rect(cx + hw * 0.4, y_sh - 2.0 * k, cx + hw, y_hip - 2.0 * k), 'deep')
        for t in (0.25, 0.5, 0.75):
            y = y_sh + (y_hip - y_sh - 4.0 * k) * t
            recess(sp, G.rect(cx - hw + 1.0 * k, y - 0.7 * k, cx + hw - 1.0 * k, y + 0.7 * k))
    xl, xr = caps.get('l'), caps.get('r')
    xl = xl if xl is not None else cx - hw
    xr = xr if xr is not None else cx + hw
    yoke = vplate(K, c, 'yoke', G.chamfer(G.rect(xl, y_sh - 2.4 * k, xr, y_sh + 2.4 * k), 0.8 * k), 2.4, GREY)
    if yoke is not None:
        yoke.fill(G.rect(xl, y_sh + 0.6 * k, xr, y_sh + 2.4 * k), 'shade')
    belt = vplate(K, c, 'hipbelt', G.chamfer(G.rect(hips['l'], y_hip - 2.6 * k, hips['r'], y_hip + 2.6 * k), 0.8 * k), 2.5, GREY)
    if belt is not None:
        belt.fill(G.rect(hips['l'], y_hip + 0.8 * k, hips['r'], y_hip + 2.6 * k), 'shade')


def yoke_y(c):
    """Screen row just below the helmet, where the back frame's yoke runs across the shoulders."""
    return max(c.form.top + 0.22 * c.form.H, 60.0 * c.k)


def _yoke_cap(K, c, fit, side, sgn, z):
    """The end of the shoulder yoke, a plate over the top of the shoulder. Returns its inner x."""
    k = c.k
    lay = F.layout(c, fit)
    yt = max(F.shoulder_top(c, fit, side), yoke_y(c) - 6.0 * k)
    xo = X(c, fit, yt + 6.0 * k, side, lift=0.8, hi=edge_hi(fit))
    w = 8.5 * k * lay['sq'] ** 0.5
    xi = xo - sgn * w
    x0, x1 = sorted((xo, xi))
    y0, y1 = yt + 0.5 * k, yt + 10.5 * k
    p = vplate(K, c, f'yokecap{side}', G.chamfer(G.rect(x0, y0, x1, y1), [2.4 * k, 2.4 * k, 1.0 * k, 1.0 * k]), z)
    if p is not None:
        p.fill(G.rect(x0, y1 - 2.6 * k, x1, y1 + 1), 'deep' if c.dir == 'north' else 'shade')
        recess(p, G.rect(x0 + 1.4 * k, y0 + 3.0 * k, x1 - 1.4 * k, y0 + 4.2 * k))
    return xi


def _housing(K, c, name, xe, y, sgn, w, h, z):
    """A joint housing straddling the silhouette's edge at (xe, y): a chamfered shell block with
    its outer side face in shade and the joint's axle recess across it. Returns the x of its
    inner edge."""
    k = c.k
    x_out = xe + sgn * w * 0.3
    x_in = x_out - sgn * w
    x0, x1 = sorted((x_out, x_in))
    p = vplate(K, c, name, G.chamfer(G.rect(x0, y - h / 2, x1, y + h / 2), min(w, h) * 0.3), z)
    if p is not None:
        xs = x_out - sgn * w * 0.32
        p.fill(G.rect(min(x_out, xs), y - h / 2, max(x_out, xs), y + h / 2), 'deep' if c.dir == 'north' else 'shade')
        recess(p, G.rect(x0 + 0.8 * k, y - 0.8 * k, x1 - 0.8 * k, y + 0.8 * k))
    return x_in

def _exoframe_side(K, c, fit, lay, y_hip, y_knee, y_bot):
    """The exoframe from the side: the back frame edge-on, the yoke over the shoulder, the hip
    belt round to the hip actuator (its cap facing us), the leg strut, the knee and the foot."""
    k = c.k
    f = c.form
    sq = lay['sq']
    under = opts(fit, 'Exoframe', under={})['under']
    y_sh = yoke_y(c) + 2.0 * k
    xhp = f.d(F.vy(c, y_hip))[0] - 1.0 * k
    xkn = xhp + 2.5 * k
    xft = xhp
    xb0 = X(c, fit, y_sh, 'l', lift=0.4) + 0.5 * k
    xb1 = X(c, fit, y_hip - 3.0 * k, 'l', lift=0.4) + 0.5 * k
    # the back frame, standing off the back
    vplate(K, c, 'spine', G.chamfer(G.poly([(xb0 - 3.0 * k, y_sh - 2.0 * k), (xb0 + 2.0 * k, y_sh - 2.0 * k), (xb1 + 2.0 * k, y_hip - 2.0 * k),
                                            (xb1 - 3.0 * k, y_hip - 2.0 * k)]), 1.2 * k), 1.5, tone='shade')
    path_strip(K, c, 'hipbelt', [(xb1, y_hip), (xhp, y_hip)], 4.4 * k, 2)
    path_strip(K, c, 'strut', [(xhp, y_hip), (xkn, y_knee), (xft, y_bot - 1.0 * k)], 4.2 * k, 2)
    vplate(K, c, 'foot', G.chamfer(G.rect(xft - 4.0 * k, y_bot - 1.6 * k, xft + 5.0 * k, y_bot + 1.6 * k), 0.8 * k), 2.2, GREY)
    if 1 not in under:
        yt = max(F.shoulder_top(c, fit), yoke_y(c) - 6.0 * k)
        cx_sh, dd = f.d(F.vy(c, yt + 6.0 * k))
        path_strip(K, c, 'yoke', [(xb0, y_sh), (cx_sh - dd * 0.3, yt + 4.0 * k)], 4.4 * k, 2.4)
        cap = vplate(K, c, 'yokecap', G.chamfer(G.rect(cx_sh - dd * 0.5, yt + 0.5 * k, cx_sh + dd * 0.3, yt + 10.5 * k),
                                                [2.4 * k, 2.4 * k, 1.0 * k, 1.0 * k]), 4.5)
        if cap is not None:
            cap.fill(G.rect(cx_sh - dd * 0.5, yt + 8.0 * k, cx_sh + dd * 0.3, yt + 10.5 * k + 1), 'shade')
            recess(cap, G.rect(cx_sh - dd * 0.5 + 1.4 * k, yt + 3.6 * k, cx_sh + dd * 0.3 - 1.4 * k, yt + 4.8 * k))
    hub_cap(K, c, 'knee', xkn, y_knee, 4.0 * k, 3)
    hub_cap(K, c, 'hip', xhp, y_hip, 6.4 * k * sq ** 0.5, 4)


# ============================================================================= body: plating

def _chest_slab(K, c, fit):
    """Front appliqué slab: a thick plate with its edge thickness showing, a raised keel,
    inset side panels, bracket clamps at the top and big bolts."""
    k = c.k
    f = c.form
    y0, y1, lay = chest_rows(c, fit)
    y0 += 1.0 * k
    v0, v1 = F.vy(c, y0), F.vy(c, y1)
    if c.dir == 'east':
        lift, thick = 2.8, 5.0 * k
        pts_o = [(X(c, fit, y, 'r', lift=lift), y) for y in np.linspace(y0, y1, 6)]
        pts_i = [(x - thick, y) for x, y in pts_o]
        p = K.block('slab', G.chamfer(G.poly(pts_o + pts_i[::-1]), 1.4 * k), 6, SHELL, bevel=0.0)
        if p is None:
            return
        xs = [x for x, _ in pts_o]
        # front face / edge band / underside
        p.fill(G.poly(pts_o + [(x - 2.2 * k, y) for x, y in pts_o[::-1]]), 'base')
        p.fill(G.poly([(x - 2.2 * k, y) for x, y in pts_o] + [(x - thick, y) for x, y in pts_o[::-1]]), 'shade')
        p.fill(G.rect(min(xs) - thick - 1, y1 - 2.6 * k, max(xs) + 1, y1 + 1), 'deep')
        for t in (0.2, 0.75):
            y = y0 + (y1 - y0) * t
            K.bolt(p, X(c, fit, y, 'r', lift=lift) - 1.0 * k, y, 1.0 * k)
        bracket_over(K, c, 'clamp', xs[0] - thick * 0.5, y0, 6.0, 6.5)
        return
    if c.dir != 'south':
        return
    w = 0.6 if fit not in F.RECON_BUILT else 0.52
    lift = 2.4
    r = F.radius(c, lift)
    fv = v1 - 3.0 * k / f.H
    poly = [(-w + 0.1, v0), (w - 0.1, v0), (w, v0 + 0.06), (w, fv), (w - 0.12, v1), (-w + 0.12, v1), (-w, fv), (-w, v0 + 0.06)]
    p = surf(K, c, 'slab', poly, r, 6, SHELL, bevel=1.4)
    if p is None:
        return
    lip = c.form.ring('south', [(-w, fv), (w, fv), (w - 0.12, v1), (-w + 0.12, v1)], r)
    if len(lip) >= 3:
        p.fill(lip, 'shade')
        p.details.append(Line(G.poly([sP(c, t, fv, r) for t in np.linspace(-w + 0.02, w - 0.02, 8)]), 0.9 * k, 'deep'))
    keel_w = w * 0.3
    # inset side panels either side of the raised keel
    for s in (1, -1):
        a, b = sorted((s * (keel_w + 0.05), s * (w - 0.09)))
        pan = c.form.ring('south', [(a, v0 + 0.06), (b, v0 + 0.06), (b, fv - 0.03), (a, fv - 0.03)], r)
        if len(pan) >= 3:
            K.panel(p, G.simplify_ring(pan, 0.4 * k), 'base', w=0.8)
        xn, yn = sP(c, s * (w - 0.2), v0 + 0.1, r)
        K.notch(p, xn - 1.2 * k, yn - 0.7 * k, xn + 1.2 * k, yn + 0.7 * k)
    keel = surf(K, c, 'keel', [(-keel_w, v0 + 0.005), (keel_w, v0 + 0.005), (keel_w * 0.8, fv + 0.01), (-keel_w * 0.8, fv + 0.01)],
                F.radius(c, lift + 1.0), 6.5, SHELL, bevel=1.2)
    if keel is not None:
        xk, yk = sP(c, 0.0, (v0 + fv) / 2, F.radius(c, lift + 1.0))
        K.stencil(keel, xk - 3.0 * k, yk + 1.0 * k, 6.0 * k, 3)
    for s in (1, -1):
        for vv in (v0 + 0.08, fv - 0.05):
            xb, yb = sP(c, s * (w - 0.1), vv, r)
            K.bolt(p, xb, yb, 1.15 * k)
        xc, yc = sP(c, s * (w - 0.24), v0, r)
        bracket_over(K, c, f'clamp{s}', xc, yc, 7.0, 6.6)


def _pauldrons(K, c, fit, caps):
    """Layered shoulder plates standing out past the shoulder: an upper plate with a lit top face
    over a lower lame, bolted, with the lower edge's thickness showing."""
    k = c.k
    f = c.form
    lay = F.layout(c, fit)
    sq = lay['sq']
    back = c.dir == 'north'
    if c.dir == 'east':
        if 1 not in caps:
            return
        y0 = F.shoulder_top(c, fit) + 4.0 * k
        h = 16.0 * k * sq
        cx, dd = f.d(F.vy(c, y0 + h / 2))
        x0, x1 = cx - 0.66 * dd, cx + 0.46 * dd
        y1 = y0 + h
        lame = K.block('lame', G.chamfer(G.rect(x0 + 1.0 * k, y0 + h * 0.45, x1 - 1.0 * k, y1), [1.0 * k, 1.0 * k, 3.0 * k, 3.0 * k]), 5,
                       SHELL, bevel=1.0, tone='shade')
        if lame is not None:
            lame.fill(G.rect(x0, y1 - 2.6 * k, x1, y1), 'deep')
            K.bolts(lame, [(x0 + 4.0 * k, y1 - 6.0 * k), (x1 - 4.0 * k, y1 - 6.0 * k)])
        top = K.block('plate', G.chamfer(G.rect(x0, y0, x1, y0 + h * 0.58), [4.0 * k, 4.0 * k, 1.5 * k, 1.5 * k]), 5.5, SHELL, bevel=1.3)
        if top is not None:
            top.fill(G.rect(x0, y0 - 1, x1, y0 + 3.0 * k), 'light')
            top.fill(G.rect(x0, y0 + h * 0.58 - 2.6 * k, x1, y0 + h * 0.58), 'shade')
            K.stencil(top, x0 + 4.0 * k, y0 + 7.0 * k, 8.0 * k, 3)
        return
    for side, s in front_sides(c):
        if s not in caps:
            continue
        sgn = -1 if side == 'l' else 1
        yt = F.shoulder_top(c, fit, side) - 1.0 * k
        h = 17.0 * k * sq
        xo = X(c, fit, yt + h * 0.5, side, lift=3.2)
        w = 15.0 * k * sq
        xi = xo - sgn * w
        x0, x1 = min(xo, xi), max(xo, xi)
        y1 = yt + h
        ym = yt + h * 0.56
        drop = 3.5 * k
        # lower lame (behind), then the main plate
        if sgn < 0:
            lring = [(x0 + 1.0 * k, ym - 2.0 * k), (x1 - 2.0 * k, ym - 2.0 * k), (x1 - 2.0 * k, y1 - 1.0 * k), (x0 + 1.0 * k, y1 + drop)]
            mring = [(x1, yt + 3.0 * k), (x0 + 6.0 * k, yt), (x0, yt + 6.0 * k), (x0, ym + drop * 0.6), (x1, ym)]
        else:
            lring = [(x1 - 1.0 * k, ym - 2.0 * k), (x0 + 2.0 * k, ym - 2.0 * k), (x0 + 2.0 * k, y1 - 1.0 * k), (x1 - 1.0 * k, y1 + drop)]
            mring = [(x0, yt + 3.0 * k), (x1 - 6.0 * k, yt), (x1, yt + 6.0 * k), (x1, ym + drop * 0.6), (x0, ym)]
        lame = K.block(f'lame{side}', G.chamfer(G.poly(lring), 1.2 * k), 5, SHELL, bevel=1.0, tone='shade' if not back else 'deep')
        if lame is not None:
            lame.fill(G.poly([(x0 - 1, y1 - 3.0 * k + (drop if sgn < 0 else 0)), (x1 + 1, y1 - 3.0 * k + (drop if sgn > 0 else 0)),
                              (x1 + 1, y1 + drop + 2), (x0 - 1, y1 + drop + 2)]), 'deep')
            K.bolt(lame, (x0 + x1) / 2 + sgn * 3.0 * k, (ym + y1) / 2 + 1.0 * k, 0.9 * k)
        mp = K.block(f'plate{side}', G.chamfer(G.poly(mring), 1.4 * k), 5.5, SHELL, bevel=1.3, tone='shade' if back else 'base')
        if mp is None:
            continue
        mp.fill(G.poly([(x0 - 1, ym - 3.0 * k + (drop * 0.6 if sgn < 0 else 0)), (x1 + 1, ym - 3.0 * k + (drop * 0.6 if sgn > 0 else 0)),
                        (x1 + 1, ym + drop + 1), (x0 - 1, ym + drop + 1)]), 'shade' if not back else 'deep')
        K.bolts(mp, [(xo - sgn * 3.5 * k, yt + 6.0 * k), (xi + sgn * 4.0 * k, yt + 5.0 * k)])
        K.chevrons(mp, (x0 + x1) / 2, yt + 8.5 * k, 4.0 * k, 1.5 * k, 2)


@register('Plating', 'body', layer=0.44)
def plating(K, c, fit):
    """Bolt-on composite plates: a thick appliqué slab with a raised keel over the chest,
    clamped on with brackets, and layered pauldrons on both shoulders."""
    o = opts(fit, 'Plating', chest=True, caps=(1, -1))
    if o['chest']:
        _chest_slab(K, c, fit)
    _pauldrons(K, c, fit, o['caps'])


# ============================================================================= body: uranium plating

def _uranium_chest(K, c, fit):
    k = c.k
    f = c.form
    y0, y1, lay = chest_rows(c, fit)
    y0 += 1.0 * k
    v0, v1 = F.vy(c, y0), F.vy(c, y1)
    if c.dir == 'east':
        thick = 7.5 * k
        pts_o = [(X(c, fit, y, 'r', lift=4.0), y) for y in np.linspace(y0, y1, 6)]
        p = K.block('slab', G.chamfer(G.poly(pts_o + [(x - thick, y) for x, y in pts_o[::-1]]), 1.4 * k), 6, URAN, bevel=0.0)
        if p is None:
            return
        p.fill(G.poly(pts_o + [(x - 2.0 * k, y) for x, y in pts_o[::-1]]), f'{SHELL.name}.base', mask='r')
        p.fill(G.poly([(x - 4.6 * k, y) for x, y in pts_o] + [(x - thick, y) for x, y in pts_o[::-1]]), 'shade')
        xs = [x for x, _ in pts_o]
        p.fill(G.rect(min(xs) - thick - 1, y1 - 2.6 * k, max(xs) + 1, y1 + 1), 'deep')
        for t in (0.25, 0.7):
            y = y0 + (y1 - y0) * t
            K.bolt(p, X(c, fit, y, 'r', lift=4.0) - 3.2 * k, y, 1.0 * k)
        bracket_over(K, c, 'clamp', xs[0] - thick * 0.5, y0, 6.0, 6.5)
        return
    if c.dir != 'south':
        return
    w = 0.68 if fit not in F.RECON_BUILT else 0.6
    lift = 3.4
    r = F.radius(c, lift)
    fv = v1 - 3.8 * k / f.H
    poly = [(-w + 0.1, v0), (w - 0.1, v0), (w, v0 + 0.06), (w, fv), (w - 0.12, v1), (-w + 0.12, v1), (-w, fv), (-w, v0 + 0.06)]
    p = surf(K, c, 'slab', poly, r, 6, URAN, bevel=1.4)
    if p is None:
        return
    # dyed trim frame round the slab
    trim = c.form.ring('south', poly, r)
    p.details.append(Line(G.simplify_ring(trim, 0.4 * k), 2.4 * k, f'{SHELL.name}.shade', closed=True, mask='r'))
    lip = c.form.ring('south', [(-w, fv), (w, fv), (w - 0.12, v1), (-w + 0.12, v1)], r)
    if len(lip) >= 3:
        p.fill(lip, 'deep')
    third = w / 3
    for s in (1, -1):
        p.line([sP(c, s * third, v, r) for v in np.linspace(v0 + 0.03, fv - 0.01, 5)], 1.2 * k, 'deep')
    keel = surf(K, c, 'keel', [(-third + 0.03, v0 + 0.01), (third - 0.03, v0 + 0.01), (third * 0.8, fv), (-third * 0.8, fv)],
                F.radius(c, lift + 1.6), 6.5, URAN, bevel=1.2, tone='light')
    if keel is not None:
        xk, yk = sP(c, 0.0, (v0 + fv) / 2, F.radius(c, lift + 1.6))
        keel.fill(G.circle(xk, yk, 3.6 * k), f'{AMBER.name}.shade', mask=None)
        trefoil(K, keel, xk, yk, 3.0 * k)
    for s in (1, -1):
        for vv in (v0 + 0.08, fv - 0.05):
            xb, yb = sP(c, s * (w - 0.1), vv, r)
            K.bolt(p, xb, yb, 1.2 * k)
        xc, yc = sP(c, s * (w - 0.24), v0, r)
        bracket_over(K, c, f'clamp{s}', xc, yc, 7.0, 6.6)


def _uranium_pauldrons(K, c, fit, caps):
    """Heavy dark pauldrons with dyed trim."""
    k = c.k
    f = c.form
    lay = F.layout(c, fit)
    sq = lay['sq']
    back = c.dir == 'north'
    if c.dir == 'east':
        if 1 not in caps:
            return
        y0 = F.shoulder_top(c, fit) + 4.0 * k
        h = 19.0 * k * sq
        cx, dd = f.d(F.vy(c, y0 + h / 2))
        x0, x1 = cx - 0.68 * dd, cx + 0.48 * dd
        p = K.block('plate', G.chamfer(G.rect(x0, y0, x1, y0 + h), [4.0 * k, 4.0 * k, 2.0 * k, 2.0 * k]), 5.5, URAN, bevel=1.3)
        if p is not None:
            p.fill(G.rect(x0, y0 - 1, x1, y0 + 2.6 * k), f'{SHELL.name}.base', mask='r')
            p.fill(G.rect(x0, y0 + h - 3.0 * k, x1, y0 + h + 1), 'deep')
            K.seam(p, [(x0 + 1.0 * k, y0 + h * 0.5), (x1 - 1.0 * k, y0 + h * 0.5)], 1.2)
            K.bolts(p, [(x0 + 4.0 * k, y0 + 6.0 * k), (x1 - 4.0 * k, y0 + 6.0 * k)])
        return
    for side, s in front_sides(c):
        if s not in caps:
            continue
        sgn = -1 if side == 'l' else 1
        yt = F.shoulder_top(c, fit, side) - 1.0 * k
        h = 21.0 * k * sq
        xo = X(c, fit, yt + h * 0.5, side, lift=4.2)
        w = 17.0 * k * sq
        xi = xo - sgn * w
        x0, x1 = min(xo, xi), max(xo, xi)
        y1 = yt + h
        drop = 3.5 * k
        if sgn < 0:
            ring = [(x1, yt + 3.0 * k), (x0 + 6.0 * k, yt), (x0, yt + 6.0 * k), (x0, y1 + drop), (x1, y1)]
        else:
            ring = [(x0, yt + 3.0 * k), (x1 - 6.0 * k, yt), (x1, yt + 6.0 * k), (x1, y1 + drop), (x0, y1)]
        p = K.block(f'plate{side}', G.chamfer(G.poly(ring), 1.4 * k), 5.5, URAN, bevel=1.3, tone='shade' if back else 'base')
        if p is None:
            continue
        p.details.append(Line(G.poly(ring), 2.4 * k, f'{SHELL.name}.shade' if not back else f'{SHELL.name}.deep', closed=True, mask='r'))
        ym = yt + h * 0.5
        K.seam(p, [(x0 + 1.0 * k, ym + (drop * 0.5 if sgn < 0 else 0)), (x1 - 1.0 * k, ym + (drop * 0.5 if sgn > 0 else 0))], 1.2)
        p.fill(G.poly([(x0 - 1, y1 - 3.0 * k + (drop if sgn < 0 else 0)), (x1 + 1, y1 - 3.0 * k + (drop if sgn > 0 else 0)),
                       (x1 + 1, y1 + drop + 2), (x0 - 1, y1 + drop + 2)]), 'deep')
        K.bolts(p, [(xo - sgn * 3.5 * k, yt + 6.0 * k), (xi + sgn * 4.0 * k, yt + 5.0 * k), (xo - sgn * 3.5 * k, ym + 4.0 * k)])


@register('UraniumPlating', 'body', layer=0.44)
def uranium_plating(K, c, fit):
    """Uranium composite plating: heavy dark uranium-ceramic slabs in dyed trim frames - a chest
    slab with a trefoil on its keel and big pauldrons - in plating's places (the two can't be
    installed together)."""
    o = opts(fit, 'UraniumPlating', chest=True, caps=(1, -1))
    if o['chest']:
        _uranium_chest(K, c, fit)
    _uranium_pauldrons(K, c, fit, o['caps'])

@register('BiogelServos', 'body', layer=0.28)
def biogel_servos(K, c, fit):
    """Biogel servo housings over both elbows: a rounded armored housing on the outside of each
    elbow with a window onto the biogel; from the side, a round housing over the joint."""
    k = c.k
    lay = F.layout(c, fit)
    y = lay['y_elbow']
    sq = lay['sq']
    if c.dir == 'east':
        x = c.form.d(F.vy(c, y))[0] + 1.0 * k
        r = 5.6 * k * sq ** 0.5
        p = K.block('servo', G.circle(x, y, r), 2, SHELL, tone='base', bevel=1.2)
        if p is not None:
            p.fill(G.poly([(x - r, y + r * 0.35), (x + r, y + r * 0.35), (x + r, y + r), (x - r, y + r)]), 'shade')
            p.fill(G.circle(x, y, r * 0.6), f'{DARK.name}.base', mask=None)
            p.fill(G.circle(x, y, r * 0.38), f'{GEL.name}.base', mask=None)
            p.fill(G.circle(x - r * 0.1, y - r * 0.12, r * 0.14), f'{GEL.name}.light', mask=None)
        return
    for side, s in front_sides(c):
        sgn = -1 if side == 'l' else 1
        xe = X(c, fit, y, side, lift=0.6, hi=edge_hi(fit))
        w, h = 7.0 * k * sq ** 0.5, 13.0 * k
        x_out = xe + sgn * w * 0.35
        x_in = x_out - sgn * w
        x0, x1 = sorted((x_out, x_in))
        p = vplate(K, c, f'servo{side}', G.rounded(G.rect(x0, y - h / 2, x1, y + h / 2), min(w, h) * 0.45), 2)
        if p is None:
            continue
        xs = x_out - sgn * w * 0.34
        p.fill(G.rect(min(x_out, xs), y - h / 2, max(x_out, xs), y + h / 2), 'deep' if c.dir == 'north' else 'shade')
        if c.dir == 'south':
            xw = (x_in + xs) / 2
            p.fill(G.rounded(G.rect(xw - 1.2 * k, y - 3.6 * k, xw + 1.2 * k, y + 3.6 * k), 1.0 * k), f'{DARK.name}.base', mask=None)
            p.fill(G.rounded(G.rect(xw - 0.6 * k, y - 3.0 * k, xw + 0.6 * k, y + 3.0 * k), 0.5 * k), f'{GEL.name}.base', mask=None)
        else:
            recess(p, G.rect(x0 + 0.8 * k, y - 0.6 * k, x1 - 0.8 * k, y + 0.6 * k))


# ============================================================================= body: regenerators

@register('Regenerators', 'body', dirs=('east', 'north'), layer=0.6)
def regenerators(K, c, fit):
    """Neuromemetic regenerator canisters: two canisters out of the upper back either side of the
    spine, angled down and outwards, a window onto the regenerator fluid in each. From the side
    the near canister hides the far one."""
    k = c.k
    f = c.form
    lay = F.layout(c, fit)
    sq = lay['sq']
    y_top = f.top + 0.16 * f.H
    L = 24.0 * k * sq ** 0.5
    r = 4.2 * k * sq ** 0.4
    if c.dir == 'east':
        xb = X(c, fit, y_top + 6.0 * k, 'l', lift=0.0) + 4.0 * k
        ang = math.radians(26)
        b = np.array([xb, y_top + 2.0 * k])
        simple_canister(K, c, 'can', b, b + np.array([-math.sin(ang), math.cos(ang)]) * L, r, 2)
        return
    cx, a_ = F.body_ext(c, F.vy(c, y_top + 10.0 * k))
    span = min(a_ * 0.42, 15.0 * k * sq)
    ang = math.radians(14)
    for s in (-1, 1):
        b = np.array([cx + s * span, y_top])
        simple_canister(K, c, f'can{s}', b, b + np.array([s * math.sin(ang), math.cos(ang)]) * L, r, 2)


# ============================================================================= body: second heart

def _heart(p, x, y, r):
    """A heart as an organ: dark red muscle with a lighter lobe and vessels at the top."""
    pts = []
    for t in np.linspace(0, 2 * PI, 48):
        hx = 16 * math.sin(t) ** 3
        hy = -(13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t))
        pts.append((x + hx / 17 * r * 0.9 + 0.12 * r * math.sin(t * 2), y + hy / 17 * r))
    p.fill(G.poly(pts), f'{RED.name}.shade', mask=None)
    p.fill(G.ellipse(x - r * 0.3, y - r * 0.2, r * 0.36, r * 0.28), f'{RED.name}.base', mask=None)
    p.fill(G.rect(x - r * 0.12, y - r * 1.25, x + r * 0.16, y - r * 0.55), f'{RED.name}.deep', mask=None)
    p.fill(G.rect(x + r * 0.28, y - r * 1.1, x + r * 0.5, y - r * 0.6), f'{RED.name}.deep', mask=None)


@register('SecondHeart', 'body', dirs=('east', 'north'), layer=0.7)
def second_heart(K, c, fit):
    """Second heart: an armored housing in the middle of the upper back with a porthole onto the
    heart; from the side, the housing standing out of the back."""
    k = c.k
    y0, y1, lay = back_rows(c, fit)
    sq = lay['sq']
    w, h = 6.5 * k * sq ** 0.5, 8.0 * k * sq ** 0.5
    cy = y0 + (y1 - y0) * 0.5
    if c.dir == 'east':
        xb = X(c, fit, cy, 'l', lift=0.0) + 1.0 * k
        p = vplate(K, c, 'housing', G.chamfer(G.rect(xb - 5.0 * k, cy - h, xb + 1.0 * k, cy + h), 1.6 * k), 2, tone='shade')
        if p is not None:
            p.fill(G.rect(xb - 5.0 * k, cy + h * 0.6, xb + 1.0 * k, cy + h), 'deep')
            recess(p, G.rect(xb - 5.0 * k, cy - h * 0.5, xb - 3.6 * k, cy + h * 0.4))
        return
    cx = F.body_ext(c, F.vy(c, cy))[0]
    p = vplate(K, c, 'housing', G.chamfer(G.rect(cx - w, cy - h, cx + w, cy + h), w * 0.45), 2)
    if p is None:
        return
    p.fill(G.rect(cx - w, cy + h * 0.65, cx + w, cy + h), 'deep')
    R = min(w, h) * 0.62
    p.fill(G.circle(cx, cy - 0.5 * k, R), f'{GREY.name}.base', mask=None)
    p.fill(G.circle(cx, cy - 0.5 * k, R * 0.78), f'{DARK.name}.deep', mask=None)
    _heart(p, cx, cy - 0.3 * k, R * 0.5)


# ============================================================================= body: subpersona

@register('Subpersona', 'body', dirs=('south', 'east'), layer=0.8)
def subpersona(K, c, fit):
    """Auxiliary subpersona: an armored case over the belt buckle with three subcore cartridges
    slotted into its face."""
    k = c.k
    lay = F.layout(c, fit)
    sq = lay['sq']
    y0 = lay['y_belt'] - 4.0 * k
    y1 = lay['y_belt'] + 7.0 * k * lay['sv'] ** 0.5
    if c.dir == 'east':
        xr = X(c, fit, (y0 + y1) / 2, 'r', lift=3.0)
        p = vplate(K, c, 'case', G.chamfer(G.rect(xr - 6.0 * k, y0, xr, y1), 1.4 * k), 7)
        if p is not None:
            p.fill(G.rect(xr - 6.0 * k, y1 - 2.4 * k, xr + 1, y1 + 1), 'shade')
            for t in (0.25, 0.55):
                yy = y0 + (y1 - y0) * t
                recess(p, G.rect(xr - 1.6 * k, yy, xr + 1, yy + 2.0 * k))
        return
    cx = F.body_ext(c, F.vy(c, y0))[0]
    W = 10.0 * k * sq
    p = vplate(K, c, 'case', G.chamfer(G.rect(cx - W, y0, cx + W, y1), 2.0 * k), 7)
    if p is None:
        return
    p.fill(G.rect(cx - W, y1 - 2.6 * k, cx + W, y1 + 1), 'shade')
    cw = 2 * W / 3
    for i in range(3):
        xm = cx - W + cw * (i + 0.5)
        recess(p, G.rect(xm - cw * 0.26, y0 + 2.4 * k, xm + cw * 0.26, y1 - 3.6 * k))
        p.fill(G.rect(xm - cw * 0.26, y0 + 2.4 * k, xm + cw * 0.26, y0 + 3.6 * k), f'{GREY.name}.base', mask=None)


# ============================================================================= body: thermal regulator

@register('ThermalFins', 'body', dirs=('east', 'north'), layer=0.36)
def thermal_regulator(K, c, fit):
    """Thermal regulation unit: a radiator plate across the lower back with vent slits; from the
    side, the plate standing out of the back."""
    k = c.k
    lay = F.layout(c, fit)
    y0 = lay['y_back'] + 1.0 * k
    y1 = min(lay['y_belt_back'] + 4.0 * k * lay['sv'], y0 + 14.0 * k)
    if c.dir == 'east':
        xb = X(c, fit, (y0 + y1) / 2, 'l', lift=3.0)
        p = vplate(K, c, 'radiator', G.chamfer(G.rect(xb, y0, xb + 5.0 * k, y1), 1.2 * k), 2, tone='shade')
        if p is not None:
            for i in range(3):
                yy = y0 + (y1 - y0) * (i + 1) / 4
                recess(p, G.rect(xb - 1, yy - 0.7 * k, xb + 2.4 * k, yy + 0.7 * k))
        return
    cx = F.body_ext(c, F.vy(c, (y0 + y1) / 2))[0]
    W = 13.0 * k * lay['sq']
    p = vplate(K, c, 'radiator', G.chamfer(G.rect(cx - W, y0, cx + W, y1), 2.0 * k), 2)
    if p is None:
        return
    p.fill(G.rect(cx - W, y1 - 2.4 * k, cx + W, y1 + 1), 'deep')
    n = 3
    for i in range(n):
        yy = y0 + 2.0 * k + (y1 - y0 - 5.0 * k) * (i + 0.5) / n
        recess(p, G.rect(cx - W + 2.4 * k, yy - 0.6 * k, cx + W - 2.4 * k, yy + 0.6 * k))


# ============================================================================= body: rigidity matrix

@register('RigidityMatrix', 'body', dirs=('south', 'east'), layer=0.14)
def rigidity_matrix(K, c, fit):
    """Rigidity matrix: a braced plate over the front of each thigh, a lattice window with a
    cross strut in it and a lock bar across the top; from the side, the plate standing off the
    front of the thigh."""
    k = c.k
    f = c.form
    lay = F.layout(c, fit)
    sq = lay['sq']
    y0 = lay['y_belt'] - 1.0 * k
    y1 = f.bot - 2.0 * k
    if c.dir == 'east':
        xf = X(c, fit, (y0 + y1) / 2, 'r', lift=2.6)
        p = vplate(K, c, 'plate', G.chamfer(G.rect(xf - 5.5 * k, y0, xf, y1), [1.0 * k, 1.8 * k, 1.8 * k, 1.0 * k]), 2)
        if p is not None:
            p.fill(G.rect(xf - 2.2 * k, y0, xf + 1, y1), 'shade')
            p.fill(G.rect(xf - 5.5 * k, y1 - 2.4 * k, xf + 1, y1 + 1), 'shade')
            p.fill(G.rect(xf - 5.5 * k - 1, y0 + 1.6 * k, xf + 1, y0 + 3.4 * k), f'{GREY.name}.base', mask=None)
        return
    cx, half = F.body_ext(c, F.vy(c, (y0 + y1) / 2))
    h0 = F.body_ext(c, F.vy(c, y0))[1] - 1.5 * k
    h1 = F.body_ext(c, F.vy(c, y1 - 2.0 * k))[1] - 1.5 * k
    for s in (-1, 1):
        xm = s * min(9.5 * k * sq, half * 0.5)
        w = min(7.0 * k * sq, half * 0.34)
        # the plate's corners, kept inside the thigh as it tapers to the knee
        xa0, xb0 = max(xm - w, -h0), min(xm + w, h0)
        xa1, xb1 = max(xm - w * 0.85, -h1), min(xm + w * 0.85, h1)
        if s > 0:
            xa0, xa1 = max(xa0, 1.5 * k), max(xa1, 1.5 * k)
        else:
            xb0, xb1 = min(xb0, -1.5 * k), min(xb1, -1.5 * k)
        pts = [(cx + xa0, y0), (cx + xb0, y0), (cx + xb1, y1), (cx + xa1, y1)]
        p = vplate(K, c, f'plate{s}', G.chamfer(G.poly(pts), 1.6 * k), 2)
        if p is None:
            continue
        x0, x1 = cx + min(xa0, xa1), cx + max(xb0, xb1)
        p.fill(G.rect(x0 - 1, y1 - 2.4 * k, x1 + 1, y1 + 1), 'shade')
        p.fill(G.rect(x0 - 1, y0 + 1.6 * k, x1 + 1, y0 + 3.4 * k), f'{GREY.name}.base', mask=None)
        # the lattice window, a cross strut standing in it
        a, b = y0 + 5.0 * k, y1 - 3.6 * k
        if b - a < 3.0 * k:
            continue
        ta, tb = (a - y0) / (y1 - y0), (b - y0) / (y1 - y0)

        def at(xt, xbm, t, inset):
            return cx + xt + (xbm - xt) * t + inset
        q = [(at(xa0, xa1, ta, 1.6 * k), a), (at(xb0, xb1, ta, -1.6 * k), a), (at(xb0, xb1, tb, -1.6 * k), b), (at(xa0, xa1, tb, 1.6 * k), b)]
        if q[1][0] - q[0][0] < 3.0 * k:
            continue
        recess(p, G.chamfer(G.poly(q), 0.6 * k))
        # (a detail that inherits the mask leaves the recess's black under it: dye it explicitly)
        p.line([q[0], q[2]], 1.3 * k, 'base', mask=SHELL.mask)
        p.line([q[1], q[3]], 1.3 * k, 'base', mask=SHELL.mask)


# ============================================================================= body: longjump hydraulics

@register('LongjumpHydraulics', 'body', dirs=('east', 'north'), layer=0.2)
def longjump_hydraulics(K, c, fit):
    """Longjump hydraulics: a heavy ram down the back of each leg from the hip to the heel; its
    heel pivot turns about the pawn's left-right axis, so it is a round cap from the side and a
    barrel from behind. From the side the near ram hides the far one."""
    k = c.k
    f = c.form
    lay = F.layout(c, fit)
    sq = lay['sq']
    y_bot = f.bot - 2.0 * k
    y0 = lay['y_belt_back'] - 1.0 * k      # from under the lower back's edge
    r = 4.0 * k * sq ** 0.4
    if c.dir == 'east':
        xt = X(c, fit, y0 + 2.0 * k, 'l', lift=0.0) + r * 0.7
        xb = X(c, fit, y_bot - 4.0 * k, 'l', lift=0.0) + r * 0.4
        _ram(K, c, 'ram', xt, y0, xb, y_bot, r)
        hub_cap(K, c, 'heel', xb, y_bot, 3.2 * k, 2.5, GREY)
        return
    cx = F.body_ext(c, F.vy(c, (y0 + y_bot) / 2))[0]
    for s in (-1, 1):
        xa = cx + s * 9.0 * k * sq
        xb = xa + s * 1.0 * k
        _ram(K, c, f'ram{s}', xa, y0, xb, y_bot, r)
        bar = vplate(K, c, f'heel{s}', G.rounded(G.rect(xb - 4.0 * k, y_bot - 1.8 * k, xb + 4.0 * k, y_bot + 1.8 * k), 1.5 * k), 2.5, GREY)
        if bar is not None:
            recess(bar, G.rect(xb - 4.0 * k, y_bot - 0.4 * k, xb + 4.0 * k, y_bot + 0.4 * k))

def _ram(K, c, name, x0, y0, x1, y1, r):
    """A hydraulic ram from (x0, y0) to (x1, y1): a white cylinder body over the top 60% with its
    far side in shade and a dark seal band at its foot, a grey rod below."""
    k = c.k
    ym = y0 + (y1 - y0) * 0.6
    xm = x0 + (x1 - x0) * 0.6
    vplate(K, c, name + '_rod', G.poly([(xm - r * 0.45, ym - 2.0 * k), (xm + r * 0.45, ym - 2.0 * k), (x1 + r * 0.45, y1), (x1 - r * 0.45, y1)]),
           1.5, GREY, bevel=0.0)
    body = vplate(K, c, name, G.rounded(G.poly([(x0 - r, y0), (x0 + r, y0), (xm + r, ym), (xm - r, ym)]), [r * 0.8, r * 0.8, 0.6 * k, 0.6 * k]),
                  2, bevel=0.0)
    if body is not None:
        body.fill(G.poly([(x0 + r * 0.3, y0), (x0 + r, y0), (xm + r, ym), (xm + r * 0.3, ym)]), 'deep' if c.dir == 'north' else 'shade')
        recess(body, G.rect(min(x0, xm) - r - 1, ym - 1.8 * k, max(x0, xm) + r + 1, ym))


# ============================================================================= helmet helpers

def hside(c, fit, s, ph0, ph1):
    """(screen x of the helmet's edge, outward sign) on the pawn's side s (+1 right, -1 left),
    south and north views."""
    side = F.screen_side(c.dir, s * PI / 2)
    r_side = F.helm_side(fit, c.dir, side, ph0, ph1)
    sgn = -1 if side == 'l' else 1
    return F.head_edge_x(c, fit, side, (ph0 + ph1) / 2, r_side), sgn


def edge_curve(c, fit, s, ph0, ph1, n=7, out=0.0):
    """Points along the helmet's side edge between two latitudes (top to bottom), ``out`` px
    at 128 outside it."""
    side = F.screen_side(c.dir, s * PI / 2)
    sgn = -1 if side == 'l' else 1
    pts = []
    for ph in np.linspace(ph1, ph0, n):
        r_side = F.helm_side(fit, c.dir, side, ph - 0.12, ph + 0.12)
        pts.append((F.head_edge_x(c, fit, side, ph, r_side) + sgn * out * c.k, F.head_y(c, ph)))
    return pts, sgn

def side_pod(K, c, fit, s, ph0, ph1, inner, outer, z, name, chamfer=2.2, east_x=(-4.0, 14.0)):
    """A housing built out of the helmet's side (pawn's right s=1 / left s=-1) between two
    latitudes: its inner side follows the helmet's edge ``inner`` px at 128 inside it, its outer
    side stands ``outer`` px out (south/north). East view (right side only): a housing on the
    side of the head over ``east_x`` (px at 128 from the head's centre). Built like the helmet:
    a flat face, its outer side face and underside in shade. Returns a dict (part, sgn, x_out,
    x_in, x_side, x0, x1, y0, y1) or None."""
    k = c.k
    hf = c.form
    y0, y1 = F.head_y(c, ph1), F.head_y(c, ph0)
    if c.dir == 'east':
        if s < 0:
            return None
        x0, x1 = hf.cx + east_x[0] * k, hf.cx + east_x[1] * k
        p = vplate(K, c, name, G.chamfer(G.rect(x0, y0, x1, y1), [chamfer * k, chamfer * 1.4 * k, chamfer * 0.8 * k, chamfer * 0.8 * k]), z)
        if p is None:
            return None
        p.fill(G.rect(x0 - 1, y1 - 2.6 * k, x1 + 1, y1 + 1), 'shade')
        return dict(part=p, sgn=1, x_out=x1, x_in=x0, x_side=x1, y0=y0, y1=y1, x0=x0, x1=x1)
    pts_in, sgn = edge_curve(c, fit, s, ph0, ph1, 7, out=-inner)
    xe, _ = hside(c, fit, s, ph0, ph1)
    xo = xe + sgn * outer * k
    ring = G.chamfer(G.poly(pts_in + [(xo, pts_in[-1][1]), (xo, pts_in[0][1])]), chamfer * k)
    p = vplate(K, c, name, ring, z)
    if p is None:
        return None
    back = c.dir == 'north'
    xs = xo - sgn * 2.4 * k
    p.fill(G.rect(min(xo, xs), y0 - 1, max(xo, xs), y1 + 1), 'deep' if back else 'shade')
    xin = min(x for x, _ in pts_in) if sgn > 0 else max(x for x, _ in pts_in)
    p.fill(G.rect(min(xo, xin) - 1, y1 - 2.4 * k, max(xo, xin) + 1, y1 + 1), 'deep' if back else 'shade')
    return dict(part=p, sgn=sgn, x_out=xo, x_in=xin, x_side=xs, y0=y0, y1=y1, x0=min(xo, xin), x1=max(xo, xin))


def _phi_at(c, y):
    """Head latitude of screen row y."""
    hf = c.form
    return math.asin(max(-1.0, min(1.0, (hf.cy - y) / (hf.ry * 0.92))))


def head_pt(c, u, v, w):
    """Screen point of a 3D point near the head, in head units: u toward the pawn's right, v up,
    w forward (the head form's rx, 0.92 ry and rx), projected the way HeadForm.P projects."""
    hf = c.form
    x, z = {'south': (-u, w), 'north': (u, -w)}.get(c.dir, (w, u))
    return hf.cx + x * hf.rx, hf.cy - v * hf.ry * 0.92 + z * hf.ry * TILT * 0.55


def clip_convex(ring, clip):
    """``ring`` clipped to the convex polygon ``clip`` (Sutherland-Hodgman)."""
    clip = np.asarray(clip, float)
    if G.signed_area(clip) < 0:
        clip = clip[::-1]
    out = [tuple(q) for q in np.asarray(ring, float)]
    for i in range(len(clip)):
        a, b = clip[i], clip[(i + 1) % len(clip)]

        def inside(q):
            return (b[0] - a[0]) * (q[1] - a[1]) - (b[1] - a[1]) * (q[0] - a[0]) >= 0

        def cut(p, q):
            d1 = (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])
            d2 = (b[0] - a[0]) * (q[1] - a[1]) - (b[1] - a[1]) * (q[0] - a[0])
            t = d1 / (d1 - d2)
            return (p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t)
        src, out = out, []
        for j in range(len(src)):
            p, q = src[j - 1], src[j]
            if inside(q):
                if not inside(p):
                    out.append(cut(p, q))
                out.append(q)
            elif inside(p):
                out.append(cut(p, q))
        if len(out) < 3:
            return np.zeros((0, 2))
    return G.poly(out)


# ============================================================================= helmet: plating

def _brow_guard(K, c, fit, o):
    """Brow guard: a heavy visor hood across the upper face, following the dome, with its lower
    lip's thickness showing, bolted at the temples, a centre ridge."""
    k = c.k
    hf = c.form
    p0, p1 = o['phi']
    w = o['w']
    if c.dir == 'east':
        rf = F.helm_side(fit, 'east', 'r', p0, p1, 0.75, 1.3)
        pts = [(F.head_edge_x(c, fit, 'r', ph, rf) + 2.8 * k, F.head_y(c, ph)) for ph in np.linspace(p1, p0, 6)]
        inner = [(x - 8.0 * k, y) for x, y in pts]
        p = K.block('brow', G.chamfer(G.poly(pts + inner[::-1]), 1.4 * k), 2, SHELL, bevel=0.0)
        if p is None:
            return
        p.fill(G.poly(pts + [(x - 2.4 * k, y) for x, y in pts[::-1]]), 'base')
        p.fill(G.poly([(x - 2.4 * k, y) for x, y in pts] + inner[::-1]), 'shade')
        yb = max(y for _, y in pts)
        p.fill(G.rect(min(x for x, _ in inner) - 1, yb - 2.4 * k, max(x for x, _ in pts) + 1, yb + 1), 'deep')
        K.bolt(p, inner[2][0] + 2.5 * k, inner[2][1], 1.0 * k)
        return
    r = F.helm_side(fit, 'south', 'l', p0, p1, 0.9, 1.25) + 0.1
    # hood: wide at the temples, dipping to a point over the nose bridge
    top = [(t, p1 - 0.06 * (1 - abs(t) / w)) for t in np.linspace(-w, w, 9)]
    bot = [(t, p0 - 0.1 * max(0.0, 1 - abs(t) / (w * 0.5))) for t in np.linspace(w, -w, 9)]
    ring = hf.ring(top + bot, r)
    if len(ring) < 3:
        return
    p = K.block('brow', G.simplify_ring(ring, 0.4 * k), 2, SHELL, bevel=1.4)
    if p is None:
        return
    lip = hf.ring([(t, p0 - 0.1 * max(0.0, 1 - abs(t) / (w * 0.5)) + 0.07) for t in np.linspace(-w, w, 9)] + bot, r)
    if len(lip) >= 3:
        p.fill(G.simplify_ring(lip, 0.4 * k), 'shade')
    ridge = hf.ring([(-0.12, p0 - 0.05), (0.12, p0 - 0.05), (0.08, p1 - 0.04), (-0.08, p1 - 0.04)], r + 0.04)
    K.block('ridge', G.simplify_ring(ridge, 0.4 * k), 2.5, SHELL, bevel=1.0, tone='light')
    for sd in (1, -1):
        x, y = hf.P(sd * (w - 0.14), (p0 + p1) / 2 + 0.02, r)
        K.bolt(p, x, y, 1.15 * k)
        xn, yn = hf.P(sd * (w * 0.5), (p0 + p1) / 2 + 0.06, r)
        K.notch(p, xn - 1.4 * k, yn - 0.6 * k, xn + 1.4 * k, yn + 0.6 * k)


# The great helm's shape (head units; see _great_helm) and its variations, picked per helmet with
# the 'variant' option: 'wedge' (broad plates over the ear pieces under a lower point, used on
# both cataphract helmets), 'visor' (a visor over a chin plate, the plates meeting at a hard fold),
# 'keel' (one plate a side, a raised keel along the joint) and 'prow' (narrow plates under a tall
# point). In uranium, 'skin' picks the plates' look: a composite texture over the dark uranium
# plates in their dyed trim, 'laminate' (bonded layers, used on both cataphract helmets), 'tiles'
# (ceramic tiles) or 'hex' (hexagonal tiles); None (plain uranium plates); or 'inlay' (dark
# uranium inlays set into composite plates).
HELM = dict(v=(1.08, -1.0), ridge=1.32, reach=0.85, slope=0.95, back=(0.3, -0.95), lip=0.12, inset=True, keel=0.07, keel_w=0.07,
            split=None, bolts=((0.86, 0.14), (0.86, 0.86)), stencil=False, mat=SHELL, trefoil=False, skin=None, cams=None)

# Camera clusters for the great helm ('cams'), on the pawn's left side of the face, their lenses
# facing forward with the face whatever the plate's slope: round from the front, edge-on from the
# side. Head units: u toward the pawn's right, v up; each lens (u, v, radius); 'front' is the
# depth of the lenses' faces (the joint of the plates stands at 'ridge').
CAMS = {
    # three lenses on gunmetal tubes standing out through the plate
    'tubes': dict(lenses=((-0.24, -0.08, 0.15), (-0.53, 0.17, 0.08), (-0.53, -0.31, 0.08)), front=1.32),
    # a dyed housing built out of the plate, its flat front facing forward with the lenses in it
    'block': dict(box=(-0.12, -0.68, 0.16, -0.36), lenses=((-0.3, -0.1, 0.15), (-0.57, 0.04, 0.075), (-0.57, -0.23, 0.075)),
                  front=1.32),
    # a narrow dyed column with three lenses stacked, like the multispectral sensor's
    'column': dict(box=(-0.24, -0.52, 0.38, -0.56), lenses=((-0.38, 0.21, 0.105), (-0.38, -0.08, 0.105), (-0.38, -0.37, 0.105)),
                   front=1.32),
    # a port cut into the plate, the helmet's own cameras looking out of it from behind the plate
    'port': dict(box=(-0.12, -0.68, 0.16, -0.36), lenses=((-0.3, -0.1, 0.15), (-0.57, 0.04, 0.075), (-0.57, -0.23, 0.075)),
                 front=0.45),
}
HELM_VARIANTS = {
    'visor': dict(keel=0, split=-0.25, bolts=((0.85, 0.22), (0.85, 0.8))),
    'keel': {},
    'wedge': dict(v=(0.95, -1.0), back=(0.2, -0.95), reach=0.95, slope=1.1, keel=0.05, keel_w=0.05,
                  bolts=((0.88, 0.18), (0.88, 0.5), (0.88, 0.82))),
    'prow': dict(v=(1.3, -1.0), back=(0.35, -0.95), reach=0.78, keel=0.09, keel_w=0.08, stencil=True, bolts=((0.82, 0.12), (0.82, 0.86))),
}


def _great_helm(K, c, fit, o):
    """Great-helm faceplate: two thick composite plates over the front of the helmet, joined
    at a hard edge down the middle of the face that stands upright in front of the helmet and
    rises to a point over the brow; each plate slopes back from it to the side of the helmet.
    Built in 3D: from the front the lit plate and the shaded one meet under the point; from the
    side the near plate shows, the joint its upright front edge. Detailed like the body
    plating: the plates' thickness and lower lip show, with an inset panel and bolts, and as
    options a raised keel along the joint and a split into a visor over a chin plate. In
    uranium (mat URAN) the plates carry a trefoil on the pawn's right plate and take one of the
    skins (see HELM)."""
    k = c.k
    vt, vb = o['v']                  # the joint's top (the point) and bottom (head units)
    wr = o['ridge']                  # how far forward the joint stands
    ue, dw = o['reach'], o['slope']  # the plates' back edges: how far out and how far back
    vbt, vbb = o['back']             # the back edges' top and bottom
    lip = o['lip']                   # the lower lip's height (head units)
    skin = o['skin'] if o['mat'] is URAN else None
    # 'inlay': uranium set into composite plates; the other skins texture the uranium itself
    mat = SHELL if skin == 'inlay' else o['mat']
    east = c.dir == 'east'
    L = math.hypot(ue, dw)           # a plate's true width (head units)

    def pt(t, v, side, dz=0.0):
        """A point on a plate: t from the joint (0) to the back edge (1), at height v, on the
        pawn's right (side 1) or left (-1); dz stands it forward of the plate."""
        return head_pt(c, side * ue * t, v, wr - dw * t + dz)

    def top(t):
        return vt + (vbt - vt) * t

    def bot(t):
        return vb + (vbb - vb) * t

    def band(side, t0, t1, va, vb_, n=4, dz=0.0):
        """Strip of the plate between heights va(t) and vb_(t) from t0 to t1."""
        ts = np.linspace(t0, t1, n)
        return G.poly([pt(t, va(t), side, dz) for t in ts] + [pt(t, vb_(t), side, dz) for t in ts[::-1]])

    def plate(name, side, va, vb_, z, tones, t1=1.0, dz=0.0, inset=True):
        hi, lo = tones
        outline = band(side, 0, t1, va, vb_, 2, dz)
        p = vplate(K, c, name, outline, z, mat, tone=hi, bevel=1.3)
        if p is None:
            return None
        # the top edge's thickness, lit from above, and the lower lip
        p.fill(band(side, 0, t1, va, lambda t: va(t) - 0.035, dz=dz), 'light' if hi == 'base' else 'base')
        if lip:
            p.fill(band(side, 0, t1, lambda t: vb_(t) + lip, vb_, dz=dz), lo)
            p.line([pt(t, vb_(t) + lip, side, dz) for t in np.linspace(0, t1, 4)], 0.8 * k, 'deep')
        if skin == 'inlay' and inset:
            # a dark uranium inlay where the composite plate's inset panel would be
            inlay = band(side, 0.2, t1 - 0.14, lambda t: va(t) - 0.15, lambda t: vb_(t) + lip + 0.09, dz=dz)
            p.fill(inlay, f'{URAN.name}.{"base" if hi == "base" else "shade"}', mask=None)
            p.details.append(Line(inlay, 1.0 * k, f'{URAN.name}.line', closed=True, mask=None))
        elif skin and inset:
            texture(p, side, va, vb_, t1, dz, hi)
        elif inset:
            K.panel(p, band(side, 0.2, t1 - 0.14, lambda t: va(t) - 0.15, lambda t: vb_(t) + lip + 0.09, dz=dz), hi, w=0.8)
        if mat is URAN:
            # the dyed trim frame round the uranium plate
            p.details.append(Line(outline, 2.4 * k, f'{SHELL.name}.{"shade" if hi == "base" else "deep"}', closed=True, mask='r'))
        return p

    def texture(p, side, va, vb_, t1, dz, hi):
        """Composite texture over a uranium plate, laid out on the plate so it foreshortens
        with it: ceramic tiles in staggered rows, hexagonal tiles, or bonded layers."""
        seam = 'deep' if hi == 'base' else 'line'
        vmax, vmin = max(va(0), va(t1)), min(vb_(0), vb_(t1)) + lip
        if skin == 'tiles':
            rows = np.arange(vmax - 0.2, vmin, -0.21)
            edges = [vmax] + list(rows) + [vmin]
            for r, (ya, yb) in enumerate(zip(edges[:-1], edges[1:])):
                if r:
                    p.line([pt(0, ya, side, dz), pt(t1, ya, side, dz)], 0.9 * k, seam)
                    p.line([pt(0, ya - 0.025, side, dz), pt(t1, ya - 0.025, side, dz)], 0.5 * k, 'light' if hi == 'base' else 'base')
                for t in (np.arange(0.3, t1, 0.3) if r % 2 else np.arange(0.15, t1, 0.3)):
                    p.line([pt(t, ya, side, dz), pt(t, yb, side, dz)], 0.9 * k, seam)
        elif skin == 'hex':
            r = 0.1
            for i in range(-1, int(L / (1.5 * r)) + 2):
                for j in range(-1, int((vmax - vmin) / (math.sqrt(3) * r)) + 2):
                    d0 = i * 1.5 * r
                    v0_ = vmin + j * math.sqrt(3) * r + (i % 2) * math.sqrt(3) / 2 * r
                    ring_ = [pt((d0 + r * math.cos(a)) / L, v0_ + r * math.sin(a), side, dz) for a in np.radians(np.arange(0, 360, 60))]
                    p.details.append(Line(G.poly(ring_), 0.8 * k, seam, closed=True))
        elif skin == 'laminate':
            v = vmax - 0.08
            i = 0
            while v > vmin:
                p.fill(G.poly([pt(0, v, side, dz), pt(t1, v, side, dz), pt(t1, v - 0.045, side, dz), pt(0, v - 0.045, side, dz)]),
                       'shade' if hi == 'base' else 'deep')
                v -= 0.1
                i += 1

    def disc(side, t0, v0, r, a0=0.0, a1=2 * PI, n=20):
        """A circle of radius r (head units) laid on a plate round (t0, v0), so it foreshortens
        with the plate; a0..a1 gives a sector of it instead."""
        pts = [pt(t0 + r * math.cos(a) / L, v0 + r * math.sin(a), side) for a in np.linspace(a0, a1, n, endpoint=a1 - a0 < 2 * PI)]
        return G.poly(pts if a1 - a0 >= 2 * PI else [pt(t0, v0, side)] + pts)

    def plate_trefoil(p, side, t0, v0, R):
        """A radiation trefoil on an amber disc."""
        p.fill(disc(side, t0, v0, R * 1.25), f'{AMBER.name}.shade', mask=None)
        for i in range(3):
            p.fill(disc(side, t0, v0, R, math.radians(60 + 120 * i), math.radians(120 + 120 * i), 6), f'{DARK.name}.base', mask=None)
        p.fill(disc(side, t0, v0, R * 0.42), f'{AMBER.name}.shade', mask=None)
        p.fill(disc(side, t0, v0, R * 0.26), f'{DARK.name}.base', mask=None)

    split = o['split']
    plates = {}
    for side in ((1,) if east else (1, -1)):
        shaded = not east and side < 0
        tones = ('shade', 'deep') if shaded else ('base', 'shade')
        if split is None:
            p = plate(f'plate{side}', side, top, bot, 2, tones, inset=o['inset'])
        else:
            # a visor over a chin plate set back under its lip
            plate(f'chin{side}', side, lambda t: split - 0.1, bot, 1.9, (tones[1], 'deep'), t1=0.94, dz=-0.05, inset=False)
            p = plate(f'plate{side}', side, top, lambda t: split, 2, tones, inset=o['inset'])
        if p is None:
            continue
        plates[side] = p
        lo_edge = (lambda t: split) if split is not None else bot
        for t, f in o['bolts']:
            v = top(t) + (lo_edge(t) + lip - top(t)) * f
            K.bolt(p, *pt(t, v, side), 1.0 * k)
        if o['stencil'] and not shaded:
            x, y = pt(0.42, top(0.42) - 0.3, side)
            K.stencil(p, x - 2.5 * k, y, 5.0 * k, 3)
        if o['trefoil'] and side > 0:
            plate_trefoil(p, side, 0.5, (top(0.5) + lo_edge(0.5)) / 2 - 0.04, 0.12)
    # a raised keel along the joint
    kw, kh = o['keel'], o['keel_w']
    if kw:
        if east:
            ring = G.poly([pt(0, vt - 0.02, 1), pt(0, vt - 0.02, 1, kw), pt(0, vb + 0.02, 1, kw), pt(0, vb + 0.02, 1)])
        else:
            ring = G.poly([head_pt(c, 0.0, vt + 0.02, wr + kw), head_pt(c, -kh, vt - 0.06, wr + kw), head_pt(c, -kh, vb + 0.02, wr + kw),
                           head_pt(c, kh, vb + 0.02, wr + kw), head_pt(c, kh, vt - 0.06, wr + kw)])
        keel = vplate(K, c, 'keel', ring, 2.5, tone='base', bevel=0.9)
        if keel is not None and not east:
            keel.fill(G.poly([head_pt(c, 0.0, vt, wr + kw), head_pt(c, -kh, vt - 0.06, wr + kw), head_pt(c, -kh, vb + 0.02, wr + kw),
                              head_pt(c, 0.0, vb + 0.02, wr + kw)]), 'light')
    if o['cams']:
        _face_cams(K, c, CAMS[o['cams']], lambda u: wr - dw * min(abs(u), ue) / ue, plates.get(-1))


LENS_GLASS = '#5a5a5a'                # mid-grey, like the siegebreaker helmet's own lenses


def _hull(pts):
    """Convex hull of screen points, as a ring."""
    pts = sorted(set((round(float(x), 3), round(float(y), 3)) for x, y in pts))

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lower, upper = [], []
    for q in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], q) <= 0:
            lower.pop()
        lower.append(q)
    for q in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], q) <= 0:
            upper.pop()
        upper.append(q)
    return G.poly(lower[:-1] + upper[:-1])


def _face_cams(K, c, spec, surface, plate):
    """A camera cluster on the pawn's left side of the face (see CAMS), its lenses facing forward
    with the face: on tubes standing out through the plate, in a housing built out of it, or
    looking out of a port in it. ``surface(u)`` is the plate's depth at u. From the side the tubes
    or the housing stand out in front of the faceplate and the near plate hides the rest; the
    port's cameras stay hidden behind it."""
    k = c.k
    hf = c.form
    east = c.dir == 'east'
    wf = spec['front']

    def lens(p, u, v, r):
        x, y = head_pt(c, u, v, wf)
        rx, ry = r * hf.rx, r * hf.ry * 0.92
        p.fill(G.ellipse(x, y, rx, ry), f'{DARK.name}.deep', mask=None)
        p.fill(G.ellipse(x, y, rx * 0.74, ry * 0.74), LENS_GLASS, mask=None)
        p.fill(G.ellipse(x - rx * 0.24, y - ry * 0.26, rx * 0.2, ry * 0.18), f'{GREY.name}.base', mask=None)

    def ell(u, v, w, r, n=16):
        x, y = head_pt(c, u, v, w)
        return [(x + r * hf.rx * math.cos(a), y + r * hf.ry * 0.92 * math.sin(a)) for a in np.linspace(0, 2 * PI, n, endpoint=False)]
    if 'box' not in spec:
        # tubes: from the front a lens with its tube's top showing above it (we look down on it);
        # from the side the tube's end standing out in front of the faceplate
        for i, (u, v, r) in enumerate(spec['lenses']):
            if east:
                (xb, yb), (xf, yf) = head_pt(c, u, v, surface(u)), head_pt(c, u, v, wf)
                rr = r * hf.ry * 0.92
                tube = K.cylinder(f'tube{i}', (xb, yb), (xf, yf), rr, 1.9 + i * 0.01, FRAME)
                if tube is not None:
                    tube.fill(G.rect(xf - 1.0 * k, yf - rr, xf + 1, yf + rr), f'{DARK.name}.deep', mask=None)
                continue
            tube = K.flat(f'tube{i}', _hull(ell(u, v, surface(u), r * 1.1) + ell(u, v, wf, r * 1.1)), 2.6 + i * 0.01, FRAME)
            if tube is not None:
                lens(tube, u, v, r)
        return
    ui, uo, vt, vb = spec['box']
    if wf < surface(ui):
        # a port: the plate's opening, dark inside, the helmet's cameras behind it
        if east or plate is None:
            return
        opening = [head_pt(c, u, v, surface(u)) for u, v in ((ui, vt), (uo, vt), (uo, vb), (ui, vb))]
        port = K.part('port', G.rounded(G.poly(opening), 1.6 * k), 2.05, DARK, tone='base', shading=[])
        if port is None:
            return
        port.fill(G.poly([opening[0], opening[1], (opening[1][0], opening[1][1] + 2.0 * k), (opening[0][0], opening[0][1] + 2.0 * k)]),
                  'deep')
        for u, v, r in spec['lenses']:
            lens(port, u, v, r)
        return
    if east:
        # the housing's inner side, standing out in front of the faceplate
        side = [head_pt(c, ui, vt, surface(ui)), head_pt(c, ui, vt, wf), head_pt(c, ui, vb, wf), head_pt(c, ui, vb, surface(ui))]
        box = vplate(K, c, 'cams', G.chamfer(G.poly(side), [0.6 * k, 1.2 * k, 1.2 * k, 0.6 * k]), 1.9, bevel=0.9)
        if box is not None:
            box.fill(G.poly([side[3], side[2], (side[2][0], side[2][1] - 2.0 * k), (side[3][0], side[3][1] - 2.0 * k)]), 'shade')
            box.fill(G.rect(side[1][0] - 1.0 * k, side[1][1], side[1][0] + 1, side[2][1]), f'{DARK.name}.deep', mask=None)
        return
    # the housing's flat front with its top face above it (we look down on it)
    front = [head_pt(c, ui, vt, wf), head_pt(c, uo, vt, wf), head_pt(c, uo, vb, wf), head_pt(c, ui, vb, wf)]
    top_face = [head_pt(c, ui, vt, surface(ui)), head_pt(c, uo, vt, surface(uo)), front[1], front[0]]
    box = vplate(K, c, 'cams', G.chamfer(_hull(front + top_face), 1.0 * k), 2.6, bevel=0.9)
    if box is None:
        return
    box.fill(G.poly(top_face), 'light')
    box.fill(G.poly([front[3], front[2], (front[2][0], front[2][1] - 2.0 * k), (front[3][0], front[3][1] - 2.0 * k)]), 'shade')
    for u, v, r in spec['lenses']:
        lens(box, u, v, r)


@register('Plating', 'head', dirs=('south', 'east'), layer=0.2)
def helm_plating(K, c, fit):
    """Brow guard: a thick composite visor hood bolted across the upper face; on cataphract
    helmets, a great-helm faceplate over the whole front."""
    o = hopts(fit, 'Plating', style='brow', variant='wedge')
    if o['style'] == 'helm':
        h = dict(HELM, **HELM_VARIANTS[o['variant']])
        h.update({key: val for key, val in o.items() if key in HELM})
        _great_helm(K, c, fit, h)
    else:
        _brow_guard(K, c, fit, hopts(fit, 'Plating', phi=(0.3, 0.62), w=0.66))


def _uranium_brow(K, c, fit, o):
    """Uranium brow guard: a dark, heavy visor hood in a dyed trim frame with a trefoil."""
    k = c.k
    hf = c.form
    p0, p1 = o['phi']
    w = o['w']
    if c.dir == 'east':
        rf = F.helm_side(fit, 'east', 'r', p0, p1, 0.75, 1.3)
        pts = [(F.head_edge_x(c, fit, 'r', ph, rf) + 3.6 * k, F.head_y(c, ph)) for ph in np.linspace(p1, p0, 6)]
        inner = [(x - 11.0 * k, y) for x, y in pts]
        p = K.block('brow', G.chamfer(G.poly(pts + inner[::-1]), 1.4 * k), 2, URAN, bevel=0.0)
        if p is None:
            return
        p.fill(G.poly(pts + [(x - 2.0 * k, y) for x, y in pts[::-1]]), f'{SHELL.name}.base', mask='r')
        p.fill(G.poly([(x - 6.0 * k, y) for x, y in pts] + inner[::-1]), 'shade')
        yb = max(y for _, y in pts)
        p.fill(G.rect(min(x for x, _ in inner) - 1, yb - 2.4 * k, max(x for x, _ in pts) + 1, yb + 1), 'deep')
        K.bolt(p, inner[2][0] + 3.0 * k, inner[2][1], 1.0 * k)
        return
    r = F.helm_side(fit, 'south', 'l', p0, p1, 0.9, 1.25) + 0.11
    top = [(t, p1 - 0.06 * (1 - abs(t) / w)) for t in np.linspace(-w, w, 9)]
    bot = [(t, p0 - 0.1 * max(0.0, 1 - abs(t) / (w * 0.5))) for t in np.linspace(w, -w, 9)]
    ring = hf.ring(top + bot, r)
    if len(ring) < 3:
        return
    ring = G.simplify_ring(ring, 0.4 * k)
    p = K.block('brow', ring, 2, URAN, bevel=1.4)
    if p is None:
        return
    p.details.append(Line(G.poly(ring), 2.4 * k, f'{SHELL.name}.shade', closed=True, mask='r'))
    lip = hf.ring([(t, p0 - 0.1 * max(0.0, 1 - abs(t) / (w * 0.5)) + 0.08) for t in np.linspace(-w, w, 9)] + bot, r)
    if len(lip) >= 3:
        p.fill(G.simplify_ring(lip, 0.4 * k), 'deep')
    x, y = hf.P(0.0, (p0 + p1) / 2 + 0.03, r)
    p.fill(G.circle(x, y, 3.0 * k), f'{AMBER.name}.shade', mask=None)
    trefoil(K, p, x, y, 2.5 * k)
    for sd in (1, -1):
        xb, yb = hf.P(sd * (w - 0.14), (p0 + p1) / 2 + 0.02, r)
        K.bolt(p, xb, yb, 1.2 * k)
        p.line([hf.P(sd * 0.3, ph, r) for ph in np.linspace(p0 + 0.04, p1 - 0.05, 4)], 1.2 * k, 'deep')


@register('UraniumPlating', 'head', dirs=('south', 'east'), layer=0.2)
def helm_uranium(K, c, fit):
    """Uranium brow guard: a dark, heavy visor hood in a dyed trim frame with a trefoil; on
    cataphract helmets, the great-helm faceplate in laminated uranium plates."""
    o = hopts(fit, 'UraniumPlating', style='brow', variant='wedge', skin='laminate')
    if o['style'] == 'helm':
        h = dict(HELM, **HELM_VARIANTS[o['variant']], mat=URAN, trefoil=True)
        h.update({key: val for key, val in o.items() if key in HELM})
        _great_helm(K, c, fit, h)
    else:
        _uranium_brow(K, c, fit, hopts(fit, 'UraniumPlating', phi=(0.26, 0.68), w=0.78))


# ============================================================================= helmet: targeting uplink

@register('TargetingUplink', 'head', layer=0.8)
def targeting_uplink(K, c, fit):
    """Targeting uplink: a rangefinder housing high on the side of the helmet above the sensor
    array, its lens looking forward, an antenna rising from its back."""
    k = c.k
    o = hopts(fit, 'TargetingUplink', phi=(0.5, 0.86), mast=True)
    s = column_side(fit, 'TargetingUplink')
    ph0, ph1 = o['phi']
    pod = side_pod(K, c, fit, s, ph0, ph1, 3.0, 4.0, 2, 'housing', chamfer=1.8, east_x=(-6.0, 7.0))
    if pod is None:
        return
    p, sgn = pod['part'], pod['sgn']
    y0, y1 = pod['y0'], pod['y1']
    if o['mast']:
        xa = pod['x0'] + 2.5 * k if c.dir == 'east' else (pod['x_side'] + pod['x_in']) / 2 + sgn * 1.0 * k
        K.flat('mast', G.rect(xa - 0.8 * k, y0 - 13.0 * k, xa + 0.8 * k, y0 + 1.0 * k), 1.7, DARK)
    if c.dir == 'north':
        recess(p, G.rect(pod['x0'] + 2.0 * k, (y0 + y1) / 2 - 0.7 * k, pod['x1'] - 2.0 * k, (y0 + y1) / 2 + 0.7 * k))
        return
    if c.dir == 'east':
        ym = (y0 + y1) / 2
        recess(p, G.rect(pod['x1'] - 2.0 * k, ym - 1.6 * k, pod['x1'] + 1, ym + 1.6 * k))
        return
    xm = (pod['x_side'] + pod['x_in']) / 2
    ym = (y0 + y1) / 2
    p.fill(G.circle(xm, ym, 2.4 * k), f'{DARK.name}.base', mask=None)
    p.fill(G.circle(xm, ym, 1.4 * k), f'{GLASS.name}.base', mask=None)
    p.fill(G.circle(xm + 0.3 * k, ym + 0.3 * k, 0.7 * k), f'{RED.name}.deep', mask=None)


# ============================================================================= helmet: sensor array

@register('SensorArray', 'head', layer=0.7)
def sensor_array(K, c, fit):
    """Multispectral sensor array: a pod built out of the side of the helmet under the uplink,
    with three cameras stacked in its dark front window - thermal, visible and ultraviolet; from
    the side, the three lens barrels look forward."""
    k = c.k
    hf = c.form
    o = hopts(fit, 'SensorArray', phi=(-0.26, 0.4))
    s = column_side(fit, 'SensorArray')
    ph0, ph1 = o['phi']
    lenses = ((0.2, 1.6, AMBER), (0.5, 2.1, CYAN), (0.8, 1.6, VIOLET))
    if c.dir == 'east':
        if s < 0:
            return
        y0, y1 = F.head_y(c, ph1), F.head_y(c, ph0)
        x0, x1 = hf.cx - 3.0 * k, hf.cx + 8.0 * k
        pod = vplate(K, c, 'pod', G.chamfer(G.rect(x0, y0, x1, y1), [1.8 * k, 2.8 * k, 1.4 * k, 1.4 * k]), 2)
        if pod is None:
            return
        pod.fill(G.rect(x0 - 1, y1 - 2.4 * k, x1 + 1, y1 + 1), 'shade')
        for i, (t, r, mat) in enumerate(lenses):
            yy = y0 + (y1 - y0) * t
            K.flat(f'barrel{i}', G.rect(x1 - 2.0 * k, yy - r * k, x1 + 1.6 * k, yy + r * k), 3 + i * 0.01, GREY)
            K.flat(f'glass{i}', G.rect(x1 + 1.0 * k, yy - r * k * 0.8, x1 + 2.2 * k, yy + r * k * 0.8), 3.5 + i * 0.01, GLASS)
        return
    pod = side_pod(K, c, fit, s, ph0, ph1, 4.0, 4.5, 2, 'pod', chamfer=2.0)
    if pod is None:
        return
    p = pod['part']
    y0, y1 = pod['y0'], pod['y1']
    xa, xb = sorted((pod['x_side'], pod['x_in']))
    if c.dir == 'north':
        for t in (0.35, 0.6):
            yy = y0 + (y1 - y0) * t
            recess(p, G.rect(xa + 1.6 * k, yy - 0.6 * k, xb - 1.6 * k, yy + 0.6 * k))
        return
    wx0, wx1 = xa + 0.8 * k, xb - 0.8 * k
    wy0, wy1 = y0 + 2.4 * k, y1 - 3.2 * k
    p.fill(G.chamfer(G.rect(wx0, wy0, wx1, wy1), 1.0 * k), f'{DARK.name}.base', mask=None)
    xm = (wx0 + wx1) / 2
    for i, (t, r, mat) in enumerate(lenses):
        rr = min(r * k, (wx1 - wx0) / 2 - 0.2 * k)
        yy = wy0 + (wy1 - wy0) * t
        p.fill(G.circle(xm, yy, rr), f'{GREY.name}.base', mask=None)
        p.fill(G.circle(xm, yy, rr * 0.7), f'{GLASS.name}.base', mask=None)
        p.fill(G.circle(xm + rr * 0.15, yy + rr * 0.15, rr * 0.35), f'{mat.name}.deep', mask=None)


# ============================================================================= helmet: subpersona

@register('Subpersona', 'head', dirs=('south', 'north'), layer=0.5)
def helm_subpersona(K, c, fit):
    """Subcore housing low on the side of the helmet opposite the sensors, three subcore
    cartridges slotted into its front."""
    k = c.k
    o = hopts(fit, 'Subpersona', phi=(-0.4, 0.06))
    pod = side_pod(K, c, fit, column_side(fit, 'Subpersona'), o['phi'][0], o['phi'][1], 3.5, 3.5, 2, 'housing', chamfer=1.6)
    if pod is None:
        return
    p = pod['part']
    y0, y1 = pod['y0'], pod['y1']
    xa, xb = sorted((pod['x_side'], pod['x_in']))
    if c.dir == 'north':
        recess(p, G.rect(xa + 1.4 * k, (y0 + y1) / 2 - 0.6 * k, xb - 1.4 * k, (y0 + y1) / 2 + 0.6 * k))
        return
    n = 3
    h = (y1 - y0 - 5.0 * k) / n
    for i in range(n):
        yy = y0 + 2.0 * k + h * i
        recess(p, G.rect(xa + 1.0 * k, yy, xb - 1.0 * k, yy + h - 1.0 * k))


# ============================================================================= helmet: second mind

@register('SecondMind', 'head', dirs=('south', 'north'), layer=0.55)
def second_mind(K, c, fit):
    """Second mind: an armored persona core housing at the helmet's temple opposite the
    sensors, the core showing dimly through a round port in its front."""
    k = c.k
    o = hopts(fit, 'SecondMind', phi=(0.32, 0.86))
    ph0, ph1 = o['phi']
    pod = side_pod(K, c, fit, column_side(fit, 'SecondMind'), ph0, ph1, 4.5, 4.0, 2, 'housing', chamfer=2.4)
    if pod is None:
        return
    p = pod['part']
    y0, y1 = pod['y0'], pod['y1']
    xa, xb = sorted((pod['x_side'], pod['x_in']))
    if c.dir == 'north':
        for t in (0.35, 0.6):
            yy = y0 + (y1 - y0) * t
            recess(p, G.rect(xa + 1.4 * k, yy - 0.6 * k, xb - 1.4 * k, yy + 0.6 * k))
        return
    cx_, cy_ = (xa + xb) / 2, y0 + (y1 - y0) * 0.5
    R = min((xb - xa) / 2 - 0.8 * k, (y1 - y0) * 0.28)
    p.fill(G.circle(cx_, cy_, R + 0.8 * k), f'{GREY.name}.base', mask=None)
    p.fill(G.circle(cx_, cy_, R), f'{DARK.name}.deep', mask=None)
    p.fill(G.circle(cx_, cy_, R * 0.55), f'{CYAN.name}.deep', mask=None)
    p.fill(G.circle(cx_, cy_, R * 0.3), f'{CYAN.name}.base', mask=None)


# ============================================================================= helmet: neural link

@register('NeuralLink', 'head', dirs=('east', 'north'), layer=0.3)
def neural_link(K, c, fit):
    """Neural link (bionic synchronization): a spinal interface socket at the nape with three
    plugs seated in it; from the side, the socket edge-on."""
    k = c.k
    hf = c.form
    yb = F.helm_bottom_y(c, fit) + hopts(fit, 'NeuralLink', dy=0.0)['dy'] * k
    if c.dir == 'east':
        r_back = F.helm_side(fit, 'east', 'l', -0.9, -0.4, 0.6, 1.3)
        xo = F.head_edge_x(c, fit, 'l', -0.6, r_back) + 1.5 * k
        y0, y1 = yb - 12.0 * k, yb - 2.0 * k
        blk = vplate(K, c, 'socket', G.chamfer(G.rect(xo - 1.0 * k, y0, xo + 5.0 * k, y1), [1.2 * k, 1.6 * k, 1.2 * k, 1.2 * k]), 2)
        if blk is not None:
            blk.fill(G.rect(xo - 1.0 * k, y1 - 2.2 * k, xo + 5.0 * k, y1 + 1), 'shade')
            recess(blk, G.rect(xo - 1.0 * k, y0 + 3.0 * k, xo + 0.6 * k, y1 - 3.4 * k))
        return
    cx = hf.cx
    y0, y1 = yb - 13.0 * k, yb - 3.0 * k
    blk = vplate(K, c, 'socket', G.chamfer(G.rect(cx - 7.0 * k, y0, cx + 7.0 * k, y1), [2.0 * k, 2.0 * k, 1.6 * k, 1.6 * k]), 2)
    if blk is None:
        return
    blk.fill(G.rect(cx - 7.0 * k, y1 - 2.2 * k, cx + 7.0 * k, y1 + 1), 'deep')
    for dx in (-3.8, 0.0, 3.8):
        xx = cx + dx * k
        blk.fill(G.circle(xx, (y0 + y1) / 2 - 0.8 * k, 1.7 * k), f'{DARK.name}.base', mask=None)
        blk.fill(G.circle(xx, (y0 + y1) / 2 - 0.8 * k, 1.0 * k), f'{GREY.name}.base', mask=None)


# ============================================================================= helmet: stress dampener

@register('StressDampener', 'head', layer=0.4)
def stress_dampener(K, c, fit):
    """Neural stress dampener: a low emitter dome on the crown (or, on crested helmets, the back
    of the dome) with three short stub antennas round it, placed in 3D so each view shows them
    where they stand."""
    k = c.k
    hf = c.form
    o = hopts(fit, 'StressDampener', at='crown')
    if o['at'] == 'back':
        if c.dir == 'south':
            return
        yt = F.head_y(c, 0.62)
        x = hf.cx - (15.0 * k if c.dir == 'east' else 0.0)
    else:
        yt = F.helm_top_y(c, fit) + 3.0 * k
        x = hf.cx + (5.0 * k if c.dir == 'east' else 0.0)
    w, h = 7.0 * k, 3.6 * k
    rp = 5.0 * k
    prongs = []
    for az in (0.0, 120.0, 240.0):          # azimuth on the dome: 0 front, 90 the pawn's right
        a = math.radians(az)
        if c.dir == 'south':
            dx, dz = -math.sin(a), math.cos(a)
        elif c.dir == 'north':
            dx, dz = math.sin(a), -math.cos(a)
        else:
            dx, dz = math.cos(a), math.sin(a)
        prongs.append((dz, x + dx * rp, yt - 0.6 * k + dz * 1.2 * k))
    prongs.sort()
    dome = vplate(K, c, 'dome', G.poly([(x - w, yt + 1.6 * k)] + [(x + w * math.cos(t), yt + 1.6 * k - (h + 1.6 * k) * math.sin(t))
                                                                   for t in np.linspace(math.pi, 0, 16)] + [(x + w, yt + 1.6 * k)]), 2)
    if dome is not None:
        dome.fill(G.rect(x - w, yt, x + w, yt + 1.6 * k + 1), 'deep' if c.dir == 'north' else 'shade')
        if c.dir != 'north':
            recess(dome, G.ellipse(x, yt - 1.4 * k, w * 0.28, h * 0.32))
    for i, (dz, xx, yy) in enumerate(prongs):
        z = 2.05 + (0.2 if dz > 0 else -0.3) + i * 0.01
        K.flat(f'stub{i}', G.rect(xx - 0.7 * k, yy - h - 3.4 * k, xx + 0.7 * k, yy - 1.0 * k), z, DARK)


# ============================================================================= helmet: regenerators

@register('Regenerators', 'head', dirs=('east', 'north'), layer=0.6)
def helm_regenerators(K, c, fit):
    """Two regenerator canisters on the back of the helmet, angled up and apart; from the side
    the near canister hides the far one."""
    k = c.k
    hf = c.form
    ph = hopts(fit, 'Regenerators', phi=-0.18)['phi']
    # on helmets open at the back the nape is high: keep clear of the neural link's socket
    ph = max(ph, _phi_at(c, F.helm_bottom_y(c, fit) - 16.0 * k))
    if c.dir == 'east':
        r_back = F.helm_side(fit, 'east', 'l', ph - 0.25, ph + 0.35, 0.8, 1.25)
        xb = F.head_edge_x(c, fit, 'l', ph + 0.13, r_back) + 3.0 * k
        yb = F.head_y(c, ph + 0.13)
        ang = math.radians(28)
        L = 13.0 * k
        simple_canister(K, c, 'can', (xb, yb), (xb - L * math.sin(ang), yb - L * math.cos(ang)), 2.6 * k, 2)
        return
    yb = F.head_y(c, ph)
    for s in (-1, 1):
        simple_canister(K, c, f'can{s}', (hf.cx + s * 5.0 * k, yb), (hf.cx + s * 9.0 * k, yb - 14.0 * k), 2.6 * k, 2)


