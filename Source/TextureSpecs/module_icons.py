"""rwtexturegen spec: item icons for the armor modifications and the mod's UI icons.

    pip install -e <rwtexturegen>
    rwtex build module_icons.py --out <scratch dir> --mod ../..

Installs Textures/ModularPowerArmor/Items/<Module>.png (64 px) and the two UI icons in
Textures/ModularPowerArmor/UI. The icons use the same white armor construction as the worn art
(see modules.py): flat white faces, #ccc lower facets, near-black recesses, black outlines.
"""
import math

from rwtex import geom as G
from rwtex.render import Bevel, Part, Scene, Split

WHITE = 'armor_white'
DARK = 'undersuit'
SHADING = lambda: [Bevel(1.0, 1.1), Split(at=0.8, tone='shade')]  # noqa: E731


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


def hexagon(cx, cy, r):
    return G.poly([(cx + r * math.cos(math.radians(60 * i + 30)), cy + r * math.sin(math.radians(60 * i + 30))) for i in range(6)])


# ----------------------------------------------------------------------------- module items

def icon_plating():
    s = scene('AdditionalPlating')
    back = part(s, 'back', G.chamfer(G.poly([(20, 9), (55, 9), (58, 20), (54, 38), (24, 38)]), 3), 1, tone='shade',
                shading=[Bevel(1.0, 1.1, light_tone='base', shade_tone='deep')])
    bolt(back, 51, 14)
    front = part(s, 'front', G.chamfer(G.poly([(8, 22), (46, 22), (51, 33), (44, 55), (14, 55), (5, 33)]), 3), 2)
    front.line([(10, 33), (46, 33)], 1.0, 'shade')
    for x, y in ((12, 27), (42, 27), (17, 49), (39, 49)):
        bolt(front, x, y)
    return s


def icon_ablative():
    s = scene('AblativeShielding')
    r = 8.2
    tiles = [(32, 17), (18, 25), (46, 25), (32, 33), (18, 41), (46, 41), (32, 49)]
    for i, (x, y) in enumerate(tiles):
        tone = 'shade' if i in (1, 5) else 'base'
        p = part(s, f'tile{i}', hexagon(x, y, r - 0.8), 1 + i * 0.01, tone=tone,
                 shading=[Bevel(0.9, 1.0, shade_tone='deep' if tone == 'shade' else 'shade')])
        p.fill(hexagon(x, y, r * 0.38), 'shade' if tone == 'base' else 'deep')
    return s


def icon_servos():
    s = scene('BiogelServos')
    rod = part(s, 'rod', G.rounded(G.rect(44, 29, 58, 35), 1.5), 1, mat='steel_bright', shading=[Bevel(0.8, 0.8)])
    rod.line([(46, 32), (56, 32)], 0.8, 'light')
    body = part(s, 'body', G.capsule(9, 32, 45, 32, 10.5), 2)
    body.fill(G.rect(23, 21.5, 31, 42.5), 'undersuit.base')
    body.fill(G.rect(23, 25, 31, 27), 'undersuit.light')
    tube = part(s, 'tube', G.poly([(12, 21), (14, 14), (22, 10), (34, 10), (42, 14), (44, 21), (40, 22), (38, 17), (33, 14.5),
                                   (23, 14.5), (18, 17), (16, 22)]), 3, mat=DARK, shading=[Bevel(0.8, 0.8)])
    tube.line([(17, 15.5), (22, 12.5), (34, 12.5), (39, 15.5)], 0.9, 'light')
    return s


def icon_bionic_sync():
    s = scene('BionicSynchronization')
    cable = part(s, 'cable', G.poly([(40, 44), (48, 50), (56, 50), (58, 56), (54, 59), (46, 57), (36, 49)]), 1, mat=DARK,
                 shading=[Bevel(0.8, 0.8)])
    cable.line([(41, 48), (47, 53), (54, 53)], 0.8, 'light')
    body = part(s, 'body', G.chamfer(G.rect(8, 10, 46, 48), 6), 2)
    body.fill(G.circle(27, 28, 11.5), 'shade')
    body.fill(G.circle(27, 28, 8.5), 'undersuit.base')
    body.fill(G.circle(27, 28, 3.2), 'base')
    for x in (16, 27, 38):
        part(s, f'pin{x}', G.rect(x - 2.2, 46, x + 2.2, 54), 1.5, mat='steel_bright', shading=[Bevel(0.6, 0.6)])
    return s


def icon_coprocessor():
    s = scene('CoProcessor')
    mast = part(s, 'mast', G.rounded(G.rect(45, 4, 49, 20), 1.5), 1, mat=DARK, shading=[Bevel(0.6, 0.6)])
    tip = part(s, 'tip', G.rounded(G.rect(43, 3, 51, 9), 2), 1.1)
    body = part(s, 'body', G.chamfer(G.rect(9, 16, 55, 57), 5), 2)
    body.fill(G.rounded(G.rect(17, 24, 47, 48), 1.5), 'undersuit.base')
    for y in (29, 36, 43):
        body.line([(20, y), (44, y)], 1.6, 'undersuit.light')
    bolt(body, 13.5, 21)
    bolt(body, 50.5, 52)
    return s


