"""Drawing kit for the module art: rwtexturegen parts at 256 px in a combat-hardware style.

Style: after the Dead Man's Switch mod's mechs, vehicles and weapons. Chunky chamfered blocks
with flat cel planes (lit top faces, mid fronts, dark undersides), exposed mechanisms (pistons,
hinge knuckles, hoses, cable looms) and dense small detail: bolts, slot vents, perforations,
stencil marks and tiny lamps.

Colour: shell parts are painted like the armor itself (white faces, #ccc lower faces, near-black
recesses) and masked red, so CutoutComplex dyes them together with the armor. Frames, pistons,
glass, hoses and lamps are unmasked and keep their own colours.

Outlines: the thick black outline vanilla puts around a silhouette is only drawn where a module
sticks out past the armor (estimated from armor_profiles.json, see mpa_fit.footprint). On the
armor, parts are separated by seam lines, so the modules read as part of the armor's
construction instead of stickers on top of it.

All sizes are in px at 128 and scaled by ``k`` (2 at 256 px).
"""
import math

import numpy as np
from PIL import Image

from rwtex import geom as G
from rwtex.materials import M, make
from rwtex.render import BLACK, Dome, Facets, Fill, Line, Part, Scene, _Win, downsample


def _mat(name, base, **kw):
    m = make(name, base, **kw)
    M[name] = m
    return m


# Shell: vanilla power armor faces are #fcfcfc with #ccc side faces.
SHELL = _mat('mpa_shell', '#fcfcfc', light='#ffffff', shade='#cccccc', deep='#9b9b9b', line='#6a6a6a', mask='r')
# Gunmetal frame (untinted).
FRAME = _mat('mpa_frame', '#686c70', light='#8f9398', shade='#4c5054', deep='#313437', line='#1c1e20')
# Darker structural steel for inner frames and housings seen in shadow.
IRON = _mat('mpa_iron', '#4d5054', light='#6d7175', shade='#3a3d40', deep='#26282a', line='#141516')
# Bright machined steel: piston rods, pins, rails.
STEEL = _mat('mpa_steel', '#b4b9bd', light='#e8ebed', shade='#878c90', deep='#5d6165', line='#3b3e41')
# Recess black-grey (vents, sockets, gaps).
DARK = _mat('mpa_dark', '#2a2c2e', light='#44474a', shade='#202224', deep='#141516', line='#0a0a0b')
# Rubber hoses and cable looms.
HOSE = _mat('mpa_hose', '#393c3f', light='#5e6266', shade='#2a2c2e', deep='#1a1b1c', line='#0e0f10')
# Indicator lamps and lens tints: dim military colours, used sparingly (untinted).
AMBER = _mat('mpa_amber', '#c28a32', light='#e2b56a', shade='#8c5f1c', deep='#56390f')
RED = _mat('mpa_red', '#9e3a33', light='#c8665c', shade='#722722', deep='#461613')
GREEN = _mat('mpa_green', '#6f9460', light='#9fbf8e', shade='#4b6a40', deep='#2e4227')
# Biogel: a muted olive translucent gel.
GEL = _mat('mpa_gel', '#74906a', light='#a5bc98', shade='#52684a', deep='#36452f')
# Persona-core glass: a dim steel blue.
CYAN = _mat('mpa_cyan', '#5f8796', light='#99b9c4', shade='#41616c', deep='#283e46')
VIOLET = _mat('mpa_violet', '#5e5a76', light='#8e8aa6', shade='#43405a', deep='#2a283a')
# Lens glass: near black with a faint coloured reflection.
GLASS = _mat('mpa_glass', '#1b2124', light='#4f5f66', shade='#131719', deep='#0a0c0d', line='#050607')
# Olive drab webbing and soft covers.
OD = _mat('mpa_od', '#5b5f45', light='#777b5c', shade='#464934', deep='#2f3123', line='#1b1c14')

SEAM = 1.25      # seam line between parts on the armor (px at 128; vanilla inner lines are ~1.4)
FINE = 0.7       # fine detail lines
LIGHT_DIR = (0.0, -1.0)   # screen direction toward the light (straight above, like vanilla apparel)


# ----------------------------------------------------------------------------- scene and render

