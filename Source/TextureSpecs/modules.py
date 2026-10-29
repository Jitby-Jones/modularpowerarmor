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
the places never overlap, so any combination of modules can be installed at once (uranium
composite plating replaces additional plating, so the two share a place):

    body    chest and shoulders (plating), elbows (servos), belt (subpersona), hips and outer thighs
            (exoframe), front of the thighs (rigidity matrix), upper back (regenerator canisters
            either side of the second heart), lower back (thermal regulator), back of the legs
            (longjump hydraulics)
    helmet  brow (plating), crown (stress dampener), right side (targeting uplink over the sensor
            array), left side (second mind over the subpersona), back (regenerator canisters),
            nape (neural link)

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
BODY_MODULES = ['Plating', 'UraniumPlating', 'BiogelServos', 'Regenerators', 'Exoframe', 'Subpersona', 'ThermalFins',
                'RigidityMatrix', 'SecondHeart', 'LongjumpHydraulics']
HELMET_MODULES = ['Plating', 'UraniumPlating', 'TargetingUplink', 'SensorArray', 'Subpersona', 'NeuralLink',
                  'StressDampener', 'Regenerators', 'SecondMind']
# Modules that can't be installed together share their place on the armor.
EXCLUSIVE = (('Plating', 'UraniumPlating'),)

# Views a module never shows in; the mod hides those facings with visibleFacing instead of
# loading empty textures.
BODY_DIRS = {'Regenerators': ('east', 'north'), 'Subpersona': ('south', 'east'), 'ThermalFins': ('east', 'north'),
             'RigidityMatrix': ('south', 'east'), 'SecondHeart': ('north',), 'LongjumpHydraulics': ('east', 'north')}
HELMET_DIRS = {'Plating': ('south', 'east'), 'UraniumPlating': ('south', 'east'), 'Subpersona': ('south', 'north'),
               'SecondMind': ('south', 'north'), 'NeuralLink': ('east', 'north'), 'Regenerators': ('east', 'north')}

MATS = dict(shell='armor_white', undersuit='undersuit', accent='visor_dark', trim='armor_white', joint='armor_white',
            lens='visor_dark', strap='undersuit', energy='visor_dark')

