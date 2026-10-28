"""rwtexturegen spec: worn art for the armor modifications, fitted to every supported armor.

    pip install -e <rwtexturegen>
    rwtex build modules.py --out <scratch dir> --mod ../..

Every modification that shows on the pawn gets one texture set per armor fit:

    body    Textures/ModularPowerArmor/Worn/Body/<Module>_<Fit>/<Module>_<Fit>_<BodyType>_<dir>.png
    helmet  Textures/ModularPowerArmor/Worn/Head/<Module>_<Fit>/<Module>_<Fit>_<dir>.png

and the render nodes ask for ModularPowerArmor/Worn/Body/<Module>_{fit}/<Module>_{fit}, where the
mod fills in the fit of the armor piece the module is installed in (see MPA_ArmorTargets.xml).

The art is white and unmasked. The mod draws it with the armor's own colour, so it is dyed
together with the armor, and it uses the armor's own construction: flat white faces, #ccc side
faces, near-black recesses and a black outline. Each module has its own place on the armor, and
the places never overlap, so any combination of modules can be installed at once:

    body    chest and shoulders (plating), forearms (servos), belt (trauma suite), hips and thighs
            (exoframe), upper back (co-processor), lower back (thermal regulator)
    helmet  brow (plating), crown (stress dampener), right side (targeting uplink), left side
            (sensor array), back (co-processor), nape (neural link)

Placement follows the silhouette of each armor, measured from its worn textures
(armor_profiles.json, written by measure_profiles.py), and the per-armor adjustments in FITS
move modules clear of launchers, wings, pauldrons, crests and horns.
"""
import json
import math
import os

import numpy as np

from rwtex import geom as G
from rwtex.archetypes import armor3d as A
from rwtex.archetypes.apparel import armor, helmet

PI = math.pi
HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, 'armor_profiles.json'), encoding='utf-8') as _f:
    PROFILES = json.load(_f)
V = PROFILES['v']

BODY_FITS = list(PROFILES['armors'])
HELMET_FITS = list(PROFILES['helmets'])
BODY_MODULES = ['Plating', 'BiogelServos', 'TraumaSuite', 'Exoframe', 'CoProcessor', 'ThermalFins']
HELMET_MODULES = ['Plating', 'TargetingUplink', 'SensorArray', 'CoProcessor', 'NeuralLink', 'StressDampener']

# Views a module never shows in; the mod hides those facings with visibleFacing instead of
# loading empty textures.
BODY_DIRS = {'TraumaSuite': ('south', 'east'), 'CoProcessor': ('east', 'north'), 'ThermalFins': ('east', 'north')}
HELMET_DIRS = {'Plating': ('south', 'east'), 'CoProcessor': ('east', 'north'), 'NeuralLink': ('east', 'north')}

MATS = dict(shell='armor_white', undersuit='undersuit', accent='visor_dark', trim='armor_white', joint='armor_white',
            lens='visor_dark', strap='undersuit', energy='visor_dark')

# Per-armor adjustments. Keys:
#   skip      {module: [dirs]} where the module isn't drawn (it would sit on a feature of the armor)
#   <module>  overrides for that module's options (surface coordinates, offsets in px at 128)
# Shoulder plates only go on plain shoulders: wings, gold trim, pauldrons and the grenadier's
# launcher stay visible. Armors with something on the upper back (launcher, jump pack, rods,
# thrusters, horns) show the co-processor from behind only.
FITS = {
    'Marine': {},
    'Recon': {},
    'Cataphract': {'skip': {'CoProcessor': ('east',)}},
    'Grenadier': {'Plating': {'caps': (1,)}, 'skip': {'CoProcessor': ('east',)}},
    'Locust': {'Plating': {'caps': ()}, 'skip': {'CoProcessor': ('east',)}},
    'Phoenix': {'Plating': {'caps': ()}, 'skip': {'CoProcessor': ('east',)}},
    'PrestigeMarine': {'Plating': {'caps': ()}},
    'PrestigeRecon': {'Plating': {'caps': ()}},
    'PrestigeCataphract': {'Plating': {'caps': ()}, 'skip': {'CoProcessor': ('east',)}},
    'Siegebreaker': {'Plating': {'caps': ()}, 'skip': {'CoProcessor': ('east',)}},
    'RoyalSiegebreaker': {'Plating': {'caps': ()}, 'skip': {'CoProcessor': ('east',)}},
    'Trooper': {},
    'RoyalTrooper': {'Plating': {'chest': False}},      # the chest carries the eagle; the plates go over the small gold pads
    'Privateer': {'Plating': {'caps': (-1,)}},
}


def fit_opts(fit, module, **defaults):
    defaults.update(FITS.get(fit, {}).get(module, {}))
    return defaults


def skipped(c, fit, module):
    return skipped_module(fit, module, c.dir)


def skipped_module(fit, module, view):
    return view in FITS.get(fit, {}).get('skip', {}).get(module, ())


# ----------------------------------------------------------------------------- measured silhouettes

def edge(fit, bt, view, side, v0, v1):
    """Offset (px at 128) of the armor's coloured edge beyond the naked body silhouette over
    v0..v1, on the screen-left ('l') or screen-right ('r') side of a view. Rows where the edge
    jumps inward (a dark belt or undersuit counts as outline) are ignored."""
    arr = PROFILES['armors'][fit]['bodies'][bt][f'{view}_{side}']
    vals = [o for v, o in zip(V, arr) if o is not None and v0 - 1e-6 <= v <= v1 + 1e-6]
    if not vals:
        return 0.0
    hi = max(vals)
    return float(np.median([o for o in vals if o >= hi - 6.0]))


def shoulder_top(c, fit, side=None):
    """Screen y where the armor's shoulder starts (side 'l'/'r' for south/north)."""
    tops = PROFILES['armors'][fit]['bodies'][c.bt][f'{c.dir}_shoulder_top']
    y = tops[0] if c.dir == 'east' else tops[0 if side == 'l' else 1]
    f = c.form
    if y is None:
        return f.top + 2.0 * c.k
    return min(max(y * c.k, f.top), f.top + 10.0 * c.k)


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
    """Screen x of the armor's coloured edge (plus ``lift`` px) at height v on one side."""
    cx, h = body_ext(c, v)
    off = min(max(edge(fit, c.bt, c.dir, side, v - win, v + win), lo), hi) + lift
    return cx + (-1 if side == 'l' else 1) * (h + off * c.k)


