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
BODY = ['Plating', 'BiogelServos', 'Regenerators', 'Exoframe', 'Subpersona', 'ThermalFins', 'RigidityMatrix', 'SecondHeart',
        'LongjumpHydraulics']
HEAD = ['Plating', 'TargetingUplink', 'SensorArray', 'Subpersona', 'NeuralLink', 'StressDampener', 'Regenerators', 'SecondMind']
ICONS = ['AdditionalPlating', 'UraniumPlating', 'BiogelServos', 'NeuromemeticRegenerators', 'Exoframe', 'AuxiliarySubpersona',
         'ThermalRegulator', 'RigidityMatrix', 'SecondHeart', 'LongjumpHydraulics', 'TargetingUplink', 'SensorArray', 'SecondMind',
         'BionicSynchronization', 'StressDampener', 'AblativeShielding']


def load(p):
    return Image.open(p).convert('RGBA') if os.path.exists(p) else Image.new('RGBA', (128, 128))


def tint(im, col):
    a = np.array(im).astype(float)
    a[:, :, :3] *= np.array(col, float)[None, None, :]
    return Image.fromarray(a.clip(0, 255).astype(np.uint8))


arm = armor('spacer', design='marine', name='Marine', mask_roles=(), ground=False, body_types=['Male'])
hel = helmet('spacer', design='marine', name='MarineHelmet', mask_roles=(), ground=False)


def pawn(d, col):
    body = PV.body_scene('Male', d).render()
    ap = arm.scenes[f'Male_{d}'].render()
    for m in BODY:
        ap.alpha_composite(load(f'{TEX}/ModularPowerArmor/Worn/Body/{m}_Marine/{m}_Marine_Male_{d}.png'))
    hm = hel.scenes[d].render()
    for m in HEAD:
        hm.alpha_composite(load(f'{TEX}/ModularPowerArmor/Worn/Head/{m}_Marine/{m}_Marine_{d}.png'))
    ap, hm = tint(ap, col), tint(hm, col)
    head = PV.head_scene(d).render()
    return PV.worn(body, ap, head, hm, d)


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
    p = p.crop((14, 14, 114, 150)).resize((180, 245), Image.NEAREST)
    img.paste(p, (40 + i * 196, 172), p)
# the Armor Modulus
bench = load(f'{TEX}/ModularPowerArmor/Things/ArmorModulus/ArmorModulus_north.png')
img.paste(bench, (858, 166), bench)
d.text((862, 428), 'Armor Modulus', font=ImageFont.truetype(font, 20), fill=(205, 212, 218))
d.text((68, 434), 'Every module is drawn to fit 14 armors and 10 helmets, dyed with the armor.',
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
