"""rwtexturegen spec: the Armor Modulus workbench (3x2, Graphic_Multi, drawSize (3,2)).

    rwtex build armor_modulus.py --out <scratch dir> --mod ../..

Installs Textures/ModularPowerArmor/Things/ArmorModulus/ArmorModulus_{north,south,east}.png
(west is east mirrored). 128 px per cell: north and south are 384x256, east is 256x384 because
RimWorld turns the draw size for horizontal facings.

Facings follow vanilla benches with interactionCellOffset (0,0,-1): placed facing north (the
default) the worker stands south of the bench, so the north texture has its working counter at
the bottom and the armor gantry behind it; south is the bench turned round (gantry in front,
the suit seen from behind); east has the counter on the left, where the worker stands.

The bench is industrial grey like vanilla workbenches and isn't dyed. The suit in the gantry is
rwtexturegen's own marine armor, not RimWorld art.
"""
import numpy as np
from PIL import Image

from rwtex import geom as G
from rwtex.archetypes.apparel import armor
from rwtex.render import Part, Scene
import rwtex.archetypes.armor3d  # noqa: F401  (registers the marine design)

OUTLINE = 4.0
FRAME = 'dms_steel'        # bench body
DARK = 'gunmetal'          # gantry and machinery
TOP = 'ultratech_case'     # work surface
RECESS = 'undersuit'
SCREEN = 'cyan_glow'
SUIT_SIZE = 192            # pawns are drawn 1.5 cells tall: the suit at the same scale


class BenchScene(Scene):
    """A scene drawn in layers, with raster images (the suit) between them."""

    def __init__(self, size, name, layers):
        super().__init__(size, name=name, outline=OUTLINE, inner=2.0)
        self.meta['kind'] = 'building'
        self.layers = layers          # list of Scene or (Image, (x, y))
        for item in layers:
            if isinstance(item, Scene):
                self.parts.extend(item.parts)

    def render(self, glow=True):
        out = Image.new('RGBA', (self.w, self.h), (0, 0, 0, 0))
        for item in self.layers:
            if isinstance(item, Scene):
                out.alpha_composite(item.render(glow))
            else:
                im, (x, y) = item
                out.alpha_composite(im, (int(x), int(y)))
        a = np.array(out)
        a[..., 3] = np.where(a[..., 3] >= 128, 255, 0)
        a[a[..., 3] == 0] = 0
        return Image.fromarray(a)

    def has_mask(self):
        return False


def layer(w, h):
    return Scene((w, h), outline=OUTLINE, inner=2.0, name='layer')


def part(s, name, ring, mat, tone='base', z=None):
    p = Part(name, ring, mat, z=len(s.parts) if z is None else z, shading=[], mask=None, tone=tone)
    s.add(p)
    return p


def vents(p, x0, y0, x1, y1, n, horizontal=True, tone='undersuit.base', width=2.0):
    for i in range(n):
        t = (i + 0.5) / n
        if horizontal:
            y = y0 + (y1 - y0) * t
            p.line([(x0, y), (x1, y)], width, tone)
        else:
            x = x0 + (x1 - x0) * t
            p.line([(x, y0), (x, y1)], width, tone)


def screw(p, x, y, r=1.8):
    p.fill(G.circle(x, y, r), 'undersuit.base')


# ----------------------------------------------------------------------------- bench pieces

def counter(s, x0, y0, x1, y1, face, end_face=None):
    """The work counter seen from above: its top, and the face turned to the camera
    (``face`` px tall along the bottom)."""
    body = part(s, 'counter', G.chamfer(G.rect(x0, y0, x1, y1 + face), 4), FRAME)
    body.fill(G.rect(x0 + 6, y0 + 6, x1 - 6, y1 - 4), f'{TOP}.base')
    body.fill(G.rect(x0 + 6, y0 + 6, x1 - 6, y0 + 10), f'{TOP}.light')
    body.fill(G.rect(x0, y1, x1, y1 + face), f'{FRAME}.shade')
    body.line([(x0, y1), (x1, y1)], 2.0, f'{FRAME}.deep')
    # panels and vents on the face
    n = max(2, int((x1 - x0) / 90))
    for i in range(1, n):
        x = x0 + (x1 - x0) * i / n
        body.line([(x, y1 + 3), (x, y1 + face - 2)], 2.0, f'{FRAME}.deep')
    for i in range(n):
        xa = x0 + (x1 - x0) * i / n + 12
        xb = xa + min(28, (x1 - x0) / n - 24)
        vents(body, xa, y1 + 6, xb, y1 + face - 5, 3, width=1.6)
    return body