def radius(c, px):
    """Radius factor (a function of v) that puts a surface patch ``px`` beyond the body
    silhouette in this view; ``px`` may itself be a function of v."""
    def r(v):
        o = px(v) if callable(px) else px
        return max(0.2, 1.0 + o * c.k / max(body_ext(c, v)[1], 1.0))
    return r


def tn(c, i, role='shell'):
    """Tone i of a role's ramp: 0 light, 1 base (white faces), 2 shade (#ccc), 3 deep."""
    return A._tones(c, role)[i]


def face(c):
    """Tone index of a face turned to the camera (white, but #ccc for the whole back)."""
    return 2 if c.dir == 'north' else 1


def plate(c, name, poly, z, r, tone=None, role='shell', **kw):
    """Flat-shaded surface patch (vanilla plate construction), unmasked."""
    return A.vplate(c, name, poly, z, role, r=r, tone=tone, mask=None, **kw)


def shape(c, name, ring, z, tone_i=1, role='shell'):
    """A flat 2D part (for things seen side-on, where a surface patch would be a sliver)."""
    return c.part(name, ring, role, z, shading=[], mask=None, tone=tn(c, tone_i, role))


def dot(p, x, y, rx, ry=None, tone='undersuit.base'):
    p.fill(G.ellipse(x, y, rx, rx if ry is None else ry), tone)


def edge_strip(c, fit, name, side, v0, v1, out_px, depth_px, z, tone_i=1, n=6, lo=-4.0, hi=8.0, chamfer=1.2):
    """A slab standing ``out_px`` proud of the armor's edge on one side, ``depth_px`` thick,
    from v0 to v1 - how a box on the front, back or flank looks when seen edge-on."""
    k = c.k
    sgn = -1 if side == 'l' else 1
    outer, inner = [], []
    for v in np.linspace(v0, v1, n):
        x = armor_x(c, fit, v, side, lo=lo, hi=hi, lift=out_px)
        y = c.form.y(v)
        outer.append((x, y))
        inner.append((x - sgn * depth_px * k, y))
    ring = G.poly(outer + inner[::-1])
    if chamfer > 0:
        ring = G.chamfer(ring, chamfer * k)
    return shape(c, name, ring, z, tone_i), outer, inner


# ----------------------------------------------------------------------------- body layout

def _load_layouts():
    import rwtex
    path = os.path.join(os.path.dirname(rwtex.__file__), 'data', 'armor_fit.json')
    with open(path, encoding='utf-8') as f:
        d = json.load(f)
    return d['layout'], d['variants']['recon']['layout']


MARINE_LAYOUT, RECON_LAYOUT = _load_layouts()
# Armors built like recon armor (slim, inside the body, recon plate heights); the rest follow marine armor.
RECON_BUILT = {'Recon', 'Locust', 'PrestigeRecon', 'Trooper', 'RoyalTrooper'}


def body_layout(c, fit):
    """Where each module sits on this body type, as surface v ranges.

    Heights come from the plate layout rwtexturegen measured on vanilla marine and recon armor
    for every body type (chest plate bottom, belt, tassets, back plate), so modules land on the
    same part of the armor whatever the body. Sizes are in px at 128, scaled with the torso height
    (``sv``) or width (``sh``). Neighbouring modules keep at least ~5 px between their coloured
    areas so their outlines touch at most."""
    L = (RECON_LAYOUT if fit in RECON_BUILT else MARINE_LAYOUT)[c.bt]
    f = c.form
    k = c.k
    y_elbow = f.y(MARINE_LAYOUT[c.bt]['front_bot'])      # the arms are where they are, whatever the armor
    y_chest, y_belt = f.y(L['front_bot']), f.y(L['belt_front'])
    y_back, y_belt_back = f.y(L['back_bot']), f.y(L['belt_back'])
    y_tasset = min(f.y(L['tasset_bot']), f.bot)
    sv = (y_belt - f.top) / (45.0 * k)
    sh = f.a(0.5)[1] / (23.5 * k)
    vy = lambda y: (y - f.top) / f.H
    px = lambda n: n * sv ** 0.8 * k
    return dict(
        sv=sv, sh=sh, sq=math.sqrt(max(sh, 0.3)),
        cap_h=min(max(0.62 * f.a(0.1)[1], 9.0 * k), 16.0 * k),
        chest=(vy(y_chest - px(18.0)), vy(y_chest - px(8.0))),
        servo=(vy(y_elbow - px(15.0)), vy(y_elbow - px(3.5))),
        trauma=(vy(y_chest - px(0.5)), vy(y_belt + px(2.5) * min(1.0, sh))),
        hip=vy(y_belt + px(5.5) + max(0.0, 1.0 - sh) * 10.0 * k),
        strut=(vy(y_belt + px(3.0)), vy(y_tasset - 1.0 * k)),
        cpu=(vy(f.top + px(8.0)), vy(y_back - px(3.0))),
        therm=(vy(y_back + px(3.5)), vy(min(y_belt_back + px(7.0), y_back + px(3.5) + px(13.0)))),
    )


# ----------------------------------------------------------------------------- body modules

