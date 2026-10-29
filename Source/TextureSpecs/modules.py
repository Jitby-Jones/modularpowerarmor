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

Rotary joints are drawn the way their axis faces each view (Kit.joint): the exoframe's
shoulder, elbow, hip and knee pivots, the elbow servos and the piston pins turn about the
pawn's left-right axis, so they are round only from the side and barrels from the front and
back.
"""
import math

import numpy as np

import mpa_fit as F
from mpa_kit import (AMBER, CYAN, DARK, FRAME, GEL, GLASS, HOSE, IRON, RED, SHELL, STEEL, VIOLET, Kit, _mat, perp, quad,
                     render, render_mask, setup, unit)
from rwtex import geom as G
from rwtex.archetypes.apparel import armor, helmet
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

# Per-helmet adjustments, {fit: {module: {option: value}}}. The targeting uplink and the sensor
# array share one side of the helmet ('side', the pawn's right by default), the second mind and
# the subpersona the other.
HELMS = {
    # the helmet's own antenna (recon, royal trooper), fins or side plates do the whip's job;
    # tall crests push the crown dampener onto the back of the dome
    'Recon': {'TargetingUplink': {'mast': False}},
    'PrestigeMarine': {'TargetingUplink': {'mast': False}, 'StressDampener': {'at': 'back'}},
    'PrestigeRecon': {'TargetingUplink': {'mast': False}},
    'PrestigeCataphract': {'StressDampener': {'at': 'back'}},
    'Siegebreaker': {'TargetingUplink': {'mast': False}},
    'RoyalSiegebreaker': {'TargetingUplink': {'mast': False}},
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

def strut(K, name, a, b, w, z, mat=FRAME, holes=True):
    """Box-section strut from a to b: gunmetal bar with a lit top edge, a dark lower edge and
    lightening holes."""
    k = K.k
    a, b = np.asarray(a, float), np.asarray(b, float)
    p = K.block(name, quad(a, b, w), z, mat, bevel=0.0)
    if p is None:
        return p
    ax = unit(b - a)
    n = perp(ax)
    if n[1] > 0:
        n = -n                       # n points up/left (toward the light)
    L = float(np.hypot(*(b - a)))
    p.fill(G.poly([a + n * w, b + n * w, b + n * w * 0.45, a + n * w * 0.45]), 'light')
    p.fill(G.poly([a - n * w, b - n * w, b - n * w * 0.5, a - n * w * 0.5]), 'shade')
    if holes and L > 10.0 * k:
        m = int(L / (5.0 * k))
        for i in range(1, m):
            q = a + ax * L * i / m
            p.fill(G.rounded(G.poly([q - ax * 1.2 * k + n * w * 0.3, q + ax * 1.2 * k + n * w * 0.3,
                                     q + ax * 1.2 * k - n * w * 0.3, q - ax * 1.2 * k - n * w * 0.3]), 0.5 * k),
                   f'{DARK.name}.base', mask=None)
    return p


def actuator(K, c, name, x, y, R, z, tone='base', lamp=True):
    """Shell actuator housing round a joint drive that turns about the pawn's left-right axis:
    the drive's hub shows from the side, its barrel through the housing from the front and back."""
    k = c.k
    p = K.block(name, G.chamfer(G.rect(x - R, y - R, x + R, y + R), R * 0.45), z, SHELL, bevel=1.2, tone=tone)
    if p is None:
        return p
    p.fill(G.rect(x - R, y + R * 0.5, x + R, y + R), 'shade' if tone == 'base' else 'deep')
    if c.dir == 'east':
        K.hinge(name + '_hub', x, y - R * 0.05, R * 0.58, z + 0.05, FRAME)
    else:
        K.knuckle(name + '_hub', x, y + R * 0.1, R * 1.05, R * 0.42, z + 0.05, FRAME)
    if lamp:
        K.lamp(p, x + R * 0.62, y - R * 0.62, 1.1 * k, 1.0 * k)
    return p


def spine(K, c, lay, y0, y1, w=4.6):
    """Segmented spine column down the middle of the back (north)."""
    k = c.k
    cx = F.body_ext(c, F.vy(c, (y0 + y1) / 2))[0]
    hw = w * k * lay['sq']
    K.block('spine', G.chamfer(G.rect(cx - hw * 0.55, y0, cx + hw * 0.55, y1), 1.0 * k), 1.6, IRON, bevel=0.6)
    n = max(4, int((y1 - y0) / (5.0 * k)))
    for i in range(n):
        yy = y0 + (y1 - y0) * (i + 0.5) / n
        v = K.block(f'vert{i}', G.chamfer(G.rect(cx - hw, yy - 1.7 * k, cx + hw, yy + 1.7 * k), 1.0 * k), 1.7 + i * 0.001, FRAME,
                    bevel=0.7)
        if v is not None:
            K.bolt(v, cx - hw * 0.55, yy, 0.6 * k)
            K.bolt(v, cx + hw * 0.55, yy, 0.6 * k)


def spine_east(K, c, xs, y0, y1):
    """The spine seen from the side: vertebrae standing out from the back."""
    k = c.k
    x0, x1 = xs
    K.block('spine', G.chamfer(G.poly([(x0 - 1.4 * k, y0), (x0 + 1.4 * k, y0), (x1 + 1.4 * k, y1), (x1 - 1.4 * k, y1)]), 0.8 * k), 1.6,
            IRON, bevel=0.6)
    n = max(4, int((y1 - y0) / (5.0 * k)))
    for i in range(n):
        t = (i + 0.5) / n
        yy = y0 + (y1 - y0) * t
        xx = x0 + (x1 - x0) * t
        K.block(f'vert{i}', G.chamfer(G.rect(xx - 3.2 * k, yy - 1.6 * k, xx + 1.8 * k, yy + 1.6 * k), 0.9 * k), 1.7 + i * 0.001, FRAME,
                bevel=0.7)


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


def canister(K, name, base, tip, hw, z, mat=SHELL, fluid=GEL, window=True, tone='base'):
    """Regenerator canister from its mount (base) to its cap (tip): cylinder body with a glass
    window showing the fluid, a collar at the mount and a cap."""
    k = K.k
    base, tip = np.asarray(base, float), np.asarray(tip, float)
    ax = unit(tip - base)
    nrm = perp(ax)
    L = float(np.hypot(*(tip - base)))
    body = K.cylinder(name, base + ax * 1.5 * k, tip - ax * 1.0 * k, hw, z, mat, tone=tone)
    if body is not None and window:
        a, b = base + ax * L * 0.3, tip - ax * L * 0.25
        body.fill(G.poly([a + nrm * hw * 0.42, b + nrm * hw * 0.42, b - nrm * hw * 0.42, a - nrm * hw * 0.42]), f'{DARK.name}.deep',
                  mask=None)
        a2, b2 = a + ax * 0.8 * k, b - ax * 0.8 * k
        body.fill(G.poly([a2 + nrm * hw * 0.26, b2 + nrm * hw * 0.26, b2 - nrm * hw * 0.26, a2 - nrm * hw * 0.26]), f'{fluid.name}.base',
                  mask=None)
        body.fill(G.poly([a2 + nrm * hw * 0.26, b2 + nrm * hw * 0.26, b2 + nrm * hw * 0.04, a2 + nrm * hw * 0.04]), f'{fluid.name}.light',
                  mask=None)
    K.cylinder(name + '_collar', base - ax * 0.5 * k, base + ax * 2.2 * k, hw * 1.15, z + 0.01, FRAME)
    K.cylinder(name + '_cap', tip - ax * 2.0 * k, tip + ax * 0.6 * k, hw * 0.9, z + 0.02, FRAME)
    return body


def damper(K, name, top, bot, r, z):
    """Telescopic shock damper: gunmetal outer tube over a bright inner rod, end caps."""
    k = K.k
    top, bot = np.asarray(top, float), np.asarray(bot, float)
    ax = unit(bot - top)
    L = float(np.hypot(*(bot - top)))
    K.cylinder(name + '_rod', top + ax * L * 0.45, bot, r * 0.55, z, STEEL)
    K.cylinder(name + '_tube', top, top + ax * L * 0.58, r, z + 0.01, FRAME)
    K.cylinder(name + '_cap0', top - ax * 1.0 * k, top + ax * 1.2 * k, r * 1.25, z + 0.02, IRON)
    K.cylinder(name + '_cap1', bot - ax * 1.2 * k, bot + ax * 0.6 * k, r * 1.1, z + 0.02, IRON)