# Per-armor adjustments. Keys:
#   skip      {module: [dirs]} where the module isn't drawn (it would sit on a feature of the armor)
#   <module>  overrides for that module's options (surface coordinates, offsets in px at 128)
# Shoulder plates only go on plain shoulders: wings, gold trim, pauldrons and the grenadier's
# launcher stay visible. Armors with something on the upper back (launcher, jump pack, rods,
# thrusters, horns) show the regenerator canisters from behind only.
FITS = {
    'Marine': {},
    'Recon': {},
    # the cataphract helmet's nape reaches down over the back of the shoulder plate in profile
    'Cataphract': {'Plating': {'cap_back': 0.3}, 'skip': {'Regenerators': ('east',)}},
    'Grenadier': {'Plating': {'caps': (1,)}, 'skip': {'Regenerators': ('east',)}},
    'Locust': {'Plating': {'caps': ()}, 'skip': {'Regenerators': ('east',)}},
    'Phoenix': {'Plating': {'caps': ()}, 'skip': {'Regenerators': ('east',)}},
    'PrestigeMarine': {'Plating': {'caps': ()}},
    'PrestigeRecon': {'Plating': {'caps': ()}},
    'PrestigeCataphract': {'Plating': {'caps': ()}, 'skip': {'Regenerators': ('east',)}},
    'Siegebreaker': {'Plating': {'caps': ()}, 'skip': {'Regenerators': ('east',)}},
    'RoyalSiegebreaker': {'Plating': {'caps': ()}, 'skip': {'Regenerators': ('east',)}},
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
    y_sub = y_belt + px(2.5) * min(1.0, sh)
    y_therm = min(y_belt_back + px(7.0), y_back + px(3.5) + px(13.0))
    y_leg = f.bot - 1.5 * k          # down to the feet: below the exoframe's struts the legs are free
    return dict(
        sv=sv, sh=sh, sq=math.sqrt(max(sh, 0.3)),
        cap_h=min(max(0.62 * f.a(0.1)[1], 9.0 * k), 16.0 * k),
        chest=(vy(y_chest - px(18.0)), vy(y_chest - px(8.0))),
        servo=(vy(y_elbow - px(15.0)), vy(y_elbow - px(3.5))),
        sub=(vy(y_chest - px(0.5)), vy(y_sub)),
        hip=vy(y_belt + px(5.5) + max(0.0, 1.0 - sh) * 10.0 * k),
        strut=(vy(y_belt + px(3.0)), vy(y_tasset - 1.0 * k)),
        regen=(vy(f.top + px(8.0)), vy(y_back - px(3.0))),
        therm=(vy(y_back + px(3.5)), vy(y_therm)),
        # the legs below the belt module (front) and below the radiator (back)
        legs_front=(vy(y_sub + 5.5 * k), vy(y_leg)),
        legs_back=(vy(y_therm + 5.0 * k), vy(y_leg)),
    )


# ----------------------------------------------------------------------------- body modules

def body_plating(c, fit):
    """Bolt-on composite plates: a raised slab over the chest and a plate over each shoulder."""
    plates(c, fit, heavy=False)


def body_uranium(c, fit):
    """Uranium composite plating: heavier plates in the same places as additional plating (the
    two can't be installed together). The chest slab is built from three blocks with a raised
    centre, and each shoulder plate is two layers with a dark seam between them."""
    plates(c, fit, heavy=True)


def plates(c, fit, heavy):
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
        if heavy:
            third = w / 3.0
            p = plate(c, 'chest_plate', poly, 6, r_, cols=(-third, third), rows=(fv,),
                      tone=lambda view, th, v: 3 if v > fv else (1 if abs(th) < third else 2))
        else:
            p = plate(c, 'chest_plate', poly, 6, r_, rows=(fv,), tone=lambda view, th, v: 2 if v > fv else 1)
        if p is not None:
            vb = v0 + 2.6 * k / form.H
            if heavy:
                for s in (1, -1):
                    A.sline(c, p, [(s * third, v0 + 0.01), (s * third, fv)], r=r_((v0 + v1) / 2), width=1.1, tone='undersuit.base')
                    x, y = form.P('south', s * (w - third / 2), vb + 0.3 * (fv - vb), r_(vb))
                    dot(p, x, y, 1.05 * k)
            else:
                for s in (1, -1):
                    x, y = form.P('south', s * (w - 0.12), vb, r_(vb))
                    dot(p, x, y, 1.05 * k)
    elif o['chest'] and c.dir == 'east':
        st, outer, inner = edge_strip(c, fit, 'chest_plate', 'r', v0, v1, 2.4, 3.2, 6)
        if heavy:
            ys = [y for _, y in outer]
            xs = [x for x, _ in outer] + [x for x, _ in inner]
            ym = (min(ys) + max(ys)) / 2
            st.line([(min(xs) + 0.6 * k, ym), (max(xs) - 0.6 * k, ym)], 1.1 * k, 'undersuit.base')
            st.fill(G.rect(min(xs), max(ys) - 2.2 * k, max(xs), max(ys) + 0.5 * k), tn(c, 3))
    ref = o.get('cap_ref', fit)
    for s in o['caps']:
        if c.dir == 'east':
            if s < 0:
                continue
            # seen from the side: a rounded pauldron over the shoulder, white in front, grey behind
            y0 = shoulder_top(c, ref) + 1.0 * k
            y1 = y0 + lay['cap_h']
            cx, dd = form.d(((y0 + y1) / 2 - form.top) / form.H)
            x0, x1 = cx - o.get('cap_back', 0.5) * dd - 1.0 * k, cx + 0.42 * dd + 1.0 * k
            if not skipped_module(fit, 'Regenerators', 'east'):
                # keep clear of the regenerator canisters on the back
                bx0, by0, bx1, by1 = regen_east_bbox(c, fit, lay)
                if by0 - 5.5 * k < y1 and by1 + 5.5 * k > y0:
                    x0 = max(x0, bx1 + 5.5 * k)
                    x1 = max(x1, min(x0 + 9.0 * k, cx + 0.62 * dd))
            ch = 3.0 * k
            ring = G.rounded(G.poly([(x0, y1), (x0, y0 + ch), (x0 + ch, y0), (x1 - ch, y0), (x1, y0 + ch), (x1, y1)]), 2.6 * k)
            p = shape(c, 'cap', ring, 7, 2)
            xm = cx + 0.08 * dd
            p.fill(G.rounded(G.poly([(xm, y1), (xm, y0), (x1 - ch, y0), (x1, y0 + ch), (x1, y1)]), 2.0 * k), tn(c, 1))
            p.fill(G.rect(x0, y1 - 2.4 * k, x1, y1 + 1.0 * k), tn(c, 3))
            if heavy:
                yh = y0 + 0.45 * (y1 - y0)
                p.line([(x0 + 0.5 * k, yh), (x1 - 0.5 * k, yh)], 1.2 * k, 'undersuit.base')
                dot(p, xm + 0.5 * (x1 - xm), y0 + 0.24 * (y1 - y0), 0.95 * k)
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
        wpx = min(max(6.0 * k, 0.4 * a_), ar)
        inner = max(0.35, min(1.2, math.asin(max(0.0, min(0.99, (ar - wpx) / ar)))))
        if c.dir == 'north':
            # leave room for the regenerator canisters (and second heart) on the upper back, at
            # every height of the plate
            cl = regen_cluster(c, fit, lay)
            if cl['y0'] < y1 + 5.5 * k:
                r_cap = radius(c, lift)
                reach = min(body_ext(c, v)[1] * r_cap(v) for v in np.linspace(cv0, cv1, 7))
                inner = max(inner, math.asin(min(0.99, (cl['half'] + 5.5 * k) / max(reach, 1.0))))
        t0, t1 = (inner, PI / 2 + 0.15) if c.dir == 'south' else (PI / 2 - 0.15, PI - inner)
        poly = A.band(s * t0, s * t1, lambda th: cv0 + 0.025 * (1 - abs(math.sin(th))), cv1, 24)
        mid = cv0 + 0.48 * (lip - cv0)
        if c.dir == 'south':
            def tone(view, th, v, s_=s, lip_=lip):
                return 2 if v > lip_ or s_ * th > 1.25 else 1
            cols = (s * 1.25,)
        else:
            def tone(view, th, v, s_=s, lip_=lip):
                return 3 if v > lip_ or s_ * th < 1.9 else 2
            cols = (s * 1.9,)
        r_ = radius(c, lift)
        p = plate(c, f'cap{s}', poly, 7, r_, cols=cols, rows=(lip,) if not heavy else (mid, lip), wrap=0.4, tone=tone)
        if heavy and p is not None:
            A.sline(c, p, [(s * th, mid) for th in np.linspace(t0 + 0.05, t1 - 0.05, 8)], r=r_(mid), width=1.2,
                    tone='undersuit.base')


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


def body_subpersona(c, fit):
    """Auxiliary subpersona clipped over the belt buckle: a processor housing with its subcore
    cartridges slotted in side by side."""
    o = fit_opts(fit, 'Subpersona', w=0.3, lift=2.4)
    k = c.k
    form = c.form
    lay = body_layout(c, fit)
    v0, v1 = o.get('v', lay['sub'])
    if c.dir == 'east':
        st, outer, inner = edge_strip(c, fit, 'housing', 'r', v0, v1, o['lift'] + 0.6, 3.6, 7, tone_i=1)
        # the cartridges' ends, seen edge-on
        xs = [x for x, _ in outer] + [x for x, _ in inner]
        x0, x1 = min(xs), max(xs)
        y0, y1 = form.y(v0), form.y(v1)
        st.fill(G.rect(x1 - 1.4 * k, y0, x1, y1), tn(c, 2))
        st.line([(x0 + 1.0 * k, (y0 + y1) / 2), (x1 - 1.8 * k, (y0 + y1) / 2)], 1.4 * k, 'undersuit.base')
        return
    w = o['w']
    fv = v1 - 2.4 * k / form.H
    poly = [(-w, v0 + 0.012), (-w + 0.05, v0), (w - 0.05, v0), (w, v0 + 0.012), (w, fv), (w - 0.07, v1), (-w + 0.07, v1), (-w, fv)]
    r_ = radius(c, o['lift'])
    p = plate(c, 'housing', poly, 7, r_, rows=(fv,), tone=lambda view, th, v: 2 if v > fv else 1)
    if p is None:
        return
    # dark cartridge slots across the face, each with a light chip edge showing
    xl, _ = form.P('south', w - 0.06, (v0 + fv) / 2, r_((v0 + fv) / 2))
    xr, _ = form.P('south', -w + 0.06, (v0 + fv) / 2, r_((v0 + fv) / 2))
    ya, yb = form.y(v0) + 2.0 * k, form.y(fv) - 1.2 * k
    span = xr - xl
    n = 3 if span >= 11.0 * k else 2
    sw = min(2.4 * k, span / n - 1.6 * k)
    for i in range(n):
        x = xl + span * (i + 0.5) / n
        p.fill(G.rounded(G.rect(x - sw / 2, ya, x + sw / 2, yb), 0.5 * k), 'undersuit.base')
        p.fill(G.rect(x - sw / 2, ya, x + sw / 2, ya + 1.0 * k), 'undersuit.light')


def pivot(c, name, x, y, R, z, tone_i):
    """Octagonal actuator pivot with a dark bearing and a light hub."""
    p = shape(c, name, G.chamfer(G.rect(x - R, y - R, x + R, y + R), R * 0.42), z, tone_i)
    p.fill(G.rect(x - R, y + R * 0.45, x + R, y + R), tn(c, min(3, tone_i + 1)))
    dot(p, x, y - 0.15 * c.k, R * 0.56)
    dot(p, x, y - 0.15 * c.k, R * 0.22, tone=tn(c, tone_i))
    return p


def exo_geom(c, fit, lay=None):
    """Where the exoframe goes in this view: strut rings and (x, y, R) of the hip pivots. Other
    leg modules keep clear of these whether or not an exoframe is installed."""
    o = fit_opts(fit, 'Exoframe', lift=1.6, sides=(1, -1), w=3.0)
    k = c.k
    form = c.form
    lay = lay or body_layout(c, fit)
    hv = o.get('hip_v', lay['hip'])
    sv0, sv1 = o.get('strut_v', lay['strut'])
    R = 3.4 * k * lay['sq'] ** 0.5
    w = o['w'] * lay['sq'] ** 0.5
    struts, pivots = [], []
    for s in o['sides']:
        if c.dir == 'east':
            if s < 0:
                continue
            r_ = radius(c, 1.5)
            x, yh = form.P('east', 1.55, hv, r_(hv))
            _, yb = form.P('east', 1.55, sv1, r_(sv1))
            yb = min(yb, 128.0 * k - 5.0 * k)       # keep the outline on the canvas (hulk)
            struts.append(dict(s=s, ring=G.rounded(G.rect(x - 1.8 * k, yh, x + 1.8 * k, yb), 0.9 * k), x=x, yh=yh, yb=yb))
            pivots.append(dict(s=s, x=x, y=yh, R=R + 0.4 * k))
            continue
        side = screen_side(c.dir, s * PI / 2)
        sgn = -1 if side == 'l' else 1
        outer, inner = [], []
        for v in np.linspace(sv0, sv1, 6):
            x = armor_x(c, fit, v, side, win=0.025, lo=SIDE_LO, hi=6.0, lift=o['lift'])
            outer.append((x, form.y(v)))
            inner.append((x - sgn * w * k, form.y(v)))
        struts.append(dict(s=s, sgn=sgn, outer=outer, inner=inner, ring=G.chamfer(G.poly(outer + inner[::-1]), 0.8 * k)))
        xh = armor_x(c, fit, hv, side, win=0.04, lo=SIDE_LO, hi=6.0, lift=o['lift'] + 0.4) - sgn * R
        pivots.append(dict(s=s, x=xh, y=form.y(hv), R=R))
    return dict(struts=struts, pivots=pivots)


def body_exoframe(c, fit):
    """Load-bearing hip frame: an actuator on each hip and a strut down the outside of each thigh."""
    k = c.k
    g = exo_geom(c, fit)
    for st_, pv in zip(g['struts'], g['pivots']):
        s = st_['s']
        if c.dir == 'east':
            x, yh, yb = st_['x'], st_['yh'], st_['yb']
            st = shape(c, 'strut', st_['ring'], 6, 2)
            st.fill(G.rect(x - 1.8 * k, yh, x - 0.5 * k, yb), tn(c, 1))
            pivot(c, 'hip', pv['x'], pv['y'], pv['R'], 7, 1)
            continue
        outer, sgn = st_['outer'], st_['sgn']
        st = shape(c, f'strut{s}', st_['ring'], 6, face(c))
        st.fill(G.poly(outer + [(x - sgn * 1.2 * k, y) for x, y in outer[::-1]]), tn(c, face(c) + 1))
        pivot(c, f'hip{s}', pv['x'], pv['y'], pv['R'], 7, face(c))


def leg_room(c, fit, y, cx, gap=5.4, lay=None, g=None):
    """Half-width (px) around ``cx`` that stays ``gap`` px clear of the exoframe at screen row y."""
    k = c.k
    g = g or exo_geom(c, fit, lay)
    room = 64.0 * k
    for st in g['struts']:
        if c.dir == 'east':
            continue
        # the strut's points within a few rows of y (the clearance is a distance, not a row)
        pts = G.resample(np.asarray(st['ring'], float), 0.5 * k)
        near_pts = pts[np.abs(pts[:, 1] - y) <= 0.75 * gap * k]
        if len(near_pts):
            near = near_pts[:, 0].max() if st['sgn'] < 0 else near_pts[:, 0].min()
            room = min(room, abs(near - cx) - gap * k)
    for pv in g['pivots']:
        if c.dir == 'east':
            continue
        reach = pv['R'] * 1.25        # a chamfered square: its corners reach past R
        if abs(y - pv['y']) < reach + gap * k:
            room = min(room, abs(pv['x'] - cx) - reach - gap * k)
    return room


def leg_slot(c, fit, y0, y1, cx, min_half, lay=None):
    """The rows from y0 down to where the space between the exoframe struts gets narrower than
    ``min_half`` (px each side of cx). Returns (y_bottom, half-width that fits all those rows)."""
    k = c.k
    g = exo_geom(c, fit, lay)
    best, half = None, None
    y = y0
    while y <= y1 + 1e-6:
        r = leg_room(c, fit, y, cx, lay=lay, g=g)
        if r < min_half:
            break
        half = r if half is None else min(half, r)
        best = y
        y += 0.5 * k
    return best, half


def regen_cluster(c, fit, lay=None):
    """The upper back seen from behind: the two regenerator canisters either side of the second
    heart. Where the back is too narrow for all three between the servo housings (thin and female
    bodies), the canisters sit side by side as one twin tank and the heart is left off.
    Returns mode ('wide' or 'twin'), cx, y0/y1 (canister mount and tip), hw (canister half-width),
    hh (heart half-width), xs (canister centres), splay (outward lean at the tip) and half (the
    cluster's half-width)."""
    lay = lay or body_layout(c, fit)
    k = c.k
    f = c.form
    v0, v1 = lay['regen']
    y0, y1 = f.y(v0), f.y(v1)
    cx, a_ = body_ext(c, (v0 + v1) / 2)
    hw = min(max(0.12 * a_, 2.3 * k), 3.4 * k)
    hh = min(max(0.11 * a_, 2.0 * k), 3.2 * k)
    gap = 5.5 * k
    splay = 1.0 * k
    room = min(abs(servo_span(c, fit, sd, lay)[1] - cx) for sd in ('l', 'r')) - gap
    need = hh + gap + 2.0 * hw + splay
    if need <= room:
        dx = hh + gap + hw
        return dict(mode='wide', cx=cx, y0=y0, y1=y1, hw=hw, hh=hh, xs=(cx - dx, cx + dx), splay=splay, half=need)
    hw = max(1.8 * k, min(hw, (room - 0.4 * k) / 2.0))
    dx = hw + 0.2 * k
    return dict(mode='twin', cx=cx, y0=y0, y1=y1, hw=hw, hh=0.0, xs=(cx - dx, cx + dx), splay=0.0, half=dx + hw)


def axis_map(origin, tip):
    """(unit axis, unit normal, length) and a mapper from (along, across) to canvas px."""
    o = np.asarray(origin, float)
    d = np.asarray(tip, float) - o
    L = float(np.hypot(*d))
    u = d / max(L, 1e-6)
    n = np.array([-u[1], u[0]])

    def m(s, t):
        q = o + s * u + t * n
        return float(q[0]), float(q[1])
    return u, n, L, m


def canister(c, name, mount, tip, hw, z, tone_i, glass=True, cap_end=True, collar=True):
    """A cylindrical canister from its mount on the armor to its free end: flat face with a lit
    and a shaded edge, a dark sight glass, a collar at the mount and the end cap facing out."""
    k = c.k
    u, n, L, m = axis_map(mount, tip)
    r = min(hw * 0.75, 1.6 * k)
    body = G.rounded(G.poly([m(0, -hw), m(L, -hw), m(L, hw), m(0, hw)]), r)
    p = shape(c, name, body, z, tone_i)
    lit = 1 if n[0] < 0 else -1        # the across-axis side that shows on the screen's left
    edge_w = min(1.4 * k, hw * 0.45)
    p.fill(G.poly([m(0.6 * k, lit * hw), m(L - 0.6 * k, lit * hw), m(L - 0.6 * k, lit * (hw - edge_w)),
                   m(0.6 * k, lit * (hw - edge_w))]), tn(c, max(0, tone_i - 1)))
    p.fill(G.poly([m(0.6 * k, -lit * hw), m(L - 0.6 * k, -lit * hw), m(L - 0.6 * k, -lit * (hw - edge_w)),
                   m(0.6 * k, -lit * (hw - edge_w))]), tn(c, min(3, tone_i + 1)))
    if collar:
        p.fill(G.poly([m(0, -hw), m(1.6 * k, -hw), m(1.6 * k, hw), m(0, hw)]), tn(c, 3))
    if glass and L > 9.0 * k:
        gw = max(0.6 * k, hw * 0.32)
        p.fill(G.rounded(G.poly([m(0.34 * L, -gw), m(0.66 * L, -gw), m(0.66 * L, gw), m(0.34 * L, gw)]), 0.4 * k),
               'undersuit.base')
        p.fill(G.poly([m(0.4 * L, -gw * 0.2), m(0.5 * L, -gw * 0.2), m(0.5 * L, gw * 0.5), m(0.4 * L, gw * 0.5)]),
               'undersuit.light')
    if cap_end:
        rs = min(hw * 0.5, 2.0 * k)
        sc = L - rs - 0.4 * k
        ring = [m(sc + rs * math.cos(a), hw * 0.92 * math.sin(a)) for a in np.linspace(0, 2 * PI, 20, endpoint=False)]
        p.fill(G.poly(ring), tn(c, max(0, tone_i - 1)))
        nz = [m(sc + rs * 0.45 * math.cos(a), hw * 0.38 * math.sin(a)) for a in np.linspace(0, 2 * PI, 14, endpoint=False)]
        p.fill(G.poly(nz), 'undersuit.base')
    return p


def regen_east(c, fit, lay=None):
    """The canisters seen from the side: (mount, tip, half-width) for the far and the near one.
    They leave the upper back and angle down and away from the body."""
    lay = lay or body_layout(c, fit)
    k = c.k
    f = c.form
    v0, v1 = lay['regen']
    vm = v0 + 0.42 * (v1 - v0)
    sq = lay['sq']
    hw = min(max(2.6 * k * sq ** 0.5, 2.3 * k), 3.4 * k)
    L = min(max(11.0 * k * sq ** 0.5, 9.0 * k), 14.0 * k)
    xb = armor_x(c, fit, vm, 'l', lift=-2.4)
    ang = math.radians(48.0)
    near = ((xb, f.y(vm)), (xb - L * math.sin(ang), f.y(vm) + L * math.cos(ang)), hw)
    far_m = (xb + 1.6 * k, f.y(vm) - 3.6 * k)
    far = (far_m, (far_m[0] - L * math.sin(ang), far_m[1] + L * math.cos(ang)), hw)
    return far, near


def regen_east_bbox(c, fit, lay=None):
    pts = []
    for mount, tip, hw in regen_east(c, fit, lay):
        pts += [(mount[0] - hw, mount[1] - hw), (tip[0] - hw, tip[1] + hw), (mount[0] + hw, mount[1] - hw), (tip[0] + hw, tip[1] + hw)]
    xs, ys = zip(*pts)
    return min(xs), min(ys), max(xs), max(ys)


def body_regen(c, fit):
    """Neuromemetic regenerators: two cylindrical canisters poking out of the upper back and
    angled down, either side of the spine (side by side as a twin tank on narrow backs)."""
    k = c.k
    lay = body_layout(c, fit)
    if c.dir == 'east':
        (fm, ft, fhw), (nm, nt, nhw) = regen_east(c, fit, lay)
        canister(c, 'canister_far', fm, ft, fhw, 6.8, 2, glass=False)
        canister(c, 'canister', nm, nt, nhw, 7, 1)
        return
    cl = regen_cluster(c, fit, lay)
    y0, y1, hw = cl['y0'], cl['y1'], cl['hw']
    if cl['mode'] == 'wide':
        for x, s in zip(cl['xs'], (-1, 1)):
            canister(c, f'canister{s}', (x, y0), (x + s * cl['splay'], y1), hw, 7, face(c))
        return
    # twin tank: one housing holding both canisters, a dark seam between them
    xl, xr = cl['xs']
    ring = G.rounded(G.poly([(xl - hw, y0), (xr + hw, y0), (xr + hw, y1), (xl - hw, y1)]), min(hw * 0.75, 1.6 * k))
    p = shape(c, 'twin_tank', ring, 7, face(c))
    p.fill(G.rect(xl - hw, y0, xr + hw, y0 + 1.6 * k), tn(c, 3))
    for x in (xl, xr):
        p.fill(G.rect(x - hw + 0.5 * k, y0 + 1.6 * k, x - hw + 0.5 * k + min(1.2 * k, hw * 0.45), y1 - 0.6 * k), tn(c, face(c) - 1))
        rs = min(hw * 0.5, 1.8 * k)
        sc = y1 - rs - 0.4 * k
        p.fill(G.ellipse(x, sc, hw * 0.9, rs), tn(c, face(c) - 1))
        p.fill(G.ellipse(x, sc, hw * 0.36, rs * 0.45), 'undersuit.base')
    p.line([(cl['cx'], y0 + 1.6 * k), (cl['cx'], y1 - 0.5 * k)], 1.0 * k, 'undersuit.base')


def body_heart(c, fit):
    """Second heart: a cylindrical pump on the spine between the regenerator canisters, with a
    round window over the pump chamber."""
    k = c.k
    lay = body_layout(c, fit)
    cl = regen_cluster(c, fit, lay)
    if cl['mode'] != 'wide':
        return
    x, hh = cl['cx'], cl['hh']
    y0, y1 = cl['y0'] + 1.0 * k, cl['y1'] - 0.5 * k
    ring = G.rounded(G.rect(x - hh, y0, x + hh, y1), min(hh * 0.8, 2.0 * k))
    p = shape(c, 'pump', ring, 7, face(c))
    p.fill(G.rect(x - hh, y0, x - hh + min(1.2 * k, hh * 0.4), y1), tn(c, face(c) - 1))
    p.fill(G.rect(x + hh - min(1.0 * k, hh * 0.35), y0, x + hh, y1), tn(c, face(c) + 1))
    for y in (y0 + 0.28 * (y1 - y0), y1 - 1.6 * k):
        p.line([(x - hh, y), (x + hh, y)], 1.0 * k, tn(c, 3))
    ym = y0 + 0.62 * (y1 - y0)
    R = min(hh * 0.78, 2.4 * k)
    p.fill(G.circle(x, ym, R), 'undersuit.base')
    p.fill(G.circle(x - 0.25 * R, ym - 0.25 * R, R * 0.38), 'undersuit.light')


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


def leg_x(c, fit, v, side, theta):
    """Screen x of a point on the front or back of one leg (south/north), between the armor's
    centre line and its edge on that side."""
    cx, h = body_ext(c, v)
    return cx + (-1 if side == 'l' else 1) * h * math.sin(theta)


def body_rigidity(c, fit):
    """Rigidity matrix: cross-braced lattice braces down the front of the thighs that lock the
    stance (seen from the side, one over the front of the knee). They fit between the exoframe's
    struts, so on thin legs there may be no room for them from the front."""
    o = fit_opts(fit, 'RigidityMatrix', w=2.6, maxw=5.5, lift=0.8)
    k = c.k
    form = c.form
    lay = body_layout(c, fit)
    v0, v1 = o.get('v', lay['legs_front'])
    y0, y1 = form.y(v0), form.y(v1)
    if c.dir == 'east':
        hw = o['w'] * lay['sq'] ** 0.5 * k
        xr = armor_x(c, fit, (v0 + v1) / 2, 'r', win=(v1 - v0) / 2, lo=SIDE_LO, hi=5.0, lift=o['lift'])
        g = exo_geom(c, fit, lay)
        st, pv = g['struts'][0], g['pivots'][0]
        xl = max(xr - 2 * hw, st['x'] + 1.8 * k + 5.0 * k)
        if y0 < pv['y'] + pv['R'] + 5.0 * k:
            xl = max(xl, pv['x'] + pv['R'] + 5.0 * k)
        if xr - xl >= 3.0 * k and y1 - y0 >= 6.0 * k:
            brace(c, 'brace', xl, y0, xr, y1, 7, 1)
        return
    # start below the belt module's lowest point (its plate stands proud, so it projects lower)
    so = fit_opts(fit, 'Subpersona', lift=2.4)
    sv1 = so.get('v', lay['sub'])[1]
    y0 = max(y0, form.P('south', 0.0, sv1, radius(c, so['lift'])(sv1))[1] + 5.0 * k)
    cx = body_ext(c, (v0 + v1) / 2)[0]
    gap = 1.6 * k
    maxw = o['maxw'] * lay['sq'] ** 0.5 * k
    yb, half = leg_slot(c, fit, y0, y1, cx, gap / 2 + 3.4 * k, lay)
    if yb is not None and yb - y0 >= 6.0 * k:
        wb = min(half - gap / 2, maxw)
        for sgn in (-1, 1):
            xa, xb = cx + sgn * gap / 2, cx + sgn * (gap / 2 + wb)
            brace(c, f'brace{sgn}', min(xa, xb), y0, max(xa, xb), yb, 7, face(c))
        return
    yb, half = leg_slot(c, fit, y0, y1, cx, 2.2 * k, lay)
    if yb is not None and yb - y0 >= 6.0 * k:
        hw = min(half, 3.4 * k)
        brace(c, 'brace', cx - hw, y0, cx + hw, yb, 7, face(c))
        return
    flank_braces(c, fit, lay, so, maxw)


def flank_braces(c, fit, lay, so, maxw):
    """Where the legs are too short or too narrow (fat bodies), the rigidity braces go either
    side of the belt module instead, between it and the exoframe and servos."""
    k = c.k
    form = c.form
    sv0, sv1 = so.get('v', lay['sub'])
    r_ = radius(c, so['lift'])
    ya, yb = form.y(sv0) + 1.0 * k, form.y(sv1)
    cx = body_ext(c, (sv0 + sv1) / 2)[0]
    x_sub = max(abs(form.P('south', so.get('w', 0.3), v, r_(v))[0] - cx) for v in (sv0, (sv0 + sv1) / 2, sv1))
    xa = x_sub + 5.5 * k
    g = exo_geom(c, fit, lay)
    servo_v = servo_opts(fit).get('v', lay['servo'])
    servo_room = min(abs(servo_span(c, fit, sd, lay)[1] - cx) for sd in ('l', 'r')) - 5.5 * k
    outer = None
    for y in np.arange(ya, yb + 0.01, 0.5 * k):
        v = (y - form.top) / form.H
        o = leg_room(c, fit, y, cx, lay=lay, g=g)
        if form.y(servo_v[0]) - 5.5 * k < y < form.y(servo_v[1]) + 5.5 * k:
            o = min(o, servo_room)
        o = min(o, body_ext(c, v)[1] - 1.5 * k)
        outer = o if outer is None else min(outer, o)
    if outer is None or outer - xa < 3.4 * k or yb - ya < 6.0 * k:
        return
    wb = min(outer - xa, maxw)
    for sgn in (-1, 1):
        x0, x1 = cx + sgn * xa, cx + sgn * (xa + wb)
        brace(c, f'brace{sgn}', min(x0, x1), ya, max(x0, x1), yb, 7, face(c))


def brace(c, name, x0, y0, x1, y1, z, tone_i):
    """A lattice brace panel: light rails with dark cross-bracing between them, and a pin at each end."""
    k = c.k
    p = shape(c, name, G.chamfer(G.rect(x0, y0, x1, y1), 1.0 * k), z, tone_i)
    p.fill(G.rect(x1 - min(1.2 * k, (x1 - x0) * 0.25), y0, x1, y1), tn(c, min(3, tone_i + 1)))
    ia, ib = x0 + 1.1 * k, x1 - 1.1 * k
    ya, yb = y0 + 2.0 * k, y1 - 2.0 * k
    n = max(1, int(round((yb - ya) / max(4.5 * k, (ib - ia) * 1.4))))
    h = (yb - ya) / n
    for i in range(n):
        ta, tb = ya + i * h, ya + (i + 1) * h
        p.line([(ia, ta), (ib, tb)], 0.9 * k, 'undersuit.base')
        p.line([(ib, ta), (ia, tb)], 0.9 * k, 'undersuit.base')
    for y in (y0 + 1.0 * k, y1 - 1.0 * k):
        dot(p, (x0 + x1) / 2, y, 0.7 * k, tone=tn(c, 3))


def piston(c, name, top, bot, hw, z, tone_i):
    """Hydraulic piston in one piece: a cylinder at the top and a narrower polished rod below
    it, with a dark seal between them and a pivot pin at each end."""
    k = c.k
    u, n, L, m = axis_map(top, bot)
    split = 0.56 * L
    rw = max(1.0 * k, hw * 0.5)
    ring = G.poly([m(0, -hw), m(split, -hw), m(split, -rw), m(L, -rw), m(L, rw), m(split, rw), m(split, hw), m(0, hw)])
    p = shape(c, name, G.chamfer(ring, min(0.9 * k, rw * 0.6)), z, tone_i)
    lit = 1 if n[0] < 0 else -1
    lw = min(1.1 * k, hw * 0.4)
    p.fill(G.poly([m(0.5 * k, lit * hw), m(split - 1.2 * k, lit * hw), m(split - 1.2 * k, lit * (hw - lw)), m(0.5 * k, lit * (hw - lw))]),
           tn(c, max(0, tone_i - 1)))
    p.fill(G.poly([m(split + 0.4 * k, -rw), m(L - 1.0 * k, -rw), m(L - 1.0 * k, rw), m(split + 0.4 * k, rw)]), tn(c, max(0, tone_i - 1)))
    p.fill(G.poly([m(split - 1.4 * k, -hw), m(split + 0.4 * k, -hw), m(split + 0.4 * k, hw), m(split - 1.4 * k, hw)]), 'undersuit.base')
    for sx in (min(1.6 * k, 0.15 * L), L - min(1.3 * k, 0.12 * L)):
        x, y = m(sx, 0.0)
        dot(p, x, y, min(0.9 * k, rw * 0.7), tone=tn(c, 3))


def body_longjump(c, fit):
    """Longjump hydraulics: a hydraulic piston down the back of each calf, between the
    exoframe's struts (seen from the side, one behind the calf)."""
    o = fit_opts(fit, 'LongjumpHydraulics', w=2.2, lean=0.8)
    k = c.k
    form = c.form
    lay = body_layout(c, fit)
    v0, v1 = o.get('v', lay['legs_back'])
    y0, y1 = form.y(v0), form.y(v1)
    hw = o['w'] * lay['sq'] ** 0.5 * k
    if c.dir == 'east':
        g = exo_geom(c, fit, lay)
        st, pv = g['struts'][0], g['pivots'][0]
        x_lim = st['x'] - 1.8 * k - 5.0 * k
        if y0 < pv['y'] + pv['R'] + 5.0 * k:
            x_lim = min(x_lim, pv['x'] - pv['R'] - 5.0 * k)
        xt = min(armor_x(c, fit, v0, 'l', win=0.03, lo=SIDE_LO, hi=5.0, lift=-hw), x_lim - hw)
        xb = min(armor_x(c, fit, v1, 'l', win=0.03, lo=SIDE_LO, hi=5.0, lift=0.4 * hw), x_lim - hw)
        if y1 - y0 >= 8.0 * k:
            piston(c, 'piston', (xt, y0 + hw), (xb, y1 - 0.5 * k), hw, 7, 1)
        return
    # start below the radiator's lowest point (its plate stands proud, so it projects lower)
    to = fit_opts(fit, 'ThermalFins', lift=2.6)
    tv1 = to.get('v', lay['therm'])[1]
    y0 = max(y0, form.P('north', PI, tv1, radius(c, to['lift'])(tv1))[1] + 5.0 * k)
    cx = body_ext(c, (v0 + v1) / 2)[0]
    gap = 1.8 * k
    yb, half = leg_slot(c, fit, y0, y1, cx, gap / 2 + 2 * hw * 0.85, lay)
    if yb is not None and yb - y0 >= 8.0 * k:
        hw = min(hw, (half - gap / 2) / 2)
        for sgn in (-1, 1):
            x = cx + sgn * (gap / 2 + hw)
            piston(c, f'piston{sgn}', (x, y0 + hw * 0.8), (x, yb - 0.5 * k), hw, 7, face(c))
        return
    # narrow legs: one piston down the middle
    yb, half = leg_slot(c, fit, y0, y1, cx, 1.6 * k, lay)
    if yb is not None and yb - y0 >= 6.0 * k:
        hw = min(hw, half)
        piston(c, 'piston', (cx, y0 + hw * 0.8), (cx, yb - 0.5 * k), hw, 7, face(c))


BODY_FN = {'Plating': body_plating, 'UraniumPlating': body_uranium, 'BiogelServos': body_servos, 'Regenerators': body_regen,
           'Exoframe': body_exoframe, 'Subpersona': body_subpersona, 'ThermalFins': body_thermal,
           'RigidityMatrix': body_rigidity, 'SecondHeart': body_heart, 'LongjumpHydraulics': body_longjump}


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
        # clamped onto the antenna (which does the mast's job)
        'TargetingUplink': {'mast': False},
        'Plating': {'w': 0.44},
        # the recon helmet leaves the back of the head bare below the ears: both sit on its rim
        'Regenerators': {'phi': (0.12, 0.5)},
        'NeuralLink': {'phi': (-0.38, -0.13), 'w': 0.26},
    },
    'Cataphract': {'Plating': {'w': 0.58}},
    'PrestigeMarine': {
        'TargetingUplink': {'mast': False},
        'StressDampener': {'at': 'back'},
    },
    'PrestigeRecon': {
        # the gold fins run down the sides to the cheeks: the boxes are clamped onto them
        'TargetingUplink': {'mast': False},
        'Regenerators': {'phi': (0.12, 0.5)},
        'NeuralLink': {'phi': (-0.38, -0.13), 'w': 0.26},
    },
    'PrestigeCataphract': {'StressDampener': {'at': 'back'}},
    'Siegebreaker': {
        # the uplink and sensors are bolted onto the tall side plates
        'TargetingUplink': {'mast': False, 'east_theta': 1.9},
    },
    'RoyalSiegebreaker': {
        # the ram horns fill the sides from the temples down: the upper boxes go above them and
        # the lower ones are clamped onto the horns' roots
        'TargetingUplink': {'phi': (0.6, 0.95)},
        'SensorArray': {'phi': (0.08, 0.36)},
        'Plating': {'w': 0.38, 'phi': (0.36, 0.6)},
        'StressDampener': {'east_x': 7.5},
    },
    'Trooper': {
        # open at the bottom: the neural link sits on the helmet's rim
        'Regenerators': {'phi': (0.0, 0.44)},
        'NeuralLink': {'phi': (-0.5, -0.24), 'w': 0.28},
    },
    'RoyalTrooper': {
        # the antenna is on the right: the uplink and sensors move to the left
        'TargetingUplink': {'side': -1},
        'Plating': {'phi': (0.74, 1.0), 'w': 0.6},    # above the gold eagle
        'StressDampener': {'at': 'back'},
        'Regenerators': {'phi': (-0.06, 0.36)},
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
    brow(c, fit, heavy=False)


def helm_uranium(c, fit):
    """Uranium composite brow plate: the plating's place on the brow (the two can't be installed
    together), built from three blocks with a raised centre and a heavy dark lip."""
    brow(c, fit, heavy=True)


def brow(c, fit, heavy):
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
    if c.dir == 'south':
        # narrow the plate where a side box sits next to the brow
        for module in SIDE_BOX:
            rect = column_rect(c, fit, module)
            if rect is None or rect[1] > head_y(c, p0) + 6.0 * k or rect[3] < head_y(c, p1) - 6.0 * k:
                continue
            room = min(abs(rect[0] - hf.cx), abs(rect[2] - hf.cx)) - 5.5 * k
            while w > 0.3 and max(abs(hf.P(w, ph, r)[0] - hf.cx) for ph in np.linspace(p0, p1, 5)) > room:
                w -= 0.02
    poly = [(-w, p0), (w, p0), (w - 0.04, p1), (-w + 0.04, p1)]
    lip = p0 + 0.07
    if c.dir == 'south':
        pl = A.hplate(c, 'brow', poly, 7, r=r, mask=None, fill=tn(c, 1))
        if pl is not None:
            if heavy:
                third = w / 3.0
                for sd in (1, -1):
                    side = hf.ring([(sd * third, p0), (sd * w, p0), (sd * (w - 0.04), p1), (sd * third, p1)], r)
                    if len(side) >= 3:
                        pl.fill(G.simplify_ring(side, 0.5 * k), tn(c, 2))
            low = hf.ring([(-w, p0), (w, p0), (w, lip), (-w, lip)], r)
            if len(low) >= 3:
                pl.fill(G.simplify_ring(low, 0.5 * k), tn(c, 3 if heavy else 2))
            if heavy:
                for sd in (1, -1):
                    pts = [hf.P(sd * third, ph, r) for ph in np.linspace(lip, p1 - 0.02, 4)]
                    pl.line(pts, 1.1 * k, 'undersuit.base')
                    x, y = hf.P(sd * (w + third) / 2, (lip + p1) / 2, r)
                    dot(pl, x, y, 0.95 * k)
            else:
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
        if heavy:
            mid = [((x + xi) / 2 + 0.6 * k, y) for (x, y), (xi, _) in zip(pts, inner)]
            pl.line(mid, 1.1 * k, 'undersuit.base')


def side_rect(c, fit, s, ph0, ph1, w_px, out_px, east_theta=1.45):
    """Screen rectangle (x0, y0, x1, y1, outward sign) of a box on the side of the helmet (pawn's
    right s=1, left s=-1): in south/north it stands against the helmet's edge, in east (pawn's
    right only) it sits on the side of the head. None where it doesn't show."""
    k = c.k
    hf = c.form
    pm = (ph0 + ph1) / 2
    y0, y1 = head_y(c, ph1), head_y(c, ph0)
    if c.dir == 'east':
        if s < 0:
            return None
        x, _ = hf.P(east_theta, pm, 1.0)
        hw = w_px * 0.62 * k
        return x - hw, y0, x + hw, y1, 1
    side = side_screen(c, s)
    r_side = helm_side(fit, c.dir, side, ph0, ph1)
    sgn = -1 if side == 'l' else 1
    xe = head_edge_x(c, fit, side, pm, r_side) + sgn * out_px * k
    xi = xe - sgn * w_px * k
    return min(xe, xi), y0, max(xe, xi), y1, sgn


def side_box(c, fit, name, s, ph0, ph1, w_px, out_px, z, east_theta=1.45):
    """Draws a box on the side of the helmet (see side_rect). Returns (part, x0, y0, x1, y1,
    outward sign) or None."""
    k = c.k
    rect = side_rect(c, fit, s, ph0, ph1, w_px, out_px, east_theta)
    if rect is None:
        return None
    x0, y0, x1, y1, sgn = rect
    if c.dir == 'east':
        p = shape(c, name, G.chamfer(G.rect(x0, y0, x1, y1), 1.6 * k), z, 2)
        p.fill(G.rect(x0, y0, x1, y0 + 2.0 * k), tn(c, 1))
        return p, x0, y0, x1, y1, 1
    p = shape(c, name, G.chamfer(G.rect(x0, y0, x1, y1), 1.4 * k), z, 1 if c.dir == 'south' else 2)
    xe = x1 if sgn > 0 else x0
    xf = xe - sgn * 1.5 * k
    p.fill(G.rect(min(xe, xf), y0, max(xe, xf), y1), tn(c, 2 if c.dir == 'south' else 3))
    return p, x0, y0, x1, y1, sgn


# Side columns: the targeting uplink over the sensor array on one side of the helmet (the
# pawn's right unless an armor needs otherwise), the second mind over the subpersona on the
# other. Each column keeps its lower box clear of the shoulder plates under the helmet.
UPPER, LOWER = (0.52, 0.9), (0.04, 0.28)
# (width, how far it stands out of the helmet's edge) in px at 128
SIDE_BOX = {'TargetingUplink': (6.6, 3.0), 'SensorArray': (5.6, 2.6), 'SecondMind': (7.0, 3.0), 'Subpersona': (5.6, 2.6)}


def column(fit, module):
    up = helm_opts(fit, 'TargetingUplink', side=1, phi=UPPER, mast=True)
    up.setdefault('east_theta', 1.85 if up['mast'] else 1.45)
    if module == 'TargetingUplink':
        return up
    if module == 'SensorArray':
        return helm_opts(fit, 'SensorArray', side=up['side'], phi=LOWER, east_theta=up['east_theta'])
    low = helm_opts(fit, 'SensorArray', phi=LOWER)['phi']
    if module == 'SecondMind':
        return helm_opts(fit, 'SecondMind', side=-up['side'], phi=up['phi'])
    return helm_opts(fit, 'Subpersona', side=-up['side'], phi=low)


def column_rect(c, fit, module):
    o = column(fit, module)
    w, out = SIDE_BOX[module]
    return side_rect(c, fit, o['side'], o['phi'][0], o['phi'][1], w, out, o.get('east_theta', 1.45))


def helm_uplink(c, fit):
    """Targeting uplink: a rangefinder box with a dark lens high on the side of the helmet and a
    short antenna mast."""
    o = column(fit, 'TargetingUplink')
    k = c.k
    ph0, ph1 = o['phi']
    # with a mast the box sits behind the ear, so the mast rises behind the crown in profile
    res = side_box(c, fit, 'uplink', o['side'], ph0, ph1, *SIDE_BOX['TargetingUplink'], 8, east_theta=o['east_theta'])
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
        shape(c, 'mast', G.rounded(G.rect(xm - 1.1 * k, y0 - o.get('mast_h', 9.0) * k, xm + 1.1 * k, y0 + 1.0 * k), 1.0 * k), 7.5, 1,
              role='accent')
        shape(c, 'mast_tip', G.rounded(G.rect(xm - 1.9 * k, y0 - (o.get('mast_h', 9.0) + 2.5) * k, xm + 1.9 * k,
                                              y0 - (o.get('mast_h', 9.0) - 1.5) * k), 1.2 * k), 7.6, 1 if c.dir != 'north' else 2)


def helm_sensor(c, fit):
    """Multispectral sensor array: a pod right under the targeting uplink with its lenses
    looking forward."""
    o = column(fit, 'SensorArray')
    k = c.k
    ph0, ph1 = o['phi']
    res = side_box(c, fit, 'sensor', o['side'], ph0, ph1, *SIDE_BOX['SensorArray'], 8, east_theta=o['east_theta'])
    if res is None:
        return
    p, x0, y0, x1, y1, sgn = res
    xm = (x0 + x1) / 2
    if c.dir == 'south':
        n = max(1, min(3, int((y1 - y0) / (4.0 * k))))
        for i in range(n):
            y = y0 + (y1 - y0) * (i + 0.5) / n
            dot(p, xm, y, 1.45 * k)
    elif c.dir == 'east':
        p.fill(G.rect(x1 - 1.8 * k, y0 + 1.6 * k, x1, y1 - 1.2 * k), 'undersuit.base')
    else:
        p.line([(xm, y0 + 1.6 * k), (xm, y1 - 1.6 * k)], 1.0 * k, 'undersuit.base')


def helm_secondmind(c, fit):
    """Second mind: an AI persona core housing high on the side of the helmet, its core showing
    through a round port."""
    o = column(fit, 'SecondMind')
    k = c.k
    ph0, ph1 = o['phi']
    res = side_box(c, fit, 'core', o['side'], ph0, ph1, *SIDE_BOX['SecondMind'], 8)
    if res is None:
        return
    p, x0, y0, x1, y1, sgn = res
    xm, ym = (x0 + x1) / 2 - sgn * 0.4 * k, (y0 + y1) / 2 + 0.4 * k
    R = min(2.4 * k, (x1 - x0) * 0.36, (y1 - y0) * 0.38)
    if c.dir == 'south':
        dot(p, xm, ym, R)
        dot(p, xm, ym, R * 0.55, tone=tn(c, 1))
        dot(p, xm, ym, R * 0.22)
    else:
        p.fill(G.rect(xm - 0.7 * k, y0 + 1.6 * k, xm + 0.7 * k, y1 - 1.6 * k), 'undersuit.base')
        dot(p, xm, ym, R * 0.5, tone=tn(c, 3))


def helm_subpersona(c, fit):
    """Auxiliary subpersona: a small housing under the second mind with its subcore cartridges
    slotted in."""
    o = column(fit, 'Subpersona')
    k = c.k
    ph0, ph1 = o['phi']
    res = side_box(c, fit, 'housing', o['side'], ph0, ph1, *SIDE_BOX['Subpersona'], 8)
    if res is None:
        return
    p, x0, y0, x1, y1, sgn = res
    if c.dir == 'south':
        n = max(1, min(3, int((y1 - y0) / (2.8 * k))))
        for i in range(n):
            y = y0 + (y1 - y0) * (i + 0.5) / n
            p.fill(G.rect(x0 + 1.2 * k, y - 0.6 * k, x1 - 1.2 * k, y + 0.6 * k), 'undersuit.base')
    else:
        xm = (x0 + x1) / 2
        p.line([(xm, y0 + 1.4 * k), (xm, y1 - 1.4 * k)], 1.0 * k, 'undersuit.base')


def helm_regen(c, fit):
    """Neuromemetic regenerators: two small canisters on the back of the helmet, angled up."""
    o = helm_opts(fit, 'Regenerators', phi=(-0.24, 0.3), th=0.3, w=2.2, splay=1.2)
    k = c.k
    hf = c.form
    p0, p1 = o['phi']
    hw = o['w'] * k
    if c.dir == 'south':
        return
    if c.dir == 'east':
        r_back = helm_side(fit, 'east', 'l', p0, p1, 0.8, 1.25)
        pm = p0 + 0.35 * (p1 - p0)
        xb = head_edge_x(c, fit, 'l', pm, r_back) + 2.2 * k
        yb = head_y(c, pm)
        L = o.get('east_len', 10.0) * k
        ang = math.radians(o.get('east_angle', 38.0))
        tip = (xb - L * math.sin(ang), yb - L * math.cos(ang))
        fm = (xb + 1.4 * k, yb + 3.0 * k)
        canister(c, 'canister_far', fm, (fm[0] - L * math.sin(ang), fm[1] - L * math.cos(ang)), hw, 6.8, 2, glass=False)
        canister(c, 'canister', (xb, yb), tip, hw, 7, 1)
        return
    r = helm_side(fit, 'east', 'l', p0, p1, 0.85, 1.25) + 0.06
    for s in (-1, 1):
        th = PI + s * o['th']
        xb, yb = hf.P(th, p0, r)
        xt, yt = hf.P(th, p1, r)
        canister(c, f'canister{s}', (xb, yb), (xt - s * o['splay'] * k, yt), hw, 7, face(c))


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
    x = hf.cx + (o.get('east_x', 8.5) * k if c.dir == 'east' else 0.0)
    ring = G.rounded(G.poly([(x - hw, yt + 2.2 * k), (x - hw + 1.2 * k, yt - 2.4 * k), (x + hw - 1.2 * k, yt - 2.4 * k), (x + hw, yt + 2.2 * k)]),
                     1.4 * k)
    p = shape(c, 'node', ring, 8, 1 if c.dir != 'north' else 2)
    p.fill(G.rect(x - hw, yt + 0.4 * k, x + hw, yt + 2.2 * k), tn(c, 2 if c.dir != 'north' else 3))
    p.fill(G.rect(x - hw + 2.4 * k, yt - 1.2 * k, x + hw - 2.4 * k, yt + 0.2 * k), 'undersuit.base')


HELMET_FN = {'Plating': helm_plating, 'UraniumPlating': helm_uranium, 'TargetingUplink': helm_uplink, 'SensorArray': helm_sensor,
             'Subpersona': helm_subpersona, 'NeuralLink': helm_neural, 'StressDampener': helm_dampener, 'Regenerators': helm_regen,
             'SecondMind': helm_secondmind}


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
