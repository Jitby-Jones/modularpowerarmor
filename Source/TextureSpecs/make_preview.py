"""Draws About/Preview.png: an rwtexturegen marine suit wearing every module, the Armor Modulus
and the item icons.

    python3 make_preview.py        (after building modules.py, module_icons.py and armor_modulus.py into the mod)

No RimWorld art is used: the pawn, armor and helmet are drawn by rwtexturegen.
"""
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from rwtex import preview as PV
from rwtex.archetypes.apparel import armor, helmet
import rwtex.archetypes.armor3d  # noqa: F401  (registers the marine designs)

MOD = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
TEX = os.path.join(MOD, 'Textures')
# in the order the render nodes draw them (layerFraction, see modules.py)
BODY = ['Exoframe', 'RigidityMatrix', 'LongjumpHydraulics', 'BiogelServos', 'ThermalFins', 'Plating', 'Regenerators', 'SecondHeart',
        'Subpersona']
HEAD = ['Plating', 'NeuralLink', 'StressDampener', 'Subpersona', 'SecondMind', 'Regenerators', 'SensorArray', 'TargetingUplink']
OVER_HEAD = ['PlatingPad']
ICONS = ['AdditionalPlating', 'UraniumPlating', 'BiogelServos', 'NeuromemeticRegenerators', 'Exoframe', 'AuxiliarySubpersona',
         'ThermalRegulator', 'RigidityMatrix', 'SecondHeart', 'LongjumpHydraulics', 'TargetingUplink', 'SensorArray', 'SecondMind',
         'BionicSynchronization', 'StressDampener', 'AblativeShielding']


def load(p):
    return Image.open(p).convert('RGBA') if os.path.exists(p) else Image.new('RGBA', (SIZE, SIZE))


def tint(im, col, mask=None):
    """Multiply by the armor's colour: everything (Cutout) or the mask's red parts (CutoutComplex)."""
    a = np.array(im).astype(float)
    c = np.array(col, float)[None, None, :]
    if mask is None:
        a[:, :, :3] *= c
    else:
        m = np.asarray(mask.convert('RGB').resize(im.size, Image.BILINEAR)).astype(float)[:, :, :1] / 255.0
        a[:, :, :3] *= (1 - m) + m * c
    return Image.fromarray(a.clip(0, 255).astype(np.uint8))


def module_layer(path, col):
    """A module texture dyed through its mask, or None where the module doesn't show."""
    if not os.path.exists(path + '.png'):
        return None
    img = load(path + '.png')
    if img.size != (SIZE, SIZE):
        return None
    return tint(img, col, Image.open(path + 'm.png'))


SIZE = 256
arm = armor('spacer', design='marine', name='Marine', size=SIZE, mask_roles=(), ground=False, body_types=['Male'])
hel = helmet('spacer', design='marine', name='MarineHelmet', size=SIZE, mask_roles=(), ground=False)


def pawn(d, col):
    body = PV.body_scene('Male', d, SIZE).render()
    ap = tint(arm.scenes[f'Male_{d}'].render(), col)
    for m in BODY:
        lay = module_layer(f'{TEX}/ModularPowerArmor/Worn/Body/{m}_Marine/{m}_Marine_Male_{d}', col)
        if lay is not None:
            ap.alpha_composite(lay)
    hm = tint(hel.scenes[d].render(), col)
    for m in HEAD:
        lay = module_layer(f'{TEX}/ModularPowerArmor/Worn/Head/{m}_Marine/{m}_Marine_{d}', col)
        if lay is not None:
            hm.alpha_composite(lay)
    head = PV.head_scene(d, SIZE).render()
    out = PV.worn(body, ap, head, hm, d, SIZE)
    # from the side the near shoulder plate is drawn over the head (aboveHead in the defs)
    for m in OVER_HEAD:
        lay = module_layer(f'{TEX}/ModularPowerArmor/Worn/Body/{m}_Marine/{m}_Marine_Male_{d}', col)
        if lay is not None:
            out.alpha_composite(lay, (0, int(SIZE * 0.3)))
    return out


W, H = 1280, 720
grad = np.zeros((H, W, 3), np.uint8)
top, bot = np.array([26, 29, 34]), np.array([40, 44, 50])
for y in range(H):
    grad[y, :, :] = (top + (bot - top) * y / H).astype(np.uint8)
img = Image.fromarray(grad)
d = ImageDraw.Draw(img)
font = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
font2 = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
d.text((64, 44), 'Modular Power Armor', font=ImageFont.truetype(font, 64), fill=(228, 234, 238))
d.text((68, 124), 'Install modifications into power armor like bionics into pawns.', font=ImageFont.truetype(font2, 26),
       fill=(150, 200, 225))
# pawns: plain, then dyed, every module installed
cols = [(1.0, 1.0, 1.0), (1.0, 1.0, 1.0), (1.0, 1.0, 1.0), (0.78, 0.36, 0.32)]
dirs = ['south', 'east', 'north', 'south']
for i, (dr, col) in enumerate(zip(dirs, cols)):
    p = pawn(dr, col)
    p = p.crop((24, 16, 232, 300)).resize((180, 245), Image.LANCZOS)
    img.paste(p, (40 + i * 196, 172), p)
# the Armor Modulus
bench = load(f'{TEX}/ModularPowerArmor/Things/ArmorModulus/ArmorModulus_north.png')
img.paste(bench, (858, 166), bench)
d.text((862, 428), 'Armor Modulus', font=ImageFont.truetype(font, 20), fill=(205, 212, 218))
d.text((68, 434), 'Drawn to fit 14 armors and 10 helmets, its plates dyed with the armor.',
       font=ImageFont.truetype(font2, 20), fill=(175, 182, 190))
# icons
for i, n in enumerate(ICONS):
    ic = load(f'{TEX}/ModularPowerArmor/Items/{n}.png').resize((60, 60), Image.NEAREST)
    x = 46 + i * 75
    d.rounded_rectangle([x - 6, 490, x + 66, 562], 10, fill=(44, 49, 56), outline=(78, 86, 96), width=2)
    img.paste(ic, (x, 496), ic)
d.text((68, 590), 'Install at the Armor Modulus: bills refit armor in bulk, and colonists can refit what they wear.',
       font=ImageFont.truetype(font2, 20), fill=(150, 200, 225))
d.text((68, 630), 'Quality on every module  ·  Computational Load budgets  ·  Combat Extended  ·  RimWorld 1.5 / 1.6 / 1.7',
       font=ImageFont.truetype(font2, 20), fill=(150, 160, 170))
img.save(os.path.join(MOD, 'About', 'Preview.png'))
print('wrote About/Preview.png')