def lattice(K, p, x0, y0, x1, y1, cell=None):
    """A recessed dark window with a gunmetal diamond lattice in it."""
    k = K.k
    cell = cell or 3.2 * k
    p.fill(G.chamfer(G.rect(x0, y0, x1, y1), 0.8 * k), f'{DARK.name}.deep', mask=None)
    w = x1 - x0
    n = max(2, int(round((y1 - y0) / cell)))
    for i in range(-n, 2 * n):
        ya = y0 + i * cell
        p.line([(x0, ya), (x1, ya + w)], 0.9 * k, f'{FRAME.name}.base', mask=None)
        p.line([(x1, ya), (x0, ya + w)], 0.9 * k, f'{FRAME.name}.base', mask=None)
    p.details.append(Line(G.chamfer(G.rect(x0, y0, x1, y1), 0.8 * k), 1.2 * k, f'{FRAME.name}.light', closed=True, mask=None))


# ============================================================================= body: exoframe

@register('Exoframe', 'body', layer=0.08)
def exoframe(K, c, fit):
    """Load-bearing exoskeleton over the whole suit. The frame runs down the outside of the
    limbs - shoulder and hip actuators on the outer side of those joints, struts down the
    outside of the arms and legs, elbow and knee joints - with a segmented spine on the back, a
    yoke from it to the shoulders and a hip frame wrapping round the back to the hip actuators.
    Seen from the front and back, the outside of the limbs is the silhouette's edge: the struts
    show edge-on there and the joints, whose axles point out of the body's side, as barrels
    sticking out sideways; the spine, yoke and hip frame only show from behind and the side."""
    k = c.k
    f = c.form
    lay = F.layout(c, fit)
    y_sh = f.top + 17.0 * k
    y_el = lay['y_elbow']
    y_hip = lay['y_belt'] + 1.5 * k
    y_bot = f.bot - 2.5 * k
    y_knee = y_hip + (y_bot - y_hip) * 0.6
    if c.dir == 'east':
        _exoframe_east(K, c, fit, lay, y_sh, y_el, y_hip, y_knee, y_bot)
        return
    back = c.dir == 'north'
    hi = edge_hi(fit)
    under = opts(fit, 'Exoframe', under={})['under']
    act = {}
    for side, s in front_sides(c):
        sgn = -1 if side == 'l' else 1

        def ex(y, lift):
            return X(c, fit, y, side, lift=lift, hi=hi)
        xsh = ex(y_sh, 1.4)
        xel = ex(y_el, 1.4)
        xwr = ex(y_hip - 6.0 * k, 1.2)
        xhp = ex(y_hip, 1.2)
        xkn = ex(y_knee, 0.8)
        xft = ex(y_bot - 1.0 * k, 0.4)
        act[side] = (xsh, xhp)
        # under a wing, launcher or big pauldron the shoulder is hidden: the strut comes out below
        y_top = y_sh
        if s in under:
            y_top = min(f.y(under[s]), y_el - 3.0 * k)
        x_top = ex(y_top, 1.4)
        if y_top < y_el - 3.0 * k:
            strut(K, f'uarm{side}', (x_top, y_top), (xel, y_el), 1.25 * k, 2, holes=False)
        strut(K, f'farm{side}', (xel, y_el), (xwr, y_hip - 6.0 * k), 1.15 * k, 2, holes=False)
        strut(K, f'thigh{side}', (xhp, y_hip), (xkn, y_knee), 1.35 * k, 2, holes=False)
        strut(K, f'shin{side}', (xkn, y_knee), (xft, y_bot), 1.25 * k, 2, holes=False)
        K.block(f'cuff{side}', quad((xwr, y_hip - 9.0 * k), (xwr, y_hip - 5.0 * k), 2.2 * k), 2.1, FRAME, bevel=0.6)
        for nm, (x, y, R) in {'elbow': (xel, y_el, 2.5 * k), 'knee': (xkn, y_knee, 2.6 * k)}.items():
            K.knuckle(f'{nm}{side}', x + sgn * R * 0.35, y, R * 0.95, R * 0.8, 4, FRAME)
        K.block(f'foot{side}', G.chamfer(G.rect(xft - 2.4 * k, y_bot - 1.4 * k, xft + 2.4 * k, y_bot + 1.4 * k), 0.7 * k), 4, FRAME, bevel=0.6)
        if s in under:
            K.block(f'emerge{side}', quad((x_top, y_top - 0.5 * k), (x_top, y_top + 3.0 * k), 2.0 * k), 2.05, FRAME, bevel=0.5)
        else:
            _side_actuator(K, c, f'shoulder{side}', xsh, y_sh, sgn, 4.2 * k, 5, back)
        _side_actuator(K, c, f'hip{side}', xhp, y_hip, sgn, 4.2 * k, 5, back)
    if not back:
        return
    cx = F.body_ext(c, F.vy(c, y_sh))[0]
    spine(K, c, lay, y_sh - 10.0 * k, y_hip - 1.0 * k)
    for side, s in front_sides(c):
        if s not in under:
            strut(K, f'yoke{side}', (cx, y_sh - 3.0 * k), (act[side][0], y_sh), 1.7 * k, 1.55, holes=False)
    _hip_frame(K, c, fit, y_hip, hi)


def _side_actuator(K, c, name, x, y, sgn, R, z, back):
    """Joint drive on the outer side of a shoulder or hip, seen from the front or back: the
    housing's narrow front face on the silhouette's edge and its drive barrel sticking out."""
    k = c.k
    x0, x1 = sorted((x - sgn * R * 0.55, x + sgn * R * 0.6))
    p = K.block(name, G.chamfer(G.rect(x0, y - R, x1, y + R), R * 0.3), z, SHELL, bevel=1.1, tone='shade' if back else 'base')
    if p is not None:
        p.fill(G.rect(x0, y + R * 0.55, x1, y + R), 'deep' if back else 'shade')
        K.seam(p, [(x0 + 0.6 * k, y - R * 0.35), (x1 - 0.6 * k, y - R * 0.35)])
    K.knuckle(name + '_drive', x + sgn * R * 0.75, y + R * 0.05, R * 0.55, R * 0.55, z + 0.05, FRAME)


def _hip_frame(K, c, fit, y_hip, hi):
    """The hip frame across the back between the hip actuators (north)."""
    k = c.k
    xl = X(c, fit, y_hip, 'l', lift=1.2, hi=hi)
    xr = X(c, fit, y_hip, 'r', lift=1.2, hi=hi)
    wb = K.block('hipframe', G.chamfer(G.rect(xl, y_hip - 2.2 * k, xr, y_hip + 2.2 * k), 0.8 * k), 1.5, FRAME, bevel=0.0)
    if wb is not None:
        wb.fill(G.rect(xl, y_hip - 2.2 * k, xr, y_hip - 1.0 * k), 'light')
        wb.fill(G.rect(xl, y_hip + 1.0 * k, xr, y_hip + 2.2 * k), 'shade')
        for t in np.linspace(0.12, 0.88, 6):
            K.bolt(wb, xl + (xr - xl) * t, y_hip, 0.75 * k)