def tray(s, x0, y0, x1, y1, modules=3):
    """A rack of finished modules waiting on the counter."""
    t = part(s, 'tray', G.chamfer(G.rect(x0, y0, x1, y1), 3), DARK)
    t.fill(G.rect(x0, y1 - 6, x1, y1), f'{DARK}.shade')
    w = (x1 - x0 - 8) / modules
    for i in range(modules):
        a = x0 + 4 + i * w
        t.fill(G.rect(a + 2, y0 + 4, a + w - 2, y1 - 9), 'undersuit.base')
    for i in range(modules):
        a = x0 + 4 + i * w
        m = part(s, f'module{i}', G.chamfer(G.rect(a + 4, y0 - 6 + (i % 2) * 3, a + w - 4, y1 - 12), 2.5), 'armor_white')
        m.fill(G.rect(a + 4, y1 - 17, a + w - 4, y1 - 12), 'armor_white.shade')
        m.fill(G.rect(a + 8, y0 + (i % 2) * 3, a + w - 8, y0 + 4 + (i % 2) * 3), 'undersuit.base')


def console(s, x0, y0, x1, y1):
    """Control console with a cyan screen."""
    c = part(s, 'console', G.chamfer(G.rect(x0, y0, x1, y1), 4), DARK)
    c.fill(G.rect(x0, y1 - 8, x1, y1), f'{DARK}.shade')
    scr = part(s, 'screen', G.rounded(G.rect(x0 + 7, y0 + 6, x1 - 7, y1 - 15), 2), SCREEN, tone='shade')
    scr.fill(G.rect(x0 + 10, y0 + 9, x1 - 10, y0 + 12), f'{SCREEN}.light')
    for i in range(3):
        y = y0 + 16 + i * 6
        if y < y1 - 18:
            scr.line([(x0 + 11, y), (x0 + 11 + (x1 - x0 - 22) * (0.8 - 0.25 * i), y)], 1.6, f'{SCREEN}.light')
    for i in range(3):
        c.fill(G.circle(x0 + 12 + i * 9, y1 - 4, 2.2), ('glow_green', 'glow_yellow', 'glow_red')[i] + '.base')


def tool(s, x, y, ang):
    """A wrench lying on the counter."""
    w = [(0, -3), (26, -3), (30, -7), (37, -7), (35, -2), (35, 2), (37, 7), (30, 7), (26, 3), (0, 3), (-4, 0)]
    ring = G.rotate(G.poly([(x + px, y + py) for px, py in w]), ang, x, y)
    part(s, 'wrench', ring, 'steel_bright')


def post(s, name, x0, y0, x1, y1, face):
    """A gantry post: its front and, along one side, its shaded flank."""
    p = part(s, name, G.chamfer(G.rect(x0, y0, x1, y1), 3), DARK)
    p.fill(G.rect(x0, y0, x0 + 5, y1), f'{DARK}.light')
    p.fill(G.rect(x1 - face, y0, x1, y1), f'{DARK}.shade')
    for y in np.arange(y0 + 14, y1 - 8, 18):
        screw(p, (x0 + x1) / 2, y)
    return p


def beam(s, x0, y0, x1, y1, vertical=False):
    b = part(s, 'beam', G.chamfer(G.rect(x0, y0, x1, y1), 3), DARK)
    if vertical:
        b.fill(G.rect(x0, y0, x0 + 5, y1), f'{DARK}.light')
        b.fill(G.rect(x1 - 6, y0, x1, y1), f'{DARK}.shade')
    else:
        b.fill(G.rect(x0, y0, x1, y0 + 5), f'{DARK}.light')
        b.fill(G.rect(x0, y1 - 6, x1, y1), f'{DARK}.shade')
    return b


def alcove(s, x0, y0, x1, y1):
    """The dark back panel behind the suit, with cable runs."""
    a = part(s, 'alcove', G.rect(x0, y0, x1, y1), 'iron_dark', tone='shade')
    for x in np.linspace(x0 + 14, x1 - 14, 4):
        a.line([(x, y0 + 4), (x, y1 - 4)], 2.0, 'iron_dark.deep')
    return a


def arm(s, name, pts, r=5.0):
    """An articulated tool arm: segments with joints, ending in a tool head."""
    for i, (a, b) in enumerate(zip(pts[:-1], pts[1:])):
        part(s, f'{name}_seg{i}', G.capsule(a[0], a[1], b[0], b[1], r - i * 0.8), FRAME)
    for i, (x, y) in enumerate(pts[:-1]):
        j = part(s, f'{name}_joint{i}', G.circle(x, y, r + 1.5 - i * 0.6), DARK)
        screw(j, x, y, 1.6)
    x, y = pts[-1]
    head = part(s, f'{name}_tool', G.circle(x, y, 3.6), SCREEN, tone='base')
    head.fill(G.circle(x - 1, y - 1, 1.4), f'{SCREEN}.light')