def body_plating(c, fit):
    """Bolt-on composite plates: a raised slab over the chest and a plate over each shoulder."""
    o = fit_opts(fit, 'Plating', chest=True, caps=(1, -1), chest_w=0.44 if fit in RECON_BUILT else 0.5, chest_lift=2.6,
                 cap_lift=2.6, cap_hi=6.0)
    k = c.k
    form = c.form
    lay = body_layout(c, fit)
    v0, v1 = o.get('chest_v', lay['chest'])
    if o['chest'] and c.dir == 'south':
        w = back_halfwidth(c, fit, lay, v0, v1, o['chest_lift'], o['chest_w'])
        fv = v1 - 2.6 * k / form.H
        poly = [(-w, v0), (w, v0), (w + 0.04, v0 + 0.25 * (v1 - v0)), (w, fv), (w - 0.1, v1), (-w + 0.1, v1), (-w, fv),
                (-w - 0.04, v0 + 0.25 * (v1 - v0))]
        r_ = radius(c, o['chest_lift'])
        p = plate(c, 'chest_plate', poly, 6, r_, rows=(fv,), tone=lambda view, th, v: 2 if v > fv else 1)
        if p is not None:
            vb = v0 + 2.6 * k / form.H
            for s in (1, -1):
                x, y = form.P('south', s * (w - 0.12), vb, r_(vb))
                dot(p, x, y, 1.05 * k)
    elif o['chest'] and c.dir == 'east':
        edge_strip(c, fit, 'chest_plate', 'r', v0, v1, 2.4, 3.2, 6)
    ref = o.get('cap_ref', fit)
    for s in o['caps']:
        if c.dir == 'east':
            if s < 0:
                continue
            # seen from the side: a rounded pauldron over the shoulder, white in front, grey behind
            y0 = shoulder_top(c, ref) + 1.0 * k
            y1 = y0 + lay['cap_h']
            cx, dd = form.d(((y0 + y1) / 2 - form.top) / form.H)
            x0, x1 = cx - 0.5 * dd - 1.0 * k, cx + 0.42 * dd + 1.0 * k
            if not skipped_module(fit, 'CoProcessor', 'east'):
                # keep clear of the co-processor box on the back
                cv0_, cv1_ = lay['cpu']
                u0, u1 = max(cv0_, (y0 - form.top) / form.H - 0.06), min(cv1_, (y1 - form.top) / form.H + 0.06)
                if u0 < u1:
                    x0 = max([x0] + [armor_x(c, fit, vv, 'l', lift=4.6) + 6.0 * k + 5.5 * k for vv in np.linspace(u0, u1, 5)])
                    x1 = max(x1, min(x0 + 9.0 * k, cx + 0.62 * dd))
            ch = 3.0 * k
            ring = G.rounded(G.poly([(x0, y1), (x0, y0 + ch), (x0 + ch, y0), (x1 - ch, y0), (x1, y0 + ch), (x1, y1)]), 2.6 * k)
            p = shape(c, 'cap', ring, 7, 2)
            xm = cx + 0.08 * dd
            p.fill(G.rounded(G.poly([(xm, y1), (xm, y0), (x1 - ch, y0), (x1, y0 + ch), (x1, y1)]), 2.0 * k), tn(c, 1))
            p.fill(G.rect(x0, y1 - 2.4 * k, x1, y1 + 1.0 * k), tn(c, 3))
            continue
        side = screen_side(c.dir, s * PI / 2)
        y0 = shoulder_top(c, ref, side) - 1.0 * k
        # end above the servo housing on the same arm
        y1 = min(y0 + lay['cap_h'], form.y(servo_opts(fit).get('v', lay['servo'])[0]) - 5.5 * k)
        cv0, cv1 = (y0 - form.top) / form.H, (y1 - form.top) / form.H
        lip = cv1 - 2.6 * k / form.H
        off = min(max(edge(fit, c.bt, c.dir, side, cv0, cv1), -3.0), o['cap_hi'])
        lift = off + o['cap_lift'] * min(1.0, lay['sq'])
        a_ = body_ext(c, (cv0 + cv1) / 2)[1]
        ar = a_ + lift * k
        # leave room for the co-processor on the back (north) between the two plates
        clear = math.sin(cpu_halfwidth(c)) * (body_ext(c, (cv0 + cv1) / 2)[1] + 3.0 * k) + 5.5 * k
        wpx = min(max(6.0 * k, 0.4 * a_), ar - clear)
        inner = max(0.35, min(1.2, math.asin(max(0.0, min(0.99, (ar - wpx) / ar)))))
        t0, t1 = (inner, PI / 2 + 0.15) if c.dir == 'south' else (PI / 2 - 0.15, PI - inner)
        poly = A.band(s * t0, s * t1, lambda th: cv0 + 0.025 * (1 - abs(math.sin(th))), cv1, 24)
        if c.dir == 'south':
            def tone(view, th, v, s_=s, lip_=lip):
                return 2 if v > lip_ or s_ * th > 1.25 else 1
            cols = (s * 1.25,)
        else:
            def tone(view, th, v, s_=s, lip_=lip):
                return 3 if v > lip_ or s_ * th < 1.9 else 2
            cols = (s * 1.9,)
        plate(c, f'cap{s}', poly, 7, radius(c, lift), cols=cols, rows=(lip,), wrap=0.4, tone=tone)


SIDE_LO = -1.5   # px: side modules stay on the arm or hip even where a slim armor sits inside the body


def servo_opts(fit):
    return fit_opts(fit, 'BiogelServos', lift=1.4, w=5.0, sides=(1, -1))


def servo_span(c, fit, side, lay):
    """Screen x of the outer and inner edge of the servo housing on one side (south/north)."""
    o = servo_opts(fit)
    v0, v1 = o.get('v', lay['servo'])
    sgn = -1 if side == 'l' else 1
    xo = armor_x(c, fit, (v0 + v1) / 2, side, win=(v1 - v0) / 2, lo=SIDE_LO, hi=7.0, lift=o['lift'])
    return xo, xo - sgn * o['w'] * lay['sq'] * c.k


def back_halfwidth(c, fit, lay, v0, v1, lift, th_max):
    """Largest half-width (theta) for a box on the back between v0 and v1 that keeps clear of the
    servo housings on both arms."""
    sv0, sv1 = servo_opts(fit).get('v', lay['servo'])
    margin = 7.0 * c.k / c.form.H
    if v1 < sv0 - margin or v0 > sv1 + margin:
        return th_max
    cx = body_ext(c, (v0 + v1) / 2)[0]
    room = min(abs(servo_span(c, fit, sd, lay)[1] - cx) for sd in ('l', 'r')) - 5.5 * c.k
    a_ = body_ext(c, (v0 + v1) / 2)[1] + lift * c.k
    return max(0.12, min(th_max, math.asin(max(0.05, min(0.95, room / a_)))))