def setup(scene, k):
    """Configure an rwtexturegen apparel scene for HD module art."""
    scene.inner = SEAM * k
    scene.occlusion = (1.4 * k, 0.28, 1.0 * k)
    scene.meta['hd'] = True
    return scene


def render(scene, footprint=None):
    """RGBA render with the thick outline clipped to outside ``footprint`` (rings in canvas px).

    Mirrors rwtexturegen's Scene.render_ss, minus the soft glow halo, which a Cutout shader
    can't show."""
    s = scene.ss
    H, W = scene.h * s, scene.w * s
    canvas = np.zeros((H, W, 4), np.float32)
    full = _Win(0, 0, H, W)
    if scene.outline > 0:
        sil = scene.silhouette_mask()
        if footprint:
            sil = sil * (1.0 - scene._fill(footprint, full))
        Scene._over(canvas, full, sil, BLACK)
    order = scene.ordered()
    scene._occl = scene._occlusion_unions(order) if scene.occlusion else None
    for p in order:
        scene._render_part(canvas, p)
    scene._occl = None
    bloom = scene._glow_layer('bloom')
    if bloom is not None:
        a, col = bloom
        inside = canvas[..., 3:4]
        rgbp = canvas[..., :3]
        lit = 1 - (1 - rgbp) * (1 - col * a[..., None] * inside)
        canvas[..., :3] = rgbp * (1 - inside) + lit * inside
    return downsample(canvas, s)


def render_mask(scene):
    return scene.render_mask()


def binarize(img, cut=128):
    """Cutout-style alpha (what the game shows): opaque where alpha >= cut."""
    a = np.array(img.convert('RGBA'))
    a[..., 3] = np.where(a[..., 3] >= cut, 255, 0)
    a[a[..., 3] == 0, :3] = 0
    return Image.fromarray(a, 'RGBA')


# ----------------------------------------------------------------------------- vector helpers

def unit(v):
    v = np.asarray(v, float)
    n = float(np.hypot(v[0], v[1]))
    return v / n if n > 1e-9 else np.array([1.0, 0.0])


def perp(v):
    return np.array([-v[1], v[0]])


def lit_normal(axis):
    """Unit normal of an axis that points toward the light."""
    n = perp(unit(axis))
    if n[0] * LIGHT_DIR[0] + n[1] * LIGHT_DIR[1] < 0 or (abs(n[1]) < 1e-6 and n[0] > 0):
        n = -n
    return n


def quad(p0, p1, hw0, hw1=None):
    """Quad along p0 -> p1 with half widths hw0 at p0 and hw1 at p1."""
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    hw1 = hw0 if hw1 is None else hw1
    n = perp(unit(p1 - p0))
    return G.poly([p0 + n * hw0, p1 + n * hw1, p1 - n * hw1, p0 - n * hw0])


def stroke(path, hw, round_caps=True):
    """Polygon around a polyline (half width ``hw``, a float or one value per point)."""
    P = np.asarray(path, float)
    n = len(P)
    hws = np.full(n, float(hw)) if np.isscalar(hw) else np.asarray(hw, float)
    left, right = [], []
    for i in range(n):
        if i == 0:
            t = P[1] - P[0]
        elif i == n - 1:
            t = P[-1] - P[-2]
        else:
            t = unit(P[i + 1] - P[i]) + unit(P[i] - P[i - 1])
        nm = perp(unit(t))
        if 0 < i < n - 1:
            cosh = max(0.5, float(np.dot(nm, perp(unit(P[i + 1] - P[i])))))
        else:
            cosh = 1.0
        left.append(P[i] + nm * hws[i] / cosh)
        right.append(P[i] - nm * hws[i] / cosh)
    cap0, cap1 = [], []
    if round_caps:
        d0 = unit(P[0] - P[1])
        d1 = unit(P[-1] - P[-2])
        for a in np.linspace(0, math.pi, 7)[1:-1]:
            # around the end points, from right to left (cap1) and left to right (cap0)
            cap1.append(P[-1] + (perp(d1) * -math.cos(a) * -1 + d1 * math.sin(a)) * hws[-1])
            cap0.append(P[0] + (perp(d0) * math.cos(a) * -1 + d0 * math.sin(a)) * hws[0])
    ring = left + cap1 + right[::-1] + cap0
    return G.poly(ring)