def clamp(s, name, x, y0, y1):
    c = part(s, name, G.rect(x - 3, y0, x + 3, y1), DARK, tone='shade')
    part(s, name + '_jaw', G.chamfer(G.rect(x - 7, y1 - 2, x + 7, y1 + 5), 2), DARK)
    return c


# ----------------------------------------------------------------------------- the suit

_SUIT = {}


def suit(view):
    """The marine suit hanging in the gantry, from rwtexturegen's own armor design."""
    if view not in _SUIT:
        aset = armor('spacer', size=SUIT_SIZE, design='marine', name='ModulusSuit', mask_roles=(), ground=False,
                     body_types=['Male'], dirs=('south', 'east', 'north'), outline=OUTLINE)
        for d in ('south', 'east', 'north'):
            _SUIT[d] = aset.scenes[f'Male_{d}'].render()
    return _SUIT[view]


# ----------------------------------------------------------------------------- facings

def bench_north():
    """Placed facing north: counter at the bottom where the worker stands, gantry behind it."""
    W, H = 384, 256
    back, front, top = layer(W, H), layer(W, H), layer(W, H)
    counter(back, 8, 118, 376, 222, 28)
    alcove(back, 86, 26, 298, 120)
    post(back, 'post_l', 60, 12, 86, 128, 7)
    post(back, 'post_r', 298, 12, 324, 128, 7)
    beam(back, 52, 8, 332, 30)
    sx, sy = 192 - SUIT_SIZE // 2, 38 - int(44 * SUIT_SIZE / 128)
    clamp(front, 'clamp_l', 166, 30, 44)
    clamp(front, 'clamp_r', 218, 30, 44)
    arm(front, 'arm_l', [(86, 60), (112, 82), (134, 86)])
    arm(front, 'arm_r', [(298, 60), (272, 82), (250, 86)])
    tray(top, 20, 146, 112, 196)
    console(top, 280, 138, 366, 200)
    tool(top, 140, 186, -12)
    return BenchScene((W, H), 'ArmorModulus_north', [back, (suit('south'), (sx, sy)), front, top])


def bench_south():
    """Turned round: the worker stands north of the bench, the gantry is nearest the camera and
    the suit shows its back."""
    W, H = 384, 256
    back, mid, front = layer(W, H), layer(W, H), layer(W, H)
    counter(back, 8, 8, 376, 112, 20)
    tray(back, 272, 30, 364, 80)
    console(back, 18, 26, 104, 86)
    alcove(mid, 86, 126, 298, 222)
    post(mid, 'post_l', 60, 112, 86, 248, 7)
    post(mid, 'post_r', 298, 112, 324, 248, 7)
    beam(mid, 52, 108, 332, 130)
    sx, sy = 192 - SUIT_SIZE // 2, 136 - int(44 * SUIT_SIZE / 128)
    clamp(mid, 'clamp_l', 166, 130, 140)
    clamp(mid, 'clamp_r', 218, 130, 140)
    beam(front, 52, 226, 332, 248)
    arm(front, 'arm_l', [(86, 160), (112, 180), (134, 184)])
    arm(front, 'arm_r', [(298, 160), (272, 180), (250, 184)])
    return BenchScene((W, H), 'ArmorModulus_south', [back, mid, (suit('north'), (sx, sy)), front])


def bench_east():
    """Facing east: the worker stands on the west side, so the counter runs down the left and
    the gantry stands on the right with the suit in profile, facing the worker."""
    W, H = 256, 384
    back, mid, front = layer(W, H), layer(W, H), layer(W, H)
    counter(back, 8, 8, 122, 352, 24)
    tray(back, 20, 34, 110, 84)
    console(back, 20, 262, 110, 324)
    tool(back, 36, 150, 70)
    alcove(mid, 134, 70, 238, 330)
    post(mid, 'post_n', 128, 22, 248, 52, 8)
    post(mid, 'post_s', 128, 330, 248, 362, 8)
    beam(mid, 222, 26, 248, 358, vertical=True)
    im = suit('east').transpose(Image.FLIP_LEFT_RIGHT)
    sx, sy = 184 - SUIT_SIZE // 2, 206 - int(76 * SUIT_SIZE / 128)
    clamp(front, 'clamp', 190, 52, 118)
    arm(front, 'arm', [(152, 330), (148, 300), (162, 276)])
    return BenchScene((W, H), 'ArmorModulus_east', [back, mid, (im, (sx, sy)), front])


SPEC = {
    'name': 'MPA_ArmorModulus',
    'output': {'dir': 'output/MPA_ArmorModulus', 'tex_root': 'ModularPowerArmor/Things/ArmorModulus', 'mask': False, 'svg': False},
}


def build(spec):
    return [bench_north(), bench_south(), bench_east()]