def body_servos(c, fit):
    """Biogel servo housings over both elbows: a capsule with a dark actuator band."""
    o = servo_opts(fit)
    k = c.k
    form = c.form
    lay = body_layout(c, fit)
    v0, v1 = o.get('v', lay['servo'])
    for s in o['sides']:
        if c.dir == 'east':
            if s < 0:
                continue
            r_ = radius(c, 2.0)
            x, y0 = form.P('east', 1.62, v0, r_(v0))
            _, y1 = form.P('east', 1.62, v1, r_(v1))
            hw = 3.3 * k * lay['sq']
            p = shape(c, 'servo', G.rounded(G.rect(x - hw, y0, x + hw, y1), min(3.0 * k, hw)), 7, 2)
            p.fill(G.rounded(G.rect(x - hw, y0, x - hw + 2.2 * k, y1), 1.0 * k), tn(c, 1))
            ym = (y0 + y1) / 2
            R = min(3.0 * k, hw - 0.6 * k)
            dot(p, x, ym, R)
            dot(p, x, ym, R * 0.42, tone=tn(c, 1))
            continue
        side = screen_side(c.dir, s * PI / 2)
        sgn = -1 if side == 'l' else 1
        y0, y1 = form.y(v0), form.y(v1)
        xo, xi = servo_span(c, fit, side, lay)
        p = shape(c, f'servo{s}', G.rounded(G.rect(min(xo, xi), y0, max(xo, xi), y1), min(2.3 * k, abs(xo - xi) / 2)), 7, face(c))
        xf = xo - sgn * 1.6 * k
        p.fill(G.rect(min(xo, xf), y0, max(xo, xf), y1), tn(c, face(c) + 1))
        ym = (y0 + y1) / 2
        p.fill(G.rect(min(xo, xi), ym - 1.4 * k, max(xo, xi), ym + 1.4 * k), 'undersuit.base')


def body_trauma(c, fit):
    """Trauma response unit clipped over the belt buckle, with an engraved cross."""
    o = fit_opts(fit, 'TraumaSuite', w=0.3, lift=2.4)
    k = c.k
    form = c.form
    lay = body_layout(c, fit)
    v0, v1 = o.get('v', lay['trauma'])
    if c.dir == 'east':
        edge_strip(c, fit, 'pack', 'r', v0, v1, o['lift'] + 0.6, 3.6, 7, tone_i=1)
        return
    w = o['w']
    fv = v1 - 2.4 * k / form.H
    poly = [(-w, v0 + 0.012), (-w + 0.05, v0), (w - 0.05, v0), (w, v0 + 0.012), (w, fv), (w - 0.07, v1), (-w + 0.07, v1), (-w, fv)]
    r_ = radius(c, o['lift'])
    p = plate(c, 'pack', poly, 7, r_, rows=(fv,), tone=lambda view, th, v: 2 if v > fv else 1)
    if p is None:
        return
    vm = (v0 + fv) / 2
    x, y = form.P('south', 0.0, vm, r_(vm))
    a_ = min(2.8 * k, (form.y(fv) - form.y(v0)) * 0.36)
    p.line([(x - a_, y), (x + a_, y)], 1.6 * k, 'undersuit.base')
    p.line([(x, y - a_), (x, y + a_)], 1.6 * k, 'undersuit.base')


def pivot(c, name, x, y, R, z, tone_i):
    """Octagonal actuator pivot with a dark bearing and a light hub."""
    p = shape(c, name, G.chamfer(G.rect(x - R, y - R, x + R, y + R), R * 0.42), z, tone_i)
    p.fill(G.rect(x - R, y + R * 0.45, x + R, y + R), tn(c, min(3, tone_i + 1)))
    dot(p, x, y - 0.15 * c.k, R * 0.56)
    dot(p, x, y - 0.15 * c.k, R * 0.22, tone=tn(c, tone_i))
    return p


def body_exoframe(c, fit):
    """Load-bearing hip frame: an actuator on each hip and a strut down the outside of each thigh."""
    o = fit_opts(fit, 'Exoframe', lift=1.6, sides=(1, -1), w=3.0)
    k = c.k
    form = c.form
    lay = body_layout(c, fit)
    hv = o.get('hip_v', lay['hip'])
    sv0, sv1 = o.get('strut_v', lay['strut'])
    R = 3.4 * k * lay['sq'] ** 0.5
    w = o['w'] * lay['sq'] ** 0.5
    for s in o['sides']:
        if c.dir == 'east':
            if s < 0:
                continue
            r_ = radius(c, 1.5)
            x, yh = form.P('east', 1.55, hv, r_(hv))
            _, yb = form.P('east', 1.55, sv1, r_(sv1))
            yb = min(yb, 128.0 * k - 5.0 * k)       # keep the outline on the canvas (hulk)
            st = shape(c, 'strut', G.rounded(G.rect(x - 1.8 * k, yh, x + 1.8 * k, yb), 0.9 * k), 6, 2)
            st.fill(G.rect(x - 1.8 * k, yh, x - 0.5 * k, yb), tn(c, 1))
            pivot(c, 'hip', x, yh, R + 0.4 * k, 7, 1)
            continue
        side = screen_side(c.dir, s * PI / 2)
        sgn = -1 if side == 'l' else 1
        outer, inner = [], []
        for v in np.linspace(sv0, sv1, 6):
            x = armor_x(c, fit, v, side, win=0.025, lo=SIDE_LO, hi=6.0, lift=o['lift'])
            outer.append((x, form.y(v)))
            inner.append((x - sgn * w * k, form.y(v)))
        st = shape(c, f'strut{s}', G.chamfer(G.poly(outer + inner[::-1]), 0.8 * k), 6, face(c))
        st.fill(G.poly(outer + [(x - sgn * 1.2 * k, y) for x, y in outer[::-1]]), tn(c, face(c) + 1))
        xh = armor_x(c, fit, hv, side, win=0.04, lo=SIDE_LO, hi=6.0, lift=o['lift'] + 0.4) - sgn * R
        pivot(c, f'hip{s}', xh, form.y(hv), R, 7, face(c))