def _exoframe_east(K, c, fit, lay, y_sh, y_el, y_hip, y_knee, y_bot):
    """From the side the frame faces the viewer: the struts show their full width, the joints
    their hubs, the spine stands out from the back and the hip frame wraps round to the hip."""
    k = c.k
    f = c.form
    sq = lay['sq']
    xb_sh = X(c, fit, y_sh - 6.0 * k, 'l', lift=0.5) + 2.6 * k
    xb_hp = X(c, fit, y_hip, 'l', lift=0.5) + 2.6 * k
    spine_east(K, c, (xb_sh, xb_hp), y_sh - 10.0 * k, y_hip)
    cx_el = f.d(F.vy(c, y_el))[0]
    xsh = f.d(F.vy(c, y_sh))[0] - 2.0 * k
    xel = cx_el + 1.0 * k
    xwr = cx_el + 6.0 * k
    xhp = f.d(F.vy(c, y_hip))[0] - 2.0 * k
    xkn = xhp + 3.0 * k
    xft = xhp
    strut(K, 'yoke', (xb_sh, y_sh - 6.0 * k), (xsh, y_sh), 1.8 * k, 1.55, holes=False)
    strut(K, 'uarm', (xsh, y_sh), (xel, y_el), 2.0 * k, 2)
    strut(K, 'farm', (xel, y_el), (xwr, y_hip - 6.0 * k), 1.8 * k, 2, holes=False)
    strut(K, 'thigh', (xhp, y_hip), (xkn, y_knee), 2.2 * k, 2)
    strut(K, 'shin', (xkn, y_knee), (xft, y_bot), 2.0 * k, 2, holes=False)
    strut(K, 'hipframe', (xb_hp, y_hip), (xhp, y_hip), 2.2 * k, 1.5, holes=False)
    K.piston('ram_arm', (xsh - 3.4 * k, y_sh + 4.0 * k), (xel - 3.2 * k, y_el - 3.0 * k), 1.4 * k, 0.7 * k, 3, eyes=False)
    K.piston('ram_leg', (xhp + 4.2 * k, y_hip + 5.0 * k), (xkn + 3.8 * k, y_knee - 2.5 * k), 1.6 * k, 0.8 * k, 3, eyes=False)
    K.hinge('elbow', xel, y_el, 3.0 * k, 4, FRAME)
    K.hinge('knee', xkn, y_knee, 3.2 * k, 4, FRAME)
    K.block('foot', G.chamfer(G.rect(xft - 3.5 * k, y_bot - 1.5 * k, xft + 4.0 * k, y_bot + 1.5 * k), 0.8 * k), 4, FRAME, bevel=0.6)
    if 1 not in opts(fit, 'Exoframe', under={})['under']:
        actuator(K, c, 'shoulder', xsh, y_sh, 5.0 * k * sq ** 0.5, 5, lamp=False)
    actuator(K, c, 'hip', xhp, y_hip, 5.2 * k * sq ** 0.5, 5, lamp=False)


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


# ============================================================================= body: biogel servos

def _gel_sleeve(K, c, name, a, b, hw, z):
    """Translucent biogel muscle sleeve: a green glass tube with dark fibre bands and clamp rings."""
    k = c.k
    p = K.cylinder(name, a, b, hw, z, GEL)
    if p is None:
        return
    a, b = np.asarray(a, float), np.asarray(b, float)
    ax = unit(b - a)
    L = float(np.hypot(*(b - a)))
    n = perp(ax)
    for t in np.linspace(0.2, 0.8, 4):
        q = a + ax * L * t
        p.line([q + n * hw * 0.9, q - n * hw * 0.9], 0.6 * k, f'{GEL.name}.deep')
    for t in (0.0, 1.0):
        q = a + ax * L * t
        K.cylinder(name + f'_clamp{int(t)}', q - ax * 1.2 * k, q + ax * 1.2 * k, hw * 1.25, z + 0.01, FRAME)

def _servo_drum(K, c, name, x, y, R, z, sgn=1, back=False):
    """Elbow servo motor on the outside of the elbow. It turns about the elbow's (left-right)
    axis, so from the side it is a finned drum with its drive hub facing the viewer, and from
    the front and back a finned barrel sticking out of the elbow's side (``sgn`` outward)."""
    k = c.k
    if c.dir != 'east':
        a, b = x - sgn * R * 0.4, x + sgn * R * 1.3
        p = K.cylinder(name, (min(a, b), y), (max(a, b), y), R * 0.78, z, SHELL, tone='shade' if back else 'base')
        if p is None:
            return
        for i in range(4):
            xx = min(a, b) + (abs(b - a)) * (0.2 + 0.2 * i)
            p.line([(xx, y - R * 0.78), (xx, y + R * 0.78)], 0.9 * k, f'{DARK.name}.base', mask=None)
        xe = b
        K.cylinder(name + '_cap', (xe - sgn * 0.8 * k, y), (xe + sgn * 1.2 * k, y), R * 0.55, z + 0.01, FRAME)
        return
    p = K.block(name, G.chamfer(G.rect(x - R, y - R, x + R, y + R), R * 0.38), z, SHELL, bevel=1.1)
    if p is None:
        return
    for i in range(4):
        a = math.radians(45 + 90 * i)
        p.line([(x + math.cos(a) * R * 0.78, y + math.sin(a) * R * 0.78), (x + math.cos(a) * R * 1.1, y + math.sin(a) * R * 1.1)], 1.0 * k,
               f'{DARK.name}.base', mask=None)
    K.hinge(name + '_hub', x, y, R * 0.62, z + 0.1, FRAME)
    p.fill(G.rect(x - R, y + R * 0.55, x + R, y + R), 'shade')


@register('BiogelServos', 'body', layer=0.28)
def biogel_servos(K, c, fit):
    """Servo motors on the outside of both elbows driving biogel muscle sleeves: one down the
    front of the upper arm and forearm (seen from the front and the side), one down the back of
    the upper arm (seen from behind and the side)."""
    k = c.k
    lay = F.layout(c, fit)
    y = lay['y_elbow']
    if c.dir == 'east':
        x = c.form.d(F.vy(c, y))[0] + 1.0 * k
        _gel_sleeve(K, c, 'sleeve_front', (x + 2.0 * k, y - 21.0 * k), (x + 3.0 * k, y - 4.0 * k), 2.0 * k, 1)
        _gel_sleeve(K, c, 'sleeve_back', (x - 4.0 * k, y - 20.0 * k), (x - 3.5 * k, y - 4.0 * k), 1.8 * k, 0.9)
        _gel_sleeve(K, c, 'sleeve_fore', (x + 3.0 * k, y + 4.0 * k), (x + 6.0 * k, y + 16.0 * k), 1.9 * k, 1)
        _servo_drum(K, c, 'servo', x, y, 4.8 * k, 2)
        return
    back = c.dir == 'north'
    for side, s in front_sides(c):
        sgn = -1 if side == 'l' else 1
        xe = X(c, fit, y, side, lift=0.4, hi=edge_hi(fit))
        xs = xe - sgn * 4.2 * k                     # on the arm's front (or back) face, near its outer edge
        _gel_sleeve(K, c, f'sleeve_up{side}', (xs + sgn * 0.6 * k, y - 21.0 * k), (xs, y - 4.0 * k), 2.0 * k, 1)
        if not back:
            _gel_sleeve(K, c, f'sleeve_lo{side}', (xs, y + 4.0 * k), (xs - sgn * 1.0 * k, y + 15.0 * k), 1.8 * k, 1)
        _servo_drum(K, c, f'servo{side}', xe - sgn * 1.0 * k, y, 4.6 * k, 2, sgn, back)


# ============================================================================= body: regenerators