def smooth(pts, n=10):
    """Open Catmull-Rom style smoothing of a few control points."""
    P = [np.asarray(p, float) for p in pts]
    if len(P) < 3:
        return np.array(P)
    out = []
    ext = [P[0] * 2 - P[1]] + P + [P[-1] * 2 - P[-2]]
    for i in range(1, len(ext) - 2):
        p0, p1, p2, p3 = ext[i - 1], ext[i], ext[i + 1], ext[i + 2]
        for t in np.linspace(0, 1, n, endpoint=False):
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(P[-1])
    return np.array(out)


def path_len(path):
    P = np.asarray(path, float)
    return float(np.hypot(*np.diff(P, axis=0).T).sum())


def along(path, d):
    """(point, tangent) at arc length d along a polyline."""
    P = np.asarray(path, float)
    acc = 0.0
    for a, b in zip(P[:-1], P[1:]):
        L = float(np.hypot(*(b - a)))
        if acc + L >= d and L > 1e-9:
            t = (d - acc) / L
            return a + (b - a) * t, unit(b - a)
        acc += L
    return P[-1], unit(P[-1] - P[-2])


def offset_path(path, d):
    P = np.asarray(path, float)
    out = []
    for i in range(len(P)):
        if i == 0:
            t = P[1] - P[0]
        elif i == len(P) - 1:
            t = P[-1] - P[-2]
        else:
            t = unit(P[i + 1] - P[i]) + unit(P[i] - P[i - 1])
        out.append(P[i] + perp(unit(t)) * d)
    return np.array(out)


# ----------------------------------------------------------------------------- shading

def cel(k, w=1.1, flat=False):
    """Chamfer facets: lit top edges, base sides, dark bottom edges - hard cel planes."""
    if flat or w <= 0:
        return []
    return [Facets(w * k, ('light', 'base', 'shade', 'deep'), (0.45, -0.3, -0.82), angle=-90.0)]


def dome(k=None):
    return [Dome(('light', 'base', 'shade'), (-0.2, -0.55), 1.3, 1.0)]


# ----------------------------------------------------------------------------- parts