def cpu_halfwidth(c):
    """Half-width (theta) of the co-processor box, narrower on slim bodies."""
    return min(0.32, 7.0 * c.k / max(body_ext(c, 0.3)[1], 1.0))


def body_coprocessor(c, fit):
    """Processing core on the upper back: a raised box with a dark heat-sink panel."""
    o = fit_opts(fit, 'CoProcessor', lift=3.0, out=4.6)
    k = c.k
    form = c.form
    lay = body_layout(c, fit)
    v0, v1 = o.get('v', lay['cpu'])
    if c.dir == 'east':
        st, outer, inner = edge_strip(c, fit, 'box', 'l', v0, v1, o['out'], 6.0, 7, tone_i=2)
        xs = [x for x, _ in outer] + [x for x, _ in inner]
        xm = (min(xs) + max(xs)) / 2
        y0, y1 = form.y(v0), form.y(v1)
        st.fill(G.rect(min(xs), y0, min(xs) + 2.0 * k, y1), tn(c, 3))
        st.fill(G.rounded(G.rect(xm - 0.9 * k, y0 + 3.0 * k, xm + 1.3 * k, y1 - 3.0 * k), 0.6 * k), 'undersuit.base')
        return
    w = back_halfwidth(c, fit, lay, v0, v1, o['lift'], o.get('th', cpu_halfwidth(c)))
    r_ = radius(c, o['lift'])
    lv = v1 - 2.4 * k / form.H
    poly = [(PI - w, v0), (PI + w, v0), (PI + w, lv), (PI + w - 0.08, v1), (PI - w + 0.08, v1), (PI - w, lv)]
    p = plate(c, 'box', poly, 7, r_, rows=(lv,), tone=lambda view, th, v: 3 if v > lv else 2)
    if p is None:
        return
    pw = w * 0.6
    pv0, pv1 = v0 + 3.0 * k / form.H, lv - 2.6 * k / form.H
    pr = form.ring('north', [(PI - pw, pv0), (PI + pw, pv0), (PI + pw, pv1), (PI - pw, pv1)], r_)
    if len(pr) >= 3:
        p.fill(G.simplify_ring(pr, 0.6 * k), 'undersuit.base')
        n = max(2, int(round((form.y(pv1) - form.y(pv0)) / (4.2 * k))))
        for i in range(n):
            v = pv0 + (pv1 - pv0) * (i + 0.5) / n
            pts = [form.P('north', t, v, r_(v)) for t in np.linspace(PI - pw + 0.06, PI + pw - 0.06, 6)]
            p.line(pts, 1.1 * k, 'undersuit.light')


def body_thermal(c, fit):
    """Heat exchanger on the lower back: a radiator box with dark vent slats."""
    o = fit_opts(fit, 'ThermalFins', th=0.4, lift=2.6, out=3.6)
    k = c.k
    form = c.form
    lay = body_layout(c, fit)
    v0, v1 = o.get('v', lay['therm'])
    n = max(2, int(round((form.y(v1) - form.y(v0)) / (4.0 * k))))
    if c.dir == 'east':
        st, outer, inner = edge_strip(c, fit, 'radiator', 'l', v0, v1, o['out'], 5.0, 7, tone_i=2)
        xs = [x for x, _ in outer] + [x for x, _ in inner]
        x0, x1 = min(xs), max(xs)
        st.fill(G.rect(x0, form.y(v0), x0 + 1.8 * k, form.y(v1)), tn(c, 3))
        for i in range(n):
            y = form.y(v0 + (v1 - v0) * (i + 0.6) / (n + 0.2))
            st.line([(x0 + 1.0 * k, y), (x1 - 1.4 * k, y)], 1.5 * k, 'undersuit.base')
        return
    w = back_halfwidth(c, fit, lay, v0, v1, o['lift'], o['th'])
    r_ = radius(c, o['lift'])
    poly = [(PI - w + 0.05, v0), (PI + w - 0.05, v0), (PI + w, v0 + 0.02), (PI + w, v1 - 0.02), (PI + w - 0.05, v1),
            (PI - w + 0.05, v1), (PI - w, v1 - 0.02), (PI - w, v0 + 0.02)]
    p = plate(c, 'radiator', poly, 7, r_)
    if p is None:
        return
    for i in range(n):
        v = v0 + (v1 - v0) * (i + 0.6) / (n + 0.2)
        pts = [form.P('north', t, v, r_(v)) for t in np.linspace(PI - w + 0.1, PI + w - 0.1, 8)]
        p.line(pts, 1.6 * k, 'undersuit.base')


BODY_FN = {'Plating': body_plating, 'BiogelServos': body_servos, 'TraumaSuite': body_trauma, 'Exoframe': body_exoframe,
           'CoProcessor': body_coprocessor, 'ThermalFins': body_thermal}


def body_set(module, fit, body_types=None, dirs=None):
    fn = BODY_FN[module]

    def design(c):
        c.scene.occlusion = None
        if skipped(c, fit, module):
            return
        fn(c, fit)
    kw = {'dirs': dirs or BODY_DIRS.get(module, ('south', 'east', 'north'))}
    if body_types:
        kw['body_types'] = body_types
    return armor('spacer', name=f'{module}_{fit}', mats=MATS, mask_roles=(), ground=False, design_fn=design, **kw)


# ----------------------------------------------------------------------------- helmet modules
#
# Positions are (theta, phi) on the head ellipsoid: theta 0 = face, +pi/2 = the pawn's right
# (screen-left from the front), pi = back; phi is latitude (+ up). Side modules are drawn as flat
# shapes against the helmet's measured edge, because seen from the front a side patch would be a
# sliver; front, back and top modules are plates on the head form.