@register('Regenerators', 'body', dirs=('east', 'north'), layer=0.6)
def regenerators(K, c, fit):
    """Neuromemetic regenerator canisters: two long tanks out of the upper back either side of
    the spine, angled down and outwards, clamped into a cradle across the back and plumbed into
    the armor, the regenerator fluid showing through their windows. From the side the near tank
    hides the far one."""
    k = c.k
    f = c.form
    lay = F.layout(c, fit)
    sq = lay['sq']
    y_top = f.top + 0.16 * f.H
    if c.dir == 'east':
        xb = X(c, fit, y_top + 8.0 * k, 'l', lift=0.0) + 5.0 * k
        yb = y_top + 6.0 * k
        cr = K.block('cradle', G.chamfer(G.rect(xb - 1.0 * k, yb - 5.0 * k, xb + 8.0 * k, yb + 9.0 * k), 1.6 * k), 1.5, FRAME, bevel=0.0)
        if cr is not None:
            cr.fill(G.rect(xb - 1.0 * k, yb - 5.0 * k, xb + 8.0 * k, yb - 3.6 * k), 'light')
            K.bolts(cr, [(xb + 5.5 * k, yb - 1.5 * k), (xb + 5.5 * k, yb + 6.0 * k)], 0.8 * k)
        L = 25.0 * k * sq ** 0.5
        ang = math.radians(28)
        b = np.array([xb + 1.0 * k, yb + 1.0 * k])
        canister(K, 'can', b, b + np.array([-math.sin(ang), math.cos(ang)]) * L, 3.4 * k, 2)
        K.hose('feed', [(xb + 6.0 * k, yb + 8.0 * k), (xb + 9.0 * k, yb + 13.0 * k), (xb + 9.5 * k, yb + 19.0 * k)], 2.4 * k, 1.6)
        return
    cx, a_ = F.body_ext(c, F.vy(c, y_top + 10.0 * k))
    hw = 3.6 * k * sq ** 0.4
    span = min(a_ * 0.42, 15.0 * k * sq)
    cr = K.block('cradle', G.chamfer(G.rect(cx - span - 5.0 * k, y_top - 1.0 * k, cx + span + 5.0 * k, y_top + 6.0 * k), 1.6 * k), 1.5,
                 FRAME, bevel=0.0)
    if cr is not None:
        cr.fill(G.rect(cx - span - 5.0 * k, y_top - 1.0 * k, cx + span + 5.0 * k, y_top + 0.6 * k), 'light')
        cr.fill(G.rect(cx - span - 5.0 * k, y_top + 4.4 * k, cx + span + 5.0 * k, y_top + 6.0 * k), 'shade')
    L = 26.0 * k * sq ** 0.5
    ang = math.radians(16)
    for s in (-1, 1):
        b = np.array([cx + s * span, y_top + 2.0 * k])
        canister(K, f'can{s}', b, b + np.array([s * math.sin(ang), math.cos(ang)]) * L, hw, 2, tone='shade')
        K.hose(f'feed{s}', [b + np.array([-s * 2.0 * k, 3.0 * k]), b + np.array([-s * 5.0 * k, 8.0 * k]), b + np.array([-s * 6.0 * k, 14.0 * k])],
               2.2 * k, 1.6)


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
    """Second heart: an armored life-support drum in the middle of the upper back. From behind,
    its porthole shows the heart, dark red in fluid, with three high subcore cartridges in the
    rim and ribbed arterial hoses into the armor; from the side, the drum stands out from the
    back with its hoses looping down into it."""
    k = c.k
    y0, y1, lay = back_rows(c, fit)
    sq = lay['sq']
    R = 8.0 * k * sq ** 0.5
    if c.dir == 'east':
        cy = y0 + (y1 - y0) * 0.5 + 1.0 * k
        xb = X(c, fit, cy, 'l', lift=0.0) + 2.0 * k
        d = 6.0 * k
        K.hose('artery', [(xb - d + 1.5 * k, cy + R * 0.7), (xb - d - 1.0 * k, cy + R * 1.4), (xb - 1.0 * k, cy + R * 2.2)], 2.8 * k, 1.4)
        drum = K.block('drum', G.chamfer(G.rect(xb - d, cy - R * 1.25, xb + 1.0 * k, cy + R * 1.05), [1.5 * k, 1.5 * k, 2.5 * k, 2.5 * k]),
                       2, SHELL, bevel=1.1, tone='shade')
        if drum is not None:
            drum.fill(G.rect(xb - d, cy + R * 0.75, xb + 1.0 * k, cy + R * 1.05), 'deep')
            # the porthole's rim, edge-on, on the drum's back face
            drum.fill(G.rect(xb - d - 0.1 * k, cy - R * 0.7, xb - d + 1.4 * k, cy + R * 0.7), f'{FRAME.name}.base', mask=None)
            K.notch(drum, xb - d + 1.5 * k, cy - R * 1.2, xb - 1.0 * k, cy - R * 0.85)
        return
    cx = F.body_ext(c, F.vy(c, (y0 + y1) / 2))[0]
    cy = y0 + (y1 - y0) * 0.5 + 1.0 * k
    for s in (-1, 1):
        K.hose(f'artery{s}', [(cx + s * R * 0.7, cy + R * 0.6), (cx + s * R * 1.45, cy + R * 1.1), (cx + s * R * 1.6, cy + R * 2.2)], 2.8 * k,
               1.4, mat=HOSE)
    drum = K.block('drum', G.chamfer(G.rect(cx - R, cy - R * 1.25, cx + R, cy + R * 1.05), R * 0.42), 2, SHELL, bevel=1.3, tone='shade')
    if drum is None:
        return
    drum.fill(G.rect(cx - R, cy + R * 0.75, cx + R, cy + R * 1.05), 'deep')
    # porthole
    drum.fill(G.circle(cx, cy, R * 0.7), f'{FRAME.name}.base', mask=None)
    drum.fill(G.circle(cx, cy, R * 0.56), f'{DARK.name}.deep', mask=None)
    drum.fill(G.circle(cx, cy, R * 0.5), '#2e1214', mask=None)
    _heart(drum, cx, cy + R * 0.02, R * 0.36)
    drum.fill(G.ellipse(cx - R * 0.24, cy - R * 0.28, R * 0.12, R * 0.07), f'{GLASS.name}.light', mask=None)
    for i in range(6):
        a = math.radians(i * 60 + 30)
        K.bolt(drum, cx + math.cos(a) * R * 0.63, cy + math.sin(a) * R * 0.63, 0.7 * k)
    # three subcore cartridges in the top rim
    for i, dx in enumerate((-0.55, 0.0, 0.55)):
        xx = cx + dx * R
        K.notch(drum, xx - 1.6 * k, cy - R * 1.2, xx + 1.6 * k, cy - R * 0.82)
        drum.fill(G.rect(xx - 1.0 * k, cy - R * 1.15, xx + 1.0 * k, cy - R * 0.9), f'{IRON.name}.light', mask=None)
    K.lamp(drum, cx + R * 0.55, cy - R * 0.86, 1.0 * k, 0.8 * k, AMBER)


# ============================================================================= body: subpersona

@register('Subpersona', 'body', dirs=('south', 'east'), layer=0.8)
def subpersona(K, c, fit):
    """Auxiliary subpersona pack across the belt: an armored processor case with three subcore
    cartridges racked in its face (pull tabs, amber lamps), a heat-sink grille on top and data
    cables up into the chest."""
    k = c.k
    lay = F.layout(c, fit)
    sq = lay['sq']
    y0 = lay['y_chest'] - 3.0 * k
    y1 = lay['y_belt'] + 10.0 * k * lay['sv'] ** 0.5
    if c.dir == 'east':
        xr = X(c, fit, (y0 + y1) / 2, 'r', lift=4.0)
        d = 9.0 * k
        p = K.block('case', G.chamfer(G.rect(xr - d, y0, xr, y1), [1.5 * k, 3.0 * k, 2.4 * k, 1.5 * k]), 7, SHELL, bevel=1.2)
        if p is None:
            return
        p.fill(G.rect(xr - d, y0 - 1, xr + 1, y0 + 3.2 * k), 'light')
        for i in range(4):
            xx = xr - d + 1.6 * k + i * 1.8 * k
            p.line([(xx, y0 + 0.6 * k), (xx, y0 + 2.8 * k)], 0.7 * k, 'deep')
        p.fill(G.rect(xr - d, y1 - 2.8 * k, xr + 1, y1 + 1), 'shade')
        # the cartridge ends at the case's front, seen edge-on
        for i in range(3):
            yy = y0 + 5.0 * k + i * (y1 - y0 - 9.0 * k) / 2
            K.notch(p, xr - 2.4 * k, yy - 1.4 * k, xr - 0.4 * k, yy + 1.4 * k)
            p.fill(G.rect(xr - 1.2 * k, yy - 1.0 * k, xr + 1.2 * k, yy + 1.0 * k), f'{STEEL.name}.base', mask=None)
        K.hose('data', [(xr - d + 2.0 * k, y0 + 2.0 * k), (xr - d - 1.0 * k, y0 - 4.0 * k), (xr - d - 1.5 * k, y0 - 9.0 * k)], 2.0 * k, 6.5)
        return
    cx = F.body_ext(c, F.vy(c, y0))[0]
    W = 12.0 * k * sq
    for s in (-1, 1):
        K.hose(f'data{s}', [(cx + s * W * 0.7, y0 + 2.0 * k), (cx + s * W * 0.85, y0 - 4.0 * k), (cx + s * W * 0.8, y0 - 9.0 * k)], 2.0 * k, 6.5)
    p = K.block('case', G.chamfer(G.rect(cx - W, y0, cx + W, y1), [3.0 * k, 3.0 * k, 2.0 * k, 2.0 * k]), 7, SHELL, bevel=1.3)
    if p is None:
        return
    p.fill(G.rect(cx - W, y0 - 1, cx + W, y0 + 3.8 * k), 'light')
    for i in range(9):
        xx = cx - W + 2.5 * k + i * (2 * W - 5.0 * k) / 8
        p.line([(xx, y0 + 0.8 * k), (xx, y0 + 3.4 * k)], 0.8 * k, 'deep')
    K.seam(p, [(cx - W + 1.0 * k, y0 + 3.8 * k), (cx + W - 1.0 * k, y0 + 3.8 * k)], 1.0)
    p.fill(G.rect(cx - W, y1 - 3.0 * k, cx + W, y1 + 1), 'shade')
    n = 3
    cw = (2 * W - 4.0 * k) / n
    for i in range(n):
        xa = cx - W + 2.0 * k + i * cw
        xb = xa + cw - 0.8 * k
        K.notch(p, xa, y0 + 5.0 * k, xb, y1 - 4.0 * k)
        p.fill(G.chamfer(G.rect(xa + 0.8 * k, y0 + 5.6 * k, xb - 0.8 * k, y1 - 4.6 * k), 0.6 * k), f'{IRON.name}.base', mask=None)
        p.fill(G.rect(xa + 0.8 * k, y0 + 5.6 * k, xb - 0.8 * k, y0 + 7.0 * k), f'{IRON.name}.light', mask=None)
        p.fill(G.rect((xa + xb) / 2 - 1.6 * k, y0 + 7.6 * k, (xa + xb) / 2 + 1.6 * k, y0 + 9.0 * k), f'{STEEL.name}.base', mask=None)
        K.lamp(p, (xa + xb) / 2, y1 - 6.6 * k, 1.2 * k, 0.8 * k)
    K.bolts(p, [(cx - W + 1.8 * k, y1 - 5.0 * k), (cx + W - 1.8 * k, y1 - 5.0 * k)], 0.9 * k)