class Kit:
    """Builds module parts into one Ctx (rwtexturegen apparel context)."""

    def __init__(self, c, footprint=None):
        self.c = c
        self.k = c.k
        self.sc = c.scene
        self.view = c.dir
        self.footprint = footprint

    # generic ---------------------------------------------------------------------------------
    def part(self, name, ring, z, mat=SHELL, tone='base', shading=None, outline='auto', silhouette=True, mask='material',
             **kw):
        if isinstance(ring, np.ndarray) and len(ring) < 3:
            return None
        p = Part(name, ring, mat, z=z, outline=outline, silhouette=silhouette, mask=mask,
                 shading=list(shading or []), tone=tone, **kw)
        self.sc.add(p)
        return p

    def block(self, name, ring, z, mat=SHELL, tone='base', bevel=1.1, **kw):
        """A chamfered block with cel facets."""
        return self.part(name, ring, z, mat, tone=tone, shading=cel(self.k, bevel), **kw)

    def flat(self, name, ring, z, mat=SHELL, tone='base', **kw):
        return self.part(name, ring, z, mat, tone=tone, shading=[], **kw)

    # cylinders, pistons, joints ---------------------------------------------------------------
    def cylinder(self, name, p0, p1, r, z, mat=STEEL, caps=False, bands=True, r1=None, outline='auto', **kw):
        """Cylinder seen side-on: banded shading across its width (lit highlight, dark far edge)."""
        k = self.k
        p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
        r1 = r if r1 is None else r1
        ring = stroke([p0, p1], [r, r1], round_caps=caps) if caps else quad(p0, p1, r, r1)
        p = self.flat(name, ring, z, mat, outline=outline, **kw)
        if p is None or not bands:
            return p
        ax = unit(p1 - p0)
        n = lit_normal(ax)
        ext = ax * (r + r1 + 2 * k)

        def strip(a, b, tone):
            q = G.poly([p0 - ext + n * a * r, p1 + ext + n * a * r1, p1 + ext + n * b * r1, p0 - ext + n * b * r])
            p.fill(q, tone)
        strip(0.12, 0.58, 'light')
        strip(-0.38, -0.72, 'shade')
        strip(-0.72, -1.2, 'deep')
        return p

    def rod(self, name, p0, p1, r, z, mat=STEEL, **kw):
        return self.cylinder(name, p0, p1, r, z, mat, **kw)

    def hinge(self, name, x, y, R, z, mat=FRAME, pin=STEEL, ry=None, bolt=True, **kw):
        """Hinge knuckle seen end-on: domed disc, dark ring, bright pin."""
        k = self.k
        ry = R if ry is None else ry
        p = self.part(name, G.ellipse(x, y, R, ry), z, mat, tone='base', shading=dome() + cel(k, 0.9), **kw)
        if p is None:
            return p
        p.fill(G.ellipse(x, y, R * 0.66, ry * 0.66), 'deep')
        p.fill(G.ellipse(x, y, R * 0.46, ry * 0.46), f'{pin.name}.base')
        p.fill(G.ellipse(x - R * 0.12, y - ry * 0.14, R * 0.22, ry * 0.22), f'{pin.name}.light')
        if bolt and R > 2.2 * k:
            p.fill(G.ellipse(x, y, R * 0.14, ry * 0.14), f'{DARK.name}.base')
        return p

    def knuckle(self, name, x, y, hl, R, z, mat=FRAME, pin=STEEL, vertical=False):
        """Hinge knuckle seen across its axis (the axis lies in the picture): a short barrel
        ``2*hl`` long and ``2*R`` thick with banded shading and the pin's ends showing as
        collars. Use it where :meth:`hinge` would show the same joint end-on in another view."""
        k = self.k
        if vertical:
            a, b = (x, y - hl), (x, y + hl)
        else:
            a, b = (x - hl, y), (x + hl, y)
        p = self.cylinder(name, a, b, R, z, mat)
        if p is None:
            return p
        a, b = np.asarray(a, float), np.asarray(b, float)
        ax = unit(b - a)
        # pin collars at both ends and a split line between the two leaves of the hinge
        for q in (a, b):
            self.cylinder(name + f'_pin{int(q[0])}{int(q[1])}', q - ax * 0.9 * k, q + ax * 0.9 * k, R * 0.62, z + 0.01, pin)
        m = (a + b) / 2
        n = perp(ax)
        p.line([m + n * R, m - n * R], 0.8 * k, 'deep')
        return p

    def joint(self, name, x, y, R, z, axis='lateral', mat=FRAME, hl=None, **kw):
        """A rotary joint drawn the way its axis faces this view. ``axis`` is the direction of
        the joint's pin on the body: 'lateral' (left-right: elbows, knees, hips, shoulders
        flexing forward and back) shows end-on only from the side (east); 'sagittal'
        (front-back) shows end-on from the front and back. Seen across its axis the joint is a
        knuckle barrel instead of a disc."""
        end_on = (self.view == 'east') == (axis == 'lateral')
        if end_on:
            return self.hinge(name, x, y, R, z, mat, **kw)
        return self.knuckle(name, x, y, hl or R * 1.25, R * 0.78, z, mat, vertical=(axis == 'sagittal' and self.view == 'east'))

    def piston(self, name, a, b, r_body, r_rod, z, split=0.5, body=FRAME, eyes=True, eye_r=None, gland=True, eye_axis='lateral'):
        """Hydraulic piston from a (body end) to b (rod end), with clevis eyes at both ends; the
        eyes' pins follow ``eye_axis`` (see :meth:`joint`)."""
        k = self.k
        a, b = np.asarray(a, float), np.asarray(b, float)
        ax = unit(b - a)
        L = float(np.hypot(*(b - a)))
        m = a + ax * L * split
        parts = []
        parts.append(self.cylinder(name + '_rod', m - ax * 1.0 * k, b, r_rod, z, STEEL))
        bd = self.cylinder(name + '_body', a, m, r_body, z + 0.02, body)
        parts.append(bd)
        if gland and bd is not None:
            g = quad(m - ax * 1.4 * k, m, r_body * 1.08)
            self.flat(name + '_gland', g, z + 0.03, IRON, tone='shade')
            # body ribs
            for t in (0.22, 0.42):
                q = a + ax * L * split * t
                bd.line([q + perp(ax) * r_body, q - perp(ax) * r_body], FINE * k, 'deep')
        if eyes:
            er = eye_r or max(r_body * 0.9, 1.6 * k)
            parts.append(self.joint(name + '_eye0', a[0], a[1], er, z + 0.04, eye_axis, FRAME))
            parts.append(self.joint(name + '_eye1', b[0], b[1], er * 0.85, z + 0.04, eye_axis, FRAME))
        return parts

    # details on a part ------------------------------------------------------------------------
    def bolt(self, p, x, y, r=None, tone=None):
        """Bolt head: dark socket ring, steel head with a lit upper edge."""
        k = self.k
        r = 1.15 * k if r is None else r
        p.fill(G.circle(x, y + r * 0.12, r), tone or f'{DARK.name}.base', mask=None)
        p.fill(G.circle(x, y, r * 0.68), f'{STEEL.name}.shade', mask=None)
        p.fill(G.circle(x - r * 0.12, y - r * 0.16, r * 0.4), f'{STEEL.name}.light', mask=None)

    def panel(self, p, ring, tone='shade', seam=True, w=None):
        """Inset panel: a flat tone patch inside a part, edged with a seam line."""
        p.fill(ring, tone)
        if seam:
            p.details.append(Line(G.poly(ring), (w or FINE) * self.k, 'deep', closed=True))

    def thickness(self, p, ring_pts, depth, tone='shade'):
        """Visible thickness under a plate's lower edge: the edge points (left to right) and the
        same points ``depth`` px lower."""
        pts = [tuple(q) for q in ring_pts]
        low = [(x, y + depth) for x, y in pts[::-1]]
        p.fill(G.poly(pts + low), tone)

    def bolts(self, p, pts, r=None):
        for x, y in pts:
            self.bolt(p, x, y, r)

    def slots(self, p, x0, y0, x1, y1, n, vertical=False, gap=0.45, lip=True):
        """A bank of slot vents inside a box."""
        k = self.k
        for i in range(n):
            if vertical:
                w = (x1 - x0) / n
                a = x0 + i * w + w * gap / 2
                b = a + w * (1 - gap)
                r = G.rounded(G.rect(a, y0, b, y1), min(0.5 * k, (b - a) / 2))
                p.fill(r, f'{DARK.name}.base', mask=None)
                if lip:
                    p.fill(G.rect(a, y1 - 0.6 * k, b, y1), f'{DARK.name}.light', mask=None)
            else:
                h = (y1 - y0) / n
                a = y0 + i * h + h * gap / 2
                b = a + h * (1 - gap)
                r = G.rounded(G.rect(x0, a, x1, b), min(0.5 * k, (b - a) / 2))
                p.fill(r, f'{DARK.name}.base', mask=None)
                if lip:
                    p.fill(G.rect(x0, b - 0.5 * k, x1, b), f'{DARK.name}.light', mask=None)

    def perfs(self, p, pts, r=None):
        k = self.k
        r = 0.8 * k if r is None else r
        for x, y in pts:
            p.fill(G.circle(x, y, r), f'{DARK.name}.base', mask=None)

    def lamp(self, p, x, y, w=None, h=None, mat=AMBER):
        """Small indicator lamp in a dark bezel."""
        k = self.k
        w = 1.2 * k if w is None else w
        h = 0.9 * k if h is None else h
        p.fill(G.rect(x - w / 2 - 0.5 * k, y - h / 2 - 0.5 * k, x + w / 2 + 0.5 * k, y + h / 2 + 0.5 * k), f'{DARK.name}.deep', mask=None)
        p.fill(G.rect(x - w / 2, y - h / 2, x + w / 2, y + h / 2), f'{mat.name}.base', mask=None)
        p.fill(G.rect(x - w / 2, y - h / 2, x + w * 0.1, y - h * 0.05), f'{mat.name}.light', mask=None)

    def stencil(self, p, x, y, w, n=3, tone=None):
        """A few short dashes, like stencilled serials."""
        k = self.k
        tone = tone or 'deep'
        seg = w / (n * 1.6)
        for i in range(n):
            a = x + i * seg * 1.6
            p.fill(G.rect(a, y - 0.35 * k, a + seg * (1.0 if i % 2 == 0 else 0.6), y + 0.35 * k), tone)

    def chevrons(self, p, x, y, w, h, n=2, tone=None, down=True):
        k = self.k
        tone = tone or 'deep'
        for i in range(n):
            yy = y + i * h * 0.9 * (1 if down else -1)
            tip = (x, yy + (h * 0.5 if down else -h * 0.5))
            pts = [(x - w / 2, yy), tip, (x + w / 2, yy)]
            p.line(pts, 0.75 * k, tone)

    def notch(self, p, x0, y0, x1, y1, tone=None):
        p.fill(G.rect(x0, y0, x1, y1), tone or f'{DARK.name}.base', mask=None)

    def seam(self, p, pts, w=None, tone='deep'):
        p.line(pts, (w or FINE) * self.k, tone)

    # compound pieces --------------------------------------------------------------------------
    def hose(self, name, pts, w, z, mat=HOSE, ribs=2.4, smooth_n=8, outline='auto'):
        """Rubber hose / cable loom along a smoothed path, with a highlight and rib rings."""
        k = self.k
        path = smooth(pts, smooth_n) if len(pts) > 2 else np.asarray(pts, float)
        hw = w / 2
        p = self.flat(name, stroke(path, hw), z, mat, outline=outline)
        if p is None:
            return p
        # lit stripe on the side facing the light
        mid = len(path) // 2
        t = unit(path[min(mid + 1, len(path) - 1)] - path[max(mid - 1, 0)])
        sgn = 1.0 if np.dot(perp(t), LIGHT_DIR) > 0 else -1.0
        p.line(offset_path(path, sgn * hw * 0.38), hw * 0.42, 'light')
        p.line(offset_path(path, -sgn * hw * 0.72), hw * 0.5, 'deep')
        if ribs:
            L = path_len(path)
            d = ribs * k
            while d < L - ribs * k * 0.5:
                q, tt = along(path, d)
                nn = perp(tt)
                p.line([q + nn * hw * 1.1, q - nn * hw * 1.1], 0.6 * k, 'deep')
                d += ribs * k
        return p

    def lens(self, name, x, y, R, z, glass=CYAN, housing=FRAME, ry=None, hood=0.0, rings=True):
        """Optic seen face-on: housing ring, rubber bezel, near-black glass with a faint tinted
        reflection and a small glint."""
        k = self.k
        ry = R if ry is None else ry
        p = self.part(name, G.ellipse(x, y, R, ry), z, housing, tone='base', shading=cel(k, 0.8))
        if p is None:
            return p
        p.fill(G.ellipse(x, y, R * 0.8, ry * 0.8), f'{DARK.name}.deep', mask=None)
        p.fill(G.ellipse(x, y, R * 0.64, ry * 0.64), f'{GLASS.name}.base', mask=None)
        # reflection: a crescent of the lens coating's tint on the lower right
        p.fill(G.ellipse(x + R * 0.12, y + ry * 0.14, R * 0.42, ry * 0.38), f'{glass.name}.deep', mask=None)
        p.fill(G.ellipse(x + R * 0.04, y + ry * 0.05, R * 0.4, ry * 0.36), f'{GLASS.name}.base', mask=None)
        p.fill(G.ellipse(x - R * 0.28, y - ry * 0.28, R * 0.14, ry * 0.12), f'{GLASS.name}.light', mask=None)
        return p

    def lamp_part(self, name, x, y, w, h, z, mat=AMBER):
        k = self.k
        p = self.flat(name, G.rect(x - w / 2, y - h / 2, x + w / 2, y + h / 2), z, mat, outline=0.6 * k)
        if p is not None:
            p.fill(G.rect(x - w / 2, y - h / 2, x + w * 0.05, y), 'light')
        return p

    def bracket(self, name, x0, y0, x1, y1, z, mat=FRAME, bolts=2, bevel=0.8):
        """A clamp/bracket plate with bolts along its long axis."""
        k = self.k
        p = self.block(name, G.chamfer(G.rect(x0, y0, x1, y1), 0.8 * k), z, mat, bevel=bevel)
        if p is None:
            return p
        if bolts:
            horiz = (x1 - x0) >= (y1 - y0)
            for i in range(bolts):
                t = (i + 0.5) / bolts
                if horiz:
                    self.bolt(p, x0 + (x1 - x0) * t, (y0 + y1) / 2, 0.75 * k)
                else:
                    self.bolt(p, (x0 + x1) / 2, y0 + (y1 - y0) * t, 0.75 * k)
        return p