HELMS = {
    'Marine': {},
    'Recon': {
        # the recon antenna is on the right and the ear module on the left: the uplink box is
        # clamped onto the antenna (which does the mast's job) and the sensors sit above the ear
        'TargetingUplink': {'phi': (0.12, 0.46), 'mast': False},
        'SensorArray': {'phi': (0.3, 0.66)},
        'Plating': {'w': 0.44},
        # the recon helmet leaves the back of the head bare below the ears: both sit on its rim
        'CoProcessor': {'w': 0.36, 'phi': (0.12, 0.48)},
        'NeuralLink': {'phi': (-0.38, -0.13), 'w': 0.26},
    },
    'Cataphract': {'Plating': {'w': 0.58}},
    'PrestigeMarine': {
        'TargetingUplink': {'phi': (-0.36, 0.06), 'mast': False},
        'SensorArray': {'phi': (-0.36, 0.06)},
        'StressDampener': {'at': 'back'},
    },
    'PrestigeRecon': {
        'TargetingUplink': {'phi': (-0.4, 0.06), 'mast': False},
        'SensorArray': {'phi': (-0.4, 0.06)},
        'CoProcessor': {'phi': (0.12, 0.48)},
        'NeuralLink': {'phi': (-0.38, -0.13), 'w': 0.26},
    },
    'PrestigeCataphract': {'StressDampener': {'at': 'back'}},
    'Siegebreaker': {
        'TargetingUplink': {'phi': (-0.45, 0.02), 'mast': False},
        'SensorArray': {'phi': (-0.45, 0.02)},
    },
    'RoyalSiegebreaker': {
        # the ram horns fill the sides up to the temples
        'TargetingUplink': {'phi': (0.54, 0.88)},
        'SensorArray': {'phi': (0.54, 0.88)},
        'Plating': {'w': 0.38, 'phi': (0.36, 0.6)},
        'StressDampener': {'east_x': 7.5},
    },
    'Trooper': {
        # open at the bottom: the neural link sits on the helmet's rim
        'CoProcessor': {'phi': (0.06, 0.44)},
        'NeuralLink': {'phi': (-0.5, -0.24), 'w': 0.28},
    },
    'RoyalTrooper': {
        # the antenna is on the right: the uplink moves to the left and the sensors clamp onto the antenna
        'TargetingUplink': {'side': -1},
        'SensorArray': {'side': 1, 'phi': (0.1, 0.44)},
        'Plating': {'phi': (0.74, 1.0), 'w': 0.6},    # above the gold eagle
        'StressDampener': {'at': 'back'},
        'CoProcessor': {'phi': (0.0, 0.36)},
        'NeuralLink': {'phi': (-0.5, -0.24), 'w': 0.28},
    },
}


def helm_opts(fit, module, **defaults):
    defaults.update(HELMS.get(fit, {}).get(module, {}))
    return defaults


def helm_rows(fit, view):
    return PROFILES['helmets'][fit][f'{view}_rows']