# ============================================================================= body: thermal regulator

@register('ThermalFins', 'body', dirs=('east', 'north'), layer=0.36)
def thermal_regulator(K, c, fit):
    """Heat exchanger on the lower back: a finned radiator block with two fans and coolant
    lines into the armor."""
    k = c.k
    lay = F.layout(c, fit)
    y0 = lay['y_back'] + 1.0 * k
    y1 = lay['y_belt_back'] + 6.0 * k * lay['sv']
    if c.dir == 'east':
        xb = X(c, fit, (y0 + y1) / 2, 'l', lift=4.0)
        p = K.block('radiator', G.chamfer(G.rect(xb, y0, xb + 8.0 * k, y1), 1.6 * k), 2, SHELL, bevel=1.0)
        if p is not None:
            for i in range(5):
                yy = y0 + 2.0 * k + i * (y1 - y0 - 4.0 * k) / 4
                p.line([(xb - 1, yy), (xb + 4.0 * k, yy)], 1.0 * k, f'{DARK.name}.base', mask=None)
            p.fill(G.rect(xb, y1 - 2.4 * k, xb + 8.0 * k, y1), 'shade')
        K.hose('line', [(xb + 7.0 * k, y0 + 2.0 * k), (xb + 11.0 * k, y0 - 2.0 * k), (xb + 14.0 * k, y0 - 3.0 * k)], 2.2 * k, 1.6)
        return
    cx = F.body_ext(c, F.vy(c, (y0 + y1) / 2))[0]
    W = 15.0 * k * lay['sq']
    p = K.block('radiator', G.chamfer(G.rect(cx - W, y0, cx + W, y1), [2.0 * k, 2.0 * k, 3.0 * k, 3.0 * k]), 2, SHELL, bevel=1.1,
                tone='shade')
    if p is None:
        return
    p.fill(G.rect(cx - W, y1 - 2.6 * k, cx + W, y1), 'deep')
    # fin field in the middle, fans either side (they face the back: round from behind)
    K.slots(p, cx - W * 0.3, y0 + 2.5 * k, cx + W * 0.3, y1 - 3.5 * k, 6, vertical=True)
    for s in (-1, 1):
        fx = cx + s * W * 0.66
        fy = (y0 + y1) / 2 - 0.5 * k
        R = min(W * 0.28, (y1 - y0) / 2 - 2.0 * k)
        p.fill(G.circle(fx, fy, R), f'{DARK.name}.base', mask=None)
        for j in range(5):
            a = math.radians(j * 72 + 20)
            p.fill(G.poly([(fx, fy), (fx + math.cos(a) * R * 0.9, fy + math.sin(a) * R * 0.9),
                           (fx + math.cos(a + 0.7) * R * 0.85, fy + math.sin(a + 0.7) * R * 0.85)]), f'{FRAME.name}.base', mask=None)
        p.fill(G.circle(fx, fy, R * 0.3), f'{STEEL.name}.base', mask=None)
    for s in (-1, 1):
        K.hose(f'line{s}', [(cx + s * W * 0.9, y0 + 2.0 * k), (cx + s * (W + 3.0 * k), y0 - 2.0 * k), (cx + s * (W + 4.0 * k), y0 - 7.0 * k)],
               2.2 * k, 1.6)


# ============================================================================= body: rigidity matrix

@register('RigidityMatrix', 'body', dirs=('south', 'east'), layer=0.14)
def rigidity_matrix(K, c, fit):
    """Rigidity matrix: a locking leg frame - lattice guard plates over both thighs joined by a
    lock bar across the hips, with telescopic dampers from the belt and a hazard-striped lock
    housing in the middle."""
    k = c.k
    f = c.form
    lay = F.layout(c, fit)
    sq = lay['sq']
    yb = lay['y_belt']
    y0 = yb + 2.0 * k
    y1 = f.bot - 1.0 * k
    if c.dir == 'east':
        xf = X(c, fit, (y0 + y1) / 2, 'r', lift=3.0)
        damper(K, 'damper', (xf - 3.0 * k, yb - 6.0 * k), (xf - 2.6 * k, y0 + 5.0 * k), 1.6 * k, 2.4)
        p = K.block('plate', G.chamfer(G.poly([(xf - 7.5 * k, y0 + 3.0 * k), (xf, y0 + 3.0 * k), (xf + 0.6 * k, y1), (xf - 6.0 * k, y1)]),
                                       [1.0 * k, 2.4 * k, 2.4 * k, 1.0 * k]), 2, SHELL, bevel=1.1)
        if p is not None:
            p.fill(G.rect(xf - 7.5 * k, y1 - 2.6 * k, xf + 1, y1 + 1), 'shade')
            lattice(K, p, xf - 6.0 * k, y0 + 6.0 * k, xf - 1.4 * k, y1 - 4.0 * k, 2.8 * k)
        return
    cx, half = F.body_ext(c, F.vy(c, (y0 + y1) / 2))
    xm_s = []
    for s in (-1, 1):
        xm = cx + s * min(10.0 * k * sq, half * 0.48)
        w0 = min(6.0 * k * sq, half * 0.3)
        xm_s.append(xm)
        damper(K, f'damper{s}', (xm + s * w0 * 0.45, yb - 6.0 * k), (xm + s * w0 * 0.4, y0 + 4.5 * k), 1.5 * k, 2.4)
        ring = G.chamfer(G.poly([(xm - w0, y0 + 3.0 * k), (xm + w0, y0 + 3.0 * k), (xm + w0 * 0.82, y1), (xm - w0 * 0.82, y1)]), 1.8 * k)
        p = K.block(f'plate{s}', ring, 2, SHELL, bevel=1.3)
        if p is None:
            continue
        p.fill(G.rect(xm - w0, y1 - 2.8 * k, xm + w0, y1 + 1), 'shade')
        lattice(K, p, xm - w0 * 0.62, y0 + 6.2 * k, xm + w0 * 0.62, y1 - 4.4 * k, 3.4 * k)
        K.bolts(p, [(xm - w0 * 0.72, y0 + 4.6 * k), (xm + w0 * 0.72, y0 + 4.6 * k)], 0.85 * k)
    # lock bar across the hips and the lock housing
    bar = K.block('lockbar', G.chamfer(G.rect(xm_s[0], y0 + 1.0 * k, xm_s[1], y0 + 4.4 * k), 0.8 * k), 2.6, FRAME, bevel=0.0)
    if bar is not None:
        bar.fill(G.rect(xm_s[0], y0 + 1.0 * k, xm_s[1], y0 + 2.0 * k), 'light')
        bar.fill(G.rect(xm_s[0], y0 + 3.6 * k, xm_s[1], y0 + 4.4 * k), 'shade')
    hs = K.block('lock', G.chamfer(G.rect(cx - 4.0 * k, y0 - 0.5 * k, cx + 4.0 * k, y0 + 6.5 * k), 1.2 * k), 2.7, FRAME, bevel=0.6)
    if hs is not None:
        for i in range(4):
            xx = cx - 4.0 * k + i * 2.4 * k
            hs.fill(G.poly([(xx, y0 + 6.5 * k), (xx + 1.2 * k, y0 + 6.5 * k), (xx + 2.6 * k, y0 + 4.2 * k), (xx + 1.4 * k, y0 + 4.2 * k)]),
                    f'{AMBER.name}.shade', mask=None)
        K.bolt(hs, cx, y0 + 1.8 * k, 0.9 * k)