def icon_exoframe():
    s = scene('Exoframe')
    bar = part(s, 'bar', G.chamfer(G.rect(6, 12, 40, 20), 2), 1)
    strut = part(s, 'strut', G.chamfer(G.poly([(30, 16), (40, 16), (44, 56), (34, 56)]), 2), 2)
    strut.line([(37, 22), (40.5, 52)], 1.0, 'shade')
    for name, (x, y, r) in (('hip', (35, 16, 8.5)), ('knee', (39, 52, 6.5))):
        p = part(s, name, G.chamfer(G.rect(x - r, y - r, x + r, y + r), r * 0.42), 3)
        p.fill(G.circle(x, y - 0.3, r * 0.56), 'undersuit.base')
        p.fill(G.circle(x, y - 0.3, r * 0.22), 'base')
    return s


def icon_sensor_array():
    s = scene('SensorArray')
    bracket = part(s, 'bracket', G.chamfer(G.poly([(36, 18), (54, 22), (54, 44), (36, 48)]), 2), 1, tone='shade',
                   shading=[Bevel(0.9, 1.0, light_tone='base', shade_tone='deep')])
    bolt(bracket, 49, 33)
    pod = part(s, 'pod', G.rounded(G.rect(12, 6, 38, 58), 7), 2)
    for y in (17, 32, 47):
        pod.fill(G.circle(25, y, 6.6), 'shade')
        pod.fill(G.circle(25, y, 4.8), 'undersuit.base')
        pod.fill(G.circle(23.4, y - 1.6, 1.3), 'undersuit.light')
    return s


def icon_stress_dampener():
    s = scene('StressDampener')
    band = []
    for i in range(25):
        a = math.radians(200 + 140 * i / 24)
        band.append((32 + 26 * math.cos(a), 44 + 26 * math.sin(a)))
    for i in range(25):
        a = math.radians(340 - 140 * i / 24)
        band.append((32 + 19 * math.cos(a), 44 + 19 * math.sin(a)))
    part(s, 'band', G.poly(band), 1, shading=[Bevel(0.9, 1.0)])
    node = part(s, 'node', G.chamfer(G.rect(20, 8, 44, 30), 5), 2)
    node.fill(G.circle(32, 19, 7.5), 'undersuit.base')
    node.fill(G.circle(32, 19, 4.2), 'shade')
    node.fill(G.circle(32, 19, 1.8), 'undersuit.base')
    return s


def icon_uplink():
    s = scene('TargetingUplink')
    mast = part(s, 'mast', G.rounded(G.rect(41, 5, 45, 30), 1.5), 1, mat=DARK, shading=[Bevel(0.6, 0.6)])
    part(s, 'tip', G.rounded(G.rect(39, 3, 47, 10), 2), 1.1)
    body = part(s, 'body', G.chamfer(G.rect(7, 24, 52, 55), 5), 2)
    body.fill(G.circle(22, 39, 9.5), 'shade')
    body.fill(G.circle(22, 39, 7), 'undersuit.base')
    body.fill(G.circle(19.5, 36.5, 2), 'undersuit.light')
    for y in (33, 39, 45):
        body.line([(37, y), (47, y)], 1.4, 'shade')
    return s


def icon_thermal():
    s = scene('ThermalRegulator')
    for x in (8, 52):
        pipe = part(s, f'pipe{x}', G.rounded(G.rect(x - 3, 14, x + 3, 50), 2.5), 1, mat=DARK, shading=[Bevel(0.7, 0.7)])
        pipe.line([(x - 1, 17), (x - 1, 47)], 0.8, 'light')
    body = part(s, 'body', G.chamfer(G.rect(12, 9, 48, 56), 4), 2)
    for i in range(5):
        y = 17 + i * 8
        body.fill(G.rounded(G.rect(17, y - 1.8, 43, y + 1.8), 1), 'undersuit.base')
    return s


def icon_trauma():
    s = scene('TraumaSuite')
    clip = part(s, 'clip', G.chamfer(G.rect(22, 5, 42, 15), 2), 1, tone='shade',
                shading=[Bevel(0.9, 1.0, light_tone='base', shade_tone='deep')])
    clip.fill(G.rect(27, 8, 37, 11), 'undersuit.base')
    body = part(s, 'body', G.rounded(G.rect(8, 12, 56, 56), 7), 2)
    body.fill(G.rect(28, 20, 36, 46), 'undersuit.base')
    body.fill(G.rect(19, 29, 45, 37), 'undersuit.base')
    return s


ICONS = [icon_plating, icon_ablative, icon_servos, icon_bionic_sync, icon_coprocessor, icon_exoframe, icon_sensor_array,
         icon_stress_dampener, icon_uplink, icon_thermal, icon_trauma]


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
    return [fn() for fn in ICONS]