def helm_side(fit, view, side, ph0, ph1, lo=0.8, hi=1.3):
    """Radius factor of the helmet's side (or, east, its back 'l' / front 'r') between two
    latitudes, from the per-row measurement."""
    vals = [r[0 if side == 'l' else 1] for p, r in zip(PROFILES['phi'], helm_rows(fit, view))
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


def side_screen(c, s):
    """Screen side ('l'/'r') of the pawn's right (s=1) or left (s=-1) in south/north."""
    return screen_side(c.dir, s * PI / 2)


def helm_plating(c, fit):
    """Brow plate: an extra composite plate bolted across the forehead."""
    o = helm_opts(fit, 'Plating', phi=(0.4, 0.68), w=0.6)
    k = c.k
    hf = c.form
    p0, p1 = o['phi']
    w = o['w']
    if c.dir == 'north':
        return
    if c.dir == 'east':
        # the head form reaches past a helmet's brow in profile: follow the helmet's measured front
        r = helm_side(fit, 'east', 'r', p0, p1, 0.75, 1.3) + 0.12
    else:
        r = helm_side(fit, 'south', 'l', p0, p1, 0.9, 1.25) + 0.08
    poly = [(-w, p0), (w, p0), (w - 0.04, p1), (-w + 0.04, p1)]
    lip = p0 + 0.07
    if c.dir == 'south':
        pl = A.hplate(c, 'brow', poly, 7, r=r, mask=None, fill=tn(c, 1))
        if pl is not None:
            low = hf.ring([(-w, p0), (w, p0), (w, lip), (-w, lip)], r)
            if len(low) >= 3:
                pl.fill(G.simplify_ring(low, 0.5 * k), tn(c, 2))
            for sd in (1, -1):
                x, y = hf.P(sd * (w - 0.16), (p0 + p1) / 2 + 0.06, r)
                dot(pl, x, y, 1.0 * k)
    else:
        # in profile: the plate's edge stands proud of the brow like a brim
        rf = helm_side(fit, 'east', 'r', p0, p1, 0.75, 1.3)
        pts = []
        for ph in np.linspace(p0, p1, 5):
            pts.append((head_edge_x(c, fit, 'r', ph, rf) + 2.6 * k, head_y(c, ph)))
        inner = [(x - 6.0 * k, y) for x, y in pts]
        ring = G.chamfer(G.poly(pts + inner[::-1]), 1.2 * k)
        pl = shape(c, 'brow', ring, 7, 1)
        pl.fill(G.poly([(x - 6.0 * k, y) for x, y in pts] + [(x - 3.6 * k, y) for x, y in pts[::-1]]), tn(c, 2))
        pl.fill(G.rect(min(x for x, _ in inner), pts[0][1] - 1.8 * k, max(x for x, _ in pts), pts[0][1] + 0.5 * k), tn(c, 3))


def side_box(c, fit, name, s, ph0, ph1, w_px, out_px, z, east_theta=1.45):
    """A box on the side of the helmet (pawn's right s=1, left s=-1): in south/north it stands
    against the helmet's edge, in east (pawn's right only) it sits on the side of the head.
    Returns (part, x0, y0, x1, y1, outward sign) or None."""
    k = c.k
    hf = c.form
    pm = (ph0 + ph1) / 2
    if c.dir == 'east':
        if s < 0:
            return None
        x, _ = hf.P(east_theta, pm, 1.0)
        y0, y1 = head_y(c, ph1), head_y(c, ph0)
        hw = w_px * 0.62 * k
        ring = G.chamfer(G.rect(x - hw, y0, x + hw, y1), 1.6 * k)
        p = shape(c, name, ring, z, 2)
        p.fill(G.rect(x - hw, y0, x + hw, y0 + 2.0 * k), tn(c, 1))
        return p, x - hw, y0, x + hw, y1, 1
    side = side_screen(c, s)
    view = c.dir
    r_side = helm_side(fit, view, side, ph0, ph1)
    sgn = -1 if side == 'l' else 1
    xe = head_edge_x(c, fit, side, pm, r_side) + sgn * out_px * k
    xi = xe - sgn * w_px * k
    y0, y1 = head_y(c, ph1), head_y(c, ph0)
    x0, x1 = min(xe, xi), max(xe, xi)
    ring = G.chamfer(G.rect(x0, y0, x1, y1), 1.4 * k)
    p = shape(c, name, ring, z, 1 if c.dir == 'south' else 2)
    xf = xe - sgn * 1.5 * k
    p.fill(G.rect(min(xe, xf), y0, max(xe, xf), y1), tn(c, 2 if c.dir == 'south' else 3))
    return p, x0, y0, x1, y1, sgn


def helm_uplink(c, fit):
    """Targeting uplink: a rangefinder box with a dark lens on the right side of the helmet and a
    short antenna mast."""
    o = helm_opts(fit, 'TargetingUplink', side=1, phi=(0.0, 0.42), mast=True)
    k = c.k
    ph0, ph1 = o['phi']
    # with a mast the box sits behind the ear, so the mast rises behind the crown in profile
    res = side_box(c, fit, 'uplink', o['side'], ph0, ph1, 6.6, 3.0, 8, east_theta=1.85 if o['mast'] else 1.45)
    if res is None:
        return
    p, x0, y0, x1, y1, sgn = res
    ym = (y0 + y1) / 2 + 0.6 * k
    if c.dir == 'south':
        dot(p, (x0 + x1) / 2, ym, 1.9 * k)
        dot(p, (x0 + x1) / 2 - 0.5 * k, ym - 0.5 * k, 0.6 * k, tone=tn(c, 2))
    elif c.dir == 'east':
        # the lens looks forward: a dark slot at the box's front edge
        p.fill(G.rect(x1 - 1.8 * k, ym - 1.6 * k, x1, ym + 1.6 * k), 'undersuit.base')
    if o['mast']:
        xm = x0 + 1.4 * k if c.dir == 'east' else (x0 + x1) / 2 + sgn * 1.0 * k
        shape(c, 'mast', G.rounded(G.rect(xm - 1.1 * k, y0 - 11.0 * k, xm + 1.1 * k, y0 + 1.0 * k), 1.0 * k), 7.5, 1, role='accent')
        shape(c, 'mast_tip', G.rounded(G.rect(xm - 1.9 * k, y0 - 13.5 * k, xm + 1.9 * k, y0 - 9.5 * k), 1.2 * k), 7.6,
              1 if c.dir != 'north' else 2)


def helm_sensor(c, fit):
    """Multispectral sensor array: a pod on the left side of the helmet with a stack of lenses
    looking forward (it replaces the visor display)."""
    o = helm_opts(fit, 'SensorArray', side=-1, phi=(-0.04, 0.42))
    k = c.k
    ph0, ph1 = o['phi']
    res = side_box(c, fit, 'sensor', o['side'], ph0, ph1, 5.6, 2.6, 8)
    if res is None:
        return
    p, x0, y0, x1, y1, sgn = res
    xm = (x0 + x1) / 2
    if c.dir == 'south':
        n = 2 if (y1 - y0) < 11 * k else 3
        for i in range(n):
            y = y0 + (y1 - y0) * (i + 0.5) / n
            dot(p, xm, y, 1.45 * k)
    elif c.dir == 'east':
        p.fill(G.rect(x1 - 1.8 * k, y0 + 2.2 * k, x1, y1 - 1.6 * k), 'undersuit.base')
    else:
        p.line([(xm, y0 + 2.0 * k), (xm, y1 - 2.0 * k)], 1.0 * k, 'undersuit.base')


def helm_coprocessor(c, fit):
    """Processing core on the back of the helmet: a box with a dark heat-sink panel."""
    o = helm_opts(fit, 'CoProcessor', phi=(-0.06, 0.36), w=0.42, out=3.2)
    k = c.k
    hf = c.form
    p0, p1 = o['phi']
    w = o['w']
    if c.dir == 'south':
        return
    if c.dir == 'east':
        r_back = helm_side(fit, 'east', 'l', p0, p1, 0.8, 1.25)
        y0, y1 = head_y(c, p1), head_y(c, p0)
        xo = head_edge_x(c, fit, 'l', (p0 + p1) / 2, r_back) - o['out'] * k
        xi = xo + 5.6 * k
        p = shape(c, 'box', G.chamfer(G.rect(xo, y0, xi, y1), 1.4 * k), 7, 2)
        p.fill(G.rect(xo, y0, xo + 1.6 * k, y1), tn(c, 3))
        p.fill(G.rect((xo + xi) / 2 - 0.6 * k, y0 + 2.2 * k, (xo + xi) / 2 + 1.2 * k, y1 - 2.2 * k), 'undersuit.base')
        return
    r = helm_side(fit, 'east', 'l', p0, p1, 0.85, 1.25) + 0.12
    poly = [(PI - w, p0), (PI + w, p0), (PI + w - 0.04, p1), (PI - w + 0.04, p1)]
    p = A.hplate(c, 'box', poly, 7, r=r, mask=None, fill=tn(c, 2))
    if p is None:
        return
    pw = w * 0.58
    q0, q1 = p0 + 0.1, p1 - 0.1
    pr = hf.ring([(PI - pw, q0), (PI + pw, q0), (PI + pw, q1), (PI - pw, q1)], r)
    if len(pr) >= 3:
        p.fill(G.simplify_ring(pr, 0.5 * k), 'undersuit.base')
        for i in range(2):
            ph = q0 + (q1 - q0) * (i + 0.5) / 2
            pts = [hf.P(t, ph, r) for t in np.linspace(PI - pw + 0.06, PI + pw - 0.06, 6)]
            p.line(pts, 1.0 * k, 'undersuit.light')
    low = hf.ring([(PI - w, p0), (PI + w, p0), (PI + w, p0 + 0.08), (PI - w, p0 + 0.08)], r)
    if len(low) >= 3:
        p.fill(G.simplify_ring(low, 0.5 * k), tn(c, 3))


def helm_neural(c, fit):
    """Neural link: a spinal interface port at the nape of the helmet with two dark sockets."""
    o = helm_opts(fit, 'NeuralLink', phi=(-0.95, -0.5), w=0.3)
    k = c.k
    hf = c.form
    p0, p1 = o['phi']
    w = o['w']
    if c.dir == 'south':
        return
    if c.dir == 'east':
        r_back = helm_side(fit, 'east', 'l', p0, p1, 0.6, 1.3)
        y0, y1 = head_y(c, p1), head_y(c, p0)
        xo = head_edge_x(c, fit, 'l', (p0 + p1) / 2, r_back) + 1.8 * k     # inside the helmet's outline
        p = shape(c, 'port', G.chamfer(G.rect(xo, y0, xo + 5.0 * k, y1), 1.2 * k), 7, 2)
        dot(p, xo + 2.4 * k, (y0 + y1) / 2, 1.3 * k)
        p.fill(G.rect(xo, y1 - 1.6 * k, xo + 5.0 * k, y1), tn(c, 3))
        return
    r = 1.08
    poly = [(PI - w, p0), (PI + w, p0), (PI + w + 0.04, p1), (PI - w - 0.04, p1)]
    p = A.hplate(c, 'port', poly, 7, r=r, mask=None, fill=tn(c, 2))
    if p is None:
        return
    for i in range(2):
        ph = p0 + (p1 - p0) * (0.3 + 0.4 * i)
        x, y = hf.P(PI, ph, r)
        p.fill(G.chamfer(G.rect(x - 2.6 * k, y - 1.1 * k, x + 2.6 * k, y + 1.1 * k), 0.5 * k), 'undersuit.base')


def helm_dampener(c, fit):
    """Neural stress dampener: a flat stimulator node on the crown (or, on crested helmets, on the
    back of the dome) with a dark emitter ring."""
    o = helm_opts(fit, 'StressDampener', at='crown')
    k = c.k
    hf = c.form
    if o['at'] == 'back':
        if c.dir == 'south':
            return
        if c.dir == 'east':
            ph = 0.86
            r_back = helm_side(fit, 'east', 'l', 0.7, 1.0, 0.8, 1.3)
            x = head_edge_x(c, fit, 'l', ph, r_back) + 1.0 * k
            y = head_y(c, ph)
            p = shape(c, 'node', G.rotate(G.chamfer(G.rect(x - 2.2 * k, y - 4.2 * k, x + 2.2 * k, y + 4.2 * k), 1.4 * k), 35, x, y), 8, 2)
            dot(p, x, y, 1.4 * k)
            return
        poly = [(PI - 0.36, 0.62), (PI + 0.36, 0.62), (PI + 0.3, 0.92), (PI - 0.3, 0.92)]
        p = A.hplate(c, 'node', poly, 8, r=1.14, mask=None, fill=tn(c, 2))
        if p is not None:
            x, y = hf.P(PI, 0.77, 1.14)
            dot(p, x, y, 2.0 * k, 1.4 * k)
            dot(p, x, y, 0.8 * k, 0.6 * k, tone=tn(c, 1))
        return
    top = PROFILES['helmets'][fit][c.dir]['top']
    yt = hf.cy - hf.ry * 0.92 * min(top, 1.35) + 2.0 * k
    hw = 5.2 * k
    x = hf.cx + (o.get('east_x', 4.5) * k if c.dir == 'east' else 0.0)
    ring = G.rounded(G.poly([(x - hw, yt + 2.2 * k), (x - hw + 1.2 * k, yt - 2.4 * k), (x + hw - 1.2 * k, yt - 2.4 * k), (x + hw, yt + 2.2 * k)]),
                     1.4 * k)
    p = shape(c, 'node', ring, 8, 1 if c.dir != 'north' else 2)
    p.fill(G.rect(x - hw, yt + 0.4 * k, x + hw, yt + 2.2 * k), tn(c, 2 if c.dir != 'north' else 3))
    p.fill(G.rect(x - hw + 2.4 * k, yt - 1.2 * k, x + hw - 2.4 * k, yt + 0.2 * k), 'undersuit.base')


HELMET_FN = {'Plating': helm_plating, 'TargetingUplink': helm_uplink, 'SensorArray': helm_sensor, 'CoProcessor': helm_coprocessor,
             'NeuralLink': helm_neural, 'StressDampener': helm_dampener}


def helmet_set(module, fit, dirs=None):
    fn = HELMET_FN[module]

    def design(c):
        c.scene.occlusion = None
        fn(c, fit)
    return helmet('spacer', name=f'{module}_{fit}', mats=MATS, mask_roles=(), ground=False, design_fn=design,
                  dirs=dirs or HELMET_DIRS.get(module, ('south', 'east', 'north')))


def build_helmets(spec):
    return [helmet_set(m, f) for f in HELMET_FITS for m in HELMET_MODULES]


SPEC = {
    'name': 'MPA_ModuleArt',
    'output': {'dir': 'output/MPA_ModuleArt', 'tex_root': 'ModularPowerArmor/Worn/Body', 'mask': False, 'svg': False},
    'items': [{'name': 'MPA_HelmetModuleArt', '_build': build_helmets, 'output': {'tex_root': 'ModularPowerArmor/Worn/Head'}}],
}


def build(spec):
    return [body_set(m, f) for f in BODY_FITS for m in BODY_MODULES]