# ============================================================================= body: longjump hydraulics

@register('LongjumpHydraulics', 'body', dirs=('east', 'north'), layer=0.2)
def longjump_hydraulics(K, c, fit):
    """Jump hydraulics: a big ram down the back of each leg from the hip to the heel, fed by a
    pressure accumulator on the lower back. The rams' pins turn about the left-right axis."""
    k = c.k
    f = c.form
    lay = F.layout(c, fit)
    y0 = lay['y_belt_back'] - 2.0 * k
    y1 = f.bot - 2.0 * k
    if c.dir == 'east':
        xb = X(c, fit, (y0 + y1) / 2, 'l', lift=2.5) + 3.0 * k
        K.piston('ram', (xb + 2.0 * k, y0), (xb, y1), 3.2 * k, 1.6 * k, 2, split=0.55, body=FRAME)
        acc = K.block('accumulator', G.rounded(G.rect(xb - 1.0 * k, y0 - 10.0 * k, xb + 7.0 * k, y0 + 2.0 * k), 3.0 * k), 1.9, SHELL,
                      bevel=1.0)
        if acc is not None:
            K.chevrons(acc, xb + 3.0 * k, y0 - 7.0 * k, 4.0 * k, 2.0 * k, 2)
        return
    cx = F.body_ext(c, F.vy(c, (y0 + y1) / 2))[0]
    for s in (-1, 1):
        xa = cx + s * 9.0 * k * lay['sq']
        K.piston(f'ram{s}', (xa, y0 + 1.0 * k), (xa + s * 1.0 * k, y1), 3.2 * k, 1.6 * k, 2, split=0.55, body=FRAME)
    acc = K.block('accumulator', G.rounded(G.rect(cx - 6.0 * k, y0 - 7.0 * k, cx + 6.0 * k, y0 + 3.0 * k), 2.6 * k), 2.1, SHELL, bevel=1.0,
                  tone='shade')
    if acc is not None:
        K.chevrons(acc, cx, y0 - 5.0 * k, 5.0 * k, 2.0 * k, 2)


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
    latitudes: ``inner`` px at 128 inside the helmet's edge, ``outer`` px out (south/north),
    set into a shell flange on the helmet so it reads as built in. East view (right side only):
    a housing on the side of the head over ``east_x`` (px at 128 from the head's centre).
    Returns a dict (part, sgn, x_out, x_in, x_side, x0, x1, y0, y1) or None."""
    k = c.k
    hf = c.form
    y0, y1 = F.head_y(c, ph1), F.head_y(c, ph0)
    if c.dir == 'east':
        if s < 0:
            return None
        x0, x1 = hf.cx + east_x[0] * k, hf.cx + east_x[1] * k
        K.block(name + '_flange', G.chamfer(G.rect(x0 - 2.5 * k, y0 + 2.0 * k, x1 - 3.0 * k, y1 + 2.0 * k), 2.0 * k), z - 0.2, SHELL,
                bevel=0.6, tone='shade')
        p = K.block(name, G.chamfer(G.rect(x0, y0, x1, y1), [chamfer * k, chamfer * 1.6 * k, chamfer * 0.8 * k, chamfer * 0.8 * k]), z,
                    SHELL, bevel=1.2)
        if p is None:
            return None
        p.fill(G.rect(x0 - 1, y0 - 1, x1 + 1, y0 + 2.8 * k), 'light')
        K.seam(p, [(x0 + 1.5 * k, y0 + 2.8 * k), (x1 - 2.0 * k, y0 + 2.8 * k)])
        p.fill(G.rect(x0 - 1, y1 - 2.8 * k, x1 + 1, y1 + 1), 'shade')
        return dict(part=p, sgn=1, x_out=x1, x_in=x0, x_side=x1, y0=y0, y1=y1, x0=x0, x1=x1)
    pts_in, sgn = edge_curve(c, fit, s, ph0, ph1, 7, out=-inner)
    xe, _ = hside(c, fit, s, ph0, ph1)
    xo = xe + sgn * outer * k
    fl_in, _ = edge_curve(c, fit, s, ph0 - 0.08, ph1 + 0.06, 7, out=-(inner + 2.2))
    fl_out, _ = edge_curve(c, fit, s, ph0 - 0.08, ph1 + 0.06, 7, out=1.0)
    K.block(name + '_flange', G.chamfer(G.poly(fl_in + fl_out[::-1]), 1.2 * k), z - 0.2, SHELL, bevel=0.6,
            tone='shade' if c.dir == 'south' else 'deep')
    ring = G.chamfer(G.poly(pts_in + [(xo, pts_in[-1][1]), (xo, pts_in[0][1])]), chamfer * k)
    p = K.block(name, ring, z, SHELL, bevel=1.2, tone='base' if c.dir == 'south' else 'shade')
    if p is None:
        return None
    xs = xo - sgn * 2.6 * k
    p.fill(G.rect(min(xo, xs), y0 - 1, max(xo, xs), y1 + 1), 'shade' if c.dir == 'south' else 'deep')
    xin = min(x for x, _ in pts_in) if sgn > 0 else max(x for x, _ in pts_in)
    p.fill(G.rect(min(xo, xin) - 1, y1 - 2.6 * k, max(xo, xin) + 1, y1 + 1), 'shade' if c.dir == 'south' else 'deep')
    return dict(part=p, sgn=sgn, x_out=xo, x_in=xin, x_side=xs, y0=y0, y1=y1, x0=min(xo, xin), x1=max(xo, xin))


def _phi_at(c, y):
    """Head latitude of screen row y."""
    hf = c.form
    return math.asin(max(-1.0, min(1.0, (hf.cy - y) / (hf.ry * 0.92))))


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


@register('Plating', 'head', dirs=('south', 'east'), layer=0.2)
def helm_plating(K, c, fit):
    """Brow guard: a thick composite visor hood bolted across the upper face."""
    _brow_guard(K, c, fit, hopts(fit, 'Plating', phi=(0.3, 0.62), w=0.66))


@register('UraniumPlating', 'head', dirs=('south', 'east'), layer=0.2)
def helm_uranium(K, c, fit):
    """Uranium brow guard: a dark, heavy visor hood in a dyed trim frame with a trefoil."""
    k = c.k
    hf = c.form
    o = hopts(fit, 'UraniumPlating', phi=(0.26, 0.68), w=0.78)
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


# ============================================================================= helmet: targeting uplink

@register('TargetingUplink', 'head', layer=0.8)
def targeting_uplink(K, c, fit):
    """Laser rangefinder and data uplink high on the side of the helmet above the sensor array:
    a compact housing with the rangefinder's dark lens in its front and a whip antenna rising
    from its back on a sprung base."""
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
        # the antenna stands on the housing's back end
        xa = pod['x0'] + 2.5 * k if c.dir == 'east' else (pod['x_side'] + pod['x_in']) / 2 + sgn * 1.0 * k
        K.block('ant_base', G.chamfer(G.rect(xa - 1.6 * k, y0 - 2.4 * k, xa + 1.6 * k, y0 + 1.0 * k), 0.6 * k), 1.8, HOSE, bevel=0.4)
        K.rod('whip', (xa, y0 - 2.0 * k), (xa, y0 - 15.0 * k), 0.55 * k, 1.7, IRON)
        K.block('whip_tip', G.circle(xa, y0 - 15.2 * k, 0.9 * k), 1.75, HOSE, bevel=0.3)
    if c.dir == 'north':
        K.slots(p, pod['x0'] + 2.0 * k, y0 + 3.0 * k, pod['x1'] - 2.0 * k, y1 - 3.0 * k, 2)
        return
    if c.dir == 'east':
        ym = (y0 + y1) / 2 + 0.8 * k
        K.cylinder('emitter', (pod['x1'] - 2.5 * k, ym), (pod['x1'] + 1.8 * k, ym), 1.5 * k, 3, FRAME)
        g = K.flat('emit_glass', G.ellipse(pod['x1'] + 2.1 * k, ym, 0.8 * k, 1.35 * k), 3.2, GLASS)
        if g is not None:
            g.fill(G.ellipse(pod['x1'] + 2.3 * k, ym + 0.2 * k, 0.45 * k, 0.8 * k), f'{RED.name}.deep', mask=None)
        K.slots(p, pod['x0'] + 2.0 * k, y0 + 3.6 * k, pod['x0'] + 6.0 * k, y1 - 3.0 * k, 2)
        return
    xm = (pod['x_side'] + pod['x_in']) / 2
    K.lens('emitter', xm, (y0 + y1) / 2 + 0.8 * k, 2.0 * k, 3, RED)


# ============================================================================= helmet: sensor array

@register('SensorArray', 'head', layer=0.7)
def sensor_array(K, c, fit):
    """Multispectral sensor array: a narrow pod built out of the side of the helmet under the
    uplink and set into a flange, with three optics stacked in its front - thermal, visible and
    ultraviolet - behind a hood. From the side the three lens barrels look forward; from behind,
    the pod's heat sink and the loom back into the helmet."""
    k = c.k
    hf = c.form
    o = hopts(fit, 'SensorArray', phi=(-0.26, 0.4))
    s = column_side(fit, 'SensorArray')
    ph0, ph1 = o['phi']
    lenses = ((0.22, 1.5, AMBER), (0.52, 2.0, CYAN), (0.82, 1.5, VIOLET))
    if c.dir == 'east':
        if s < 0:
            return
        y0, y1 = F.head_y(c, ph1), F.head_y(c, ph0)
        x0, x1 = hf.cx - 3.0 * k, hf.cx + 9.0 * k
        K.block('flange', G.chamfer(G.rect(x0 - 2.5 * k, y0 + 2.0 * k, x1 - 3.0 * k, y1 + 1.5 * k), 1.6 * k), 1.8, SHELL, bevel=0.6,
                tone='shade')
        K.hose('loom', [(x0 + 1.0 * k, y1 - 2.5 * k), (x0 - 4.0 * k, y1 + 1.0 * k), (x0 - 9.0 * k, y1 + 1.5 * k)], 2.2 * k, 1.9)
        pod = K.block('pod', G.chamfer(G.rect(x0, y0, x1, y1), [2.0 * k, 3.2 * k, 1.6 * k, 1.6 * k]), 2, SHELL, bevel=1.2)
        if pod is None:
            return
        pod.fill(G.rect(x0 - 1, y0 - 1, x1 + 1, y0 + 2.6 * k), 'light')
        pod.fill(G.rect(x0 - 1, y1 - 2.4 * k, x1 + 1, y1 + 1), 'shade')
        K.slots(pod, x0 + 2.0 * k, y0 + 4.0 * k, x0 + 5.5 * k, y1 - 4.0 * k, 3)
        K.bolt(pod, x0 + 8.0 * k, y1 - 4.5 * k, 0.8 * k)
        for i, (t, r, mat) in enumerate(lenses):
            yy = y0 + (y1 - y0) * t
            bx0, bx1 = x1 - 3.0 * k, x1 + (1.8 if r > 1.8 else 1.0) * k
            K.cylinder(f'barrel{i}', (bx0, yy), (bx1, yy), r * k, 3 + i * 0.01, FRAME)
            g = K.flat(f'glass{i}', G.ellipse(bx1 + 0.6 * k, yy, 0.8 * k, r * k * 0.9), 3.5 + i * 0.01, GLASS)
            if g is not None:
                g.fill(G.ellipse(bx1 + 0.8 * k, yy + 0.3 * k, 0.45 * k, r * k * 0.5), f'{mat.name}.deep', mask=None)
        return
    pod = side_pod(K, c, fit, s, ph0, ph1, 4.0, 4.5, 2, 'pod', chamfer=2.0)
    if pod is None:
        return
    p, sgn = pod['part'], pod['sgn']
    y0, y1 = pod['y0'], pod['y1']
    xa, xb = sorted((pod['x_side'], pod['x_in']))
    if c.dir == 'north':
        K.slots(p, xa + 1.6 * k, y0 + 3.0 * k, xb - 1.6 * k, y0 + 11.0 * k, 3)
        xm = (xa + xb) / 2
        K.hose('loom', [(xm, y1 - 2.0 * k), (pod['x_in'] - sgn * 4.0 * k, y1 + 1.5 * k), (pod['x_in'] - sgn * 9.0 * k, y1 + 2.0 * k)], 2.2 * k,
               1.9)
        return
    # hood over the optics, then the dark window with the three lenses stacked
    p.fill(G.rect(xa - 1, y0 - 1, xb + 1, y0 + 2.8 * k), 'light')
    wx0, wx1 = xa + 0.6 * k, xb - 0.6 * k
    wy0, wy1 = y0 + 3.0 * k, y1 - 2.6 * k
    p.fill(G.chamfer(G.rect(wx0, wy0, wx1, wy1), 1.0 * k), f'{DARK.name}.base', mask=None)
    xm = (wx0 + wx1) / 2
    for i, (t, r, mat) in enumerate(lenses):
        K.lens(f'lens{i}', xm, wy0 + (wy1 - wy0) * t, min(r * k, (wx1 - wx0) / 2 - 0.2 * k), 3 + i * 0.01, mat)


# ============================================================================= helmet: subpersona

@register('Subpersona', 'head', dirs=('south', 'north'), layer=0.5)
def helm_subpersona(K, c, fit):
    """Subcore housing low on the side of the helmet opposite the sensors: three subcore
    cartridges slotted into its front, each with a pull tab, and one status lamp."""
    k = c.k
    o = hopts(fit, 'Subpersona', phi=(-0.4, 0.06))
    pod = side_pod(K, c, fit, column_side(fit, 'Subpersona'), o['phi'][0], o['phi'][1], 3.5, 3.5, 2, 'housing', chamfer=1.6)
    if pod is None:
        return
    p = pod['part']
    y0, y1 = pod['y0'], pod['y1']
    xa, xb = sorted((pod['x_side'], pod['x_in']))
    if c.dir == 'north':
        K.slots(p, xa + 1.4 * k, y0 + 3.0 * k, xb - 1.4 * k, y1 - 3.5 * k, 3)
        return
    n = 3
    h = (y1 - y0 - 5.0 * k) / n
    for i in range(n):
        yy = y0 + 2.0 * k + h * i
        K.notch(p, xa + 1.0 * k, yy, xb - 1.0 * k, yy + h - 1.0 * k)
        p.fill(G.rect(xa + 1.4 * k, yy + 0.4 * k, xb - 2.6 * k, yy + 1.3 * k), f'{STEEL.name}.shade', mask=None)
    K.lamp(p, xb - 1.8 * k, y1 - 2.0 * k, 0.9 * k, 0.7 * k)


# ============================================================================= helmet: second mind

@register('SecondMind', 'head', dirs=('south', 'north'), layer=0.55)
def second_mind(K, c, fit):
    """Second mind: an armored persona core housing at the helmet's temple opposite the sensors,
    the core showing dimly through a round port in its front, cooling slots above it; from
    behind, its heat sink and a data cable into the helmet."""
    k = c.k
    o = hopts(fit, 'SecondMind', phi=(0.32, 0.86))
    ph0, ph1 = o['phi']
    pod = side_pod(K, c, fit, column_side(fit, 'SecondMind'), ph0, ph1, 4.5, 4.0, 2, 'housing', chamfer=2.4)
    if pod is None:
        return
    p, sgn = pod['part'], pod['sgn']
    y0, y1 = pod['y0'], pod['y1']
    xa, xb = sorted((pod['x_side'], pod['x_in']))
    if c.dir == 'north':
        K.slots(p, xa + 1.4 * k, y0 + 3.0 * k, xb - 1.4 * k, y1 - 3.5 * k, 3)
        xm = (xa + xb) / 2
        K.hose('data', [(xm, y1 - 1.5 * k), (pod['x_in'] - sgn * 4.0 * k, y1 + 2.0 * k), (pod['x_in'] - sgn * 8.0 * k, y1 + 2.5 * k)], 2.4 * k,
               1.9)
        return
    p.fill(G.rect(xa - 1, y0 - 1, xb + 1, y0 + 2.6 * k), 'light')
    K.slots(p, xa + 1.4 * k, y0 + 3.4 * k, xb - 1.4 * k, y0 + 6.4 * k, 2)
    cx_, cy_ = (xa + xb) / 2, y0 + (y1 - y0) * 0.62
    R = min((xb - xa) / 2 - 0.8 * k, (y1 - y0) * 0.26)
    p.fill(G.circle(cx_, cy_, R + 0.9 * k), f'{FRAME.name}.base', mask=None)
    p.fill(G.circle(cx_, cy_ - 0.3 * k, R + 0.3 * k), f'{FRAME.name}.light', mask=None)
    p.fill(G.circle(cx_, cy_, R), f'{DARK.name}.deep', mask=None)
    p.fill(G.circle(cx_, cy_, R * 0.62), f'{CYAN.name}.deep', mask=None)
    p.fill(G.circle(cx_, cy_, R * 0.34), f'{CYAN.name}.base', mask=None)
    p.fill(G.ellipse(cx_ - R * 0.3, cy_ - R * 0.32, R * 0.16, R * 0.1), f'{GLASS.name}.light', mask=None)


# ============================================================================= helmet: neural link

@register('NeuralLink', 'head', dirs=('east', 'north'), layer=0.3)
def neural_link(K, c, fit):
    """Neural link (bionic synchronization): a spinal interface socket at the nape with three
    armored plugs seated side by side, their cables bending down into the armor's collar. From
    the side the socket is seen edge-on and the three cables lie behind one another as one
    bundle."""
    k = c.k
    hf = c.form
    yb = F.helm_bottom_y(c, fit) + hopts(fit, 'NeuralLink', dy=0.0)['dy'] * k
    if c.dir == 'east':
        r_back = F.helm_side(fit, 'east', 'l', -0.9, -0.4, 0.6, 1.3)
        xo = F.head_edge_x(c, fit, 'l', -0.6, r_back) + 1.5 * k
        y0, y1 = yb - 13.0 * k, yb - 3.0 * k
        K.hose('cables', [(xo + 2.6 * k, y1 - 2.0 * k), (xo + 1.2 * k, y1 + 3.0 * k), (xo + 1.8 * k, y1 + 6.0 * k)], 3.0 * k, 1.8, ribs=1.8)
        blk = K.block('socket', G.chamfer(G.rect(xo - 1.0 * k, y0, xo + 5.5 * k, y1), [1.2 * k, 1.8 * k, 1.2 * k, 1.2 * k]), 2, SHELL, bevel=1.0)
        if blk is not None:
            blk.fill(G.rect(xo - 1.0 * k, y0 - 1, xo + 5.5 * k, y0 + 2.2 * k), 'light')
            blk.fill(G.rect(xo - 1.0 * k, y1 - 2.2 * k, xo + 5.5 * k, y1 + 1), 'shade')
            K.notch(blk, xo - 1.0 * k, y0 + 4.0 * k, xo + 0.6 * k, y1 - 3.6 * k)
        return
    cx = hf.cx
    y0, y1 = yb - 15.0 * k, yb - 5.0 * k
    for i, dx in enumerate((-3.6, 0.0, 3.6)):
        K.hose(f'cable{i}', [(cx + dx * k, y1 - 2.0 * k), (cx + dx * 1.15 * k, y1 + 3.0 * k), (cx + dx * 1.25 * k, y1 + 6.0 * k)], 2.2 * k,
               1.8 + i * 0.01, ribs=1.8)
    blk = K.block('socket', G.chamfer(G.rect(cx - 7.0 * k, y0, cx + 7.0 * k, y1), [2.0 * k, 2.0 * k, 1.6 * k, 1.6 * k]), 2, SHELL, bevel=1.1,
                  tone='shade')
    if blk is None:
        return
    blk.fill(G.rect(cx - 7.0 * k, y0 - 1, cx + 7.0 * k, y0 + 2.2 * k), 'base')
    blk.fill(G.rect(cx - 7.0 * k, y1 - 2.2 * k, cx + 7.0 * k, y1 + 1), 'deep')
    for dx in (-3.6, 0.0, 3.6):
        xx = cx + dx * k
        # round mil-spec plugs with knurled collars
        blk.fill(G.circle(xx, (y0 + y1) / 2 - 0.4 * k, 1.8 * k), f'{DARK.name}.base', mask=None)
        blk.fill(G.circle(xx, (y0 + y1) / 2 - 0.4 * k, 1.3 * k), f'{FRAME.name}.base', mask=None)
        blk.fill(G.circle(xx - 0.3 * k, (y0 + y1) / 2 - 0.8 * k, 0.6 * k), f'{FRAME.name}.light', mask=None)


# ============================================================================= helmet: stress dampener

@register('StressDampener', 'head', layer=0.4)
def stress_dampener(K, c, fit):
    """Neural stress dampener: a low armored emitter dome on the crown (or, on crested helmets,
    the back of the dome) with three short stub antennas round it - one at the front, two at
    the back - placed in 3D so each view shows them where they stand."""
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
    rp = 5.2 * k
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
    K.block('base', G.chamfer(G.rect(x - w, yt - 0.8 * k, x + w, yt + 2.4 * k), 1.0 * k), 1.8, FRAME, bevel=0.6)
    dome = K.block('dome', G.ellipse(x, yt - 0.8 * k, w * 0.66, h), 2, SHELL, bevel=1.1, tone='base' if c.dir != 'north' else 'shade')
    for i, (dz, xx, yy) in enumerate(prongs):
        z = 2.05 + (0.2 if dz > 0 else -0.3) + i * 0.01
        top = yy - h - 3.2 * k
        K.rod(f'stub{i}', (xx, yy - 1.0 * k), (xx, top), 0.6 * k, z, IRON)
        K.block(f'stub_tip{i}', G.circle(xx, top, 0.9 * k), z + 0.005, HOSE, bevel=0.0)
    if dome is not None and c.dir != 'north':
        dome.fill(G.ellipse(x, yt - 1.2 * k, w * 0.3, h * 0.42), f'{DARK.name}.base', mask=None)
        dome.fill(G.ellipse(x - w * 0.08, yt - 1.6 * k, w * 0.1, h * 0.14), f'{GLASS.name}.light', mask=None)


# ============================================================================= helmet: regenerators

@register('Regenerators', 'head', dirs=('east', 'north'), layer=0.6)
def helm_regenerators(K, c, fit):
    """Two regenerator canisters rising from an armored cradle on the back of the helmet, angled
    up and apart; from the side the near canister hides the far one."""
    k = c.k
    hf = c.form
    ph = hopts(fit, 'Regenerators', phi=-0.18)['phi']
    # on helmets open at the back the nape is high: keep the cradle above the neural link's socket
    ph = max(ph, _phi_at(c, F.helm_bottom_y(c, fit) - 19.0 * k))
    if c.dir == 'east':
        r_back = F.helm_side(fit, 'east', 'l', ph - 0.25, ph + 0.35, 0.8, 1.25)
        xb = F.head_edge_x(c, fit, 'l', ph + 0.13, r_back) + 2.0 * k
        yb = F.head_y(c, ph + 0.13)
        L = 13.0 * k
        ang = math.radians(28)
        b = (xb + 1.0 * k, yb - 2.0 * k)
        canister(K, 'can', b, (b[0] - L * math.sin(ang), b[1] - L * math.cos(ang)), 2.3 * k, 2)
        cr = K.block('cradle', G.chamfer(G.rect(xb - 2.0 * k, yb - 3.0 * k, xb + 6.0 * k, yb + 5.0 * k), 1.4 * k), 2.1, SHELL, bevel=1.0)
        if cr is not None:
            cr.fill(G.rect(xb - 2.0 * k, yb + 2.6 * k, xb + 6.0 * k, yb + 5.0 * k), 'shade')
            K.bolt(cr, xb + 3.5 * k, yb + 0.5 * k, 0.8 * k)
        return
    yb = F.head_y(c, ph)
    for s in (-1, 1):
        canister(K, f'can{s}', (hf.cx + s * 5.0 * k, yb - 1.0 * k), (hf.cx + s * 9.0 * k, yb - 15.0 * k), 2.4 * k, 2, tone='shade')
    cr = K.block('cradle', G.chamfer(G.rect(hf.cx - 8.5 * k, yb - 3.0 * k, hf.cx + 8.5 * k, yb + 4.0 * k), 1.6 * k), 2.1, SHELL, bevel=1.0,
                 tone='shade')
    if cr is not None:
        cr.fill(G.rect(hf.cx - 8.5 * k, yb + 1.8 * k, hf.cx + 8.5 * k, yb + 4.0 * k), 'deep')
        K.bolts(cr, [(hf.cx - 5.0 * k, yb + 0.2 * k), (hf.cx + 5.0 * k, yb + 0.2 * k)], 0.8 * k)


