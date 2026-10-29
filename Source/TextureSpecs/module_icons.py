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


def icon_subpersona():
    s = scene('AuxiliarySubpersona')
    # three subcore cartridges slotted into the housing from above
    for i, (x, top) in enumerate(((19, 13), (32, 8), (45, 13))):
        cart = part(s, f'cartridge{i}', G.chamfer(G.rect(x - 5.5, top, x + 5.5, 34), 1.8), 1 + 0.01 * i,
                    tone='shade' if i != 1 else 'base', shading=[Bevel(0.8, 0.9, shade_tone='deep')])
        cart.fill(G.rect(x - 3.2, top + 3.2, x + 3.2, top + 9.5), 'undersuit.base')
        cart.fill(G.rect(x - 3.2, top + 3.2, x + 3.2, top + 4.6), 'undersuit.light')
    body = part(s, 'body', G.chamfer(G.rect(7, 28, 57, 57), 5), 2)
    body.fill(G.rect(7, 28, 57, 33.5), 'shade')
    for x in (19, 32, 45):
        body.fill(G.rect(x - 6.0, 28, x + 6.0, 31.5), 'undersuit.base')
    body.fill(G.rounded(G.rect(14, 40, 50, 49), 1.5), 'undersuit.base')
    for x in (20, 27, 34):
        body.fill(G.rect(x - 1.6, 43, x + 1.6, 46), 'undersuit.light')
    bolt(body, 11.5, 52.5)
    bolt(body, 52.5, 52.5)
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


def icon_uranium():
    s = scene('UraniumPlating')
    back = part(s, 'back', G.chamfer(G.poly([(16, 6), (54, 6), (58, 18), (54, 32), (18, 32)]), 3), 1, tone='shade',
                shading=[Bevel(1.0, 1.1, light_tone='base', shade_tone='deep')])
    back.line([(36, 8), (36, 30)], 1.2, 'undersuit.base')
    bolt(back, 50, 11)
    front = G.chamfer(G.poly([(6, 18), (48, 18), (53, 30), (48, 56), (10, 56), (4, 30)]), 3)
    f = part(s, 'front', front, 2)
    f.fill(G.poly([(6, 18), (19, 18), (19, 56), (10, 56), (4, 30)]), 'shade')
    f.fill(G.poly([(35, 18), (48, 18), (53, 30), (48, 56), (35, 56)]), 'shade')
    f.fill(G.rect(4, 49, 53, 56), 'deep')
    for x in (19, 35):
        f.line([(x, 19), (x, 49)], 1.6, 'undersuit.base')
    f.line([(5, 30), (52, 30)], 1.2, 'undersuit.base')
    for x, y in ((11.5, 24), (42, 24), (11.5, 43), (42, 43)):
        bolt(f, x, y, 1.4)
    return s


def icon_rigidity():
    s = scene('RigidityMatrix')
    # a lattice brace: two cross-braced bays between heavy rails, pinned at both ends
    p = part(s, 'frame', G.chamfer(G.rect(16, 4, 48, 60), 3), 1)
    for y0, y1 in ((10, 31), (33, 54)):
        ym = (y0 + y1) / 2
        for h in (G.poly([(21, y0 + 2), (43, y0 + 2), (32, ym - 1.5)]), G.poly([(21, y1 - 2), (43, y1 - 2), (32, ym + 1.5)]),
                  G.poly([(21, y0 + 5), (29, ym), (21, y1 - 5)]), G.poly([(43, y0 + 5), (35, ym), (43, y1 - 5)])):
            p.fill(G.chamfer(h, 0.8), 'undersuit.base')
    p.fill(G.rect(43, 4, 48, 60), 'shade')
    p.fill(G.rect(16, 30.5, 48, 33.5), 'shade')
    for y in (7, 57):
        p.fill(G.rect(16, y - 3, 48, y + 3), 'shade')
    for name, y in (('pin_top', 7), ('pin_bottom', 57)):
        pin = part(s, name, G.rounded(G.rect(8, y - 3.5, 56, y + 3.5), 3), 2, tone='shade',
                   shading=[Bevel(0.7, 0.8, light_tone='base', shade_tone='deep')])
        bolt(pin, 12, y, 1.5)
        bolt(pin, 52, y, 1.5)
    return s


def icon_second_heart():
    s = scene('SecondHeart')
    for i, x in enumerate((24, 40)):
        tube = part(s, f'tube{i}', G.rounded(G.rect(x - 3.5, 4.5, x + 3.5, 16), 1.5), 1, mat=DARK, shading=[Bevel(0.7, 0.7)])
        tube.line([(x - 1.2, 6.5), (x - 1.2, 14)], 0.9, 'light')
    body = part(s, 'body', G.rounded(G.rect(13, 11, 51, 59), 9), 2)
    body.fill(G.rect(13, 11, 51, 17), 'shade')
    body.fill(G.rect(13, 52, 51, 59), 'shade')
    body.fill(G.rect(43, 17, 51, 52), 'shade')
    body.fill(G.circle(32, 35, 11.5), 'deep')
    body.fill(G.circle(32, 35, 9.0), 'undersuit.base')
    heart = [(32, 42), (24.5, 34.5), (24.5, 30.5), (27.5, 28), (32, 31), (36.5, 28), (39.5, 30.5), (39.5, 34.5)]
    body.fill(G.rounded(G.poly(heart), 1.6), 'light')
    return s


def icon_second_mind():
    s = scene('SecondMind')
    for i, y in enumerate((14, 23, 32, 41)):
        fin = part(s, f'fin{i}', G.rounded(G.rect(4, y, 60, y + 5), 1.5), 1 + i * 0.01, tone='shade',
                   shading=[Bevel(0.6, 0.7, shade_tone='deep')])
    body = part(s, 'body', G.chamfer(G.rect(11, 6, 53, 56), 7), 2)
    body.fill(G.rect(46, 6, 53, 56), 'shade')
    body.fill(G.circle(31, 30, 14), 'deep')
    body.fill(G.circle(31, 30, 11), 'undersuit.base')
    body.fill(G.circle(31, 30, 6.8), 'light')
    body.fill(G.circle(31, 30, 3.4), 'undersuit.base')
    body.fill(G.circle(28.5, 27.5, 1.3), 'light')
    body.fill(G.rect(17, 49, 45, 52), 'undersuit.base')
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
