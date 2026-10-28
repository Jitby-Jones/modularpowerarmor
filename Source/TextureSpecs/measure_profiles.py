#!/usr/bin/env python3
"""Measure the silhouettes of the supported power armors so modules can be fitted to each one.

    python3 measure_profiles.py --core <art source>/Things/Pawn/Humanlike \
        --royalty <art source>/RoyaltyArtSource/Things/Pawn/Humanlike/Apparel \
        --vae <VanillaArmourExpanded>/Textures/Things \
        --vfep <VanillaFactionsExpanded-Pirates>/Textures/Things/Pawn/Humanlike

Writes armor_profiles.json next to this script. The reference textures are only read, never
copied: the output holds numbers, the same kind of measurement rwtexturegen keeps in
rwtex/data/armor_fit.json.

Body armor, per body type and view: the offset in px (at 128) of the armor's coloured edge
(opaque, non-outline pixels) beyond the naked-body template that rwtex's TorsoForm is built on,
sampled at the body heights in V, separately for the screen-left and screen-right side because
launchers and grappling hooks make several armors asymmetric.

Also per body type and view: the top row of the coloured area over each shoulder, so shoulder
plates start where the armor's shoulder does.

Helmets, per view: the helmet's coloured extent as a radius factor of the head template that
rwtex's HeadForm is built on, for the sides, the top, and the front and back (east view), plus
the side extents row by row (at the head latitudes in PHI), which show where antennas, horns and
crests stick out.
"""
import argparse
import json
import math
import os
import sys

import numpy as np
from PIL import Image

from rwtex.archetypes.apparel import templates
from rwtex.form import HeadForm, TorsoForm

BODY_TYPES = ['Male', 'Female', 'Thin', 'Hulk', 'Fat']
DIRS = ['south', 'east', 'north']
V = [round(0.04 * i, 2) for i in range(-1, 27)]      # -0.04 .. 1.04
OUTLINE_LUMA = 40         # opaque pixels darker than this are the black outline

# armor key -> (source, worn graphic path relative to the source folder)
ARMORS = {
    'Marine': ('core', 'Apparel/PowerArmor/PowerArmor'),
    'Recon': ('core', 'Apparel/ReconArmor/ReconArmor'),
    'Cataphract': ('royalty', 'CataphractArmor/CataphractArmor'),
    'Grenadier': ('royalty', 'GrenadierArmor/GrenadierArmor'),
    'Locust': ('royalty', 'LocustArmor/LocustArmor'),
    'Phoenix': ('royalty', 'PhoenixArmor/PhoenixArmor'),
    'PrestigeMarine': ('royalty', 'PrestigeMarineArmor/PrestigeMarineArmor'),
    'PrestigeRecon': ('royalty', 'PrestigeReconArmor/PrestigeReconArmor'),
    'PrestigeCataphract': ('royalty', 'PrestigeCataphractArmor/PrestigeCataphractArmor'),
    'Siegebreaker': ('vae', 'Apparel/SiegebreakerArmor/SiegebreakerArmor'),
    'RoyalSiegebreaker': ('vae', 'Apparel/RoyalSiegebreakerArmor/RoyalSiegebreakerArmor'),
    'Trooper': ('vae', 'Apparel/TrooperArmor/TrooperArmor'),
    'RoyalTrooper': ('vae', 'Apparel/RoyalTrooperArmor/RoyalTrooperArmor'),
    'Privateer': ('vfep', 'PrivateerArmor/PrivateerArmor'),
}
HELMETS = {
    'Marine': ('core', 'Apparel/PowerArmorHelmet/PowerArmorHelmet'),
    'Recon': ('core', 'Apparel/ReconArmorHelmet/ReconHelmet'),
    'Cataphract': ('royalty', 'CataphractArmorHelmet/CataphractHelmet'),
    'PrestigeMarine': ('royalty', 'PrestigeMarineHelmet/PrestigeMarineHelmet'),
    'PrestigeRecon': ('royalty', 'PrestigeReconHelmet/PrestigeReconHelmet'),
    'PrestigeCataphract': ('royalty', 'PrestigeCataphractHelmet/PrestigeCataphractHelmet'),
    'Siegebreaker': ('vae', 'Headgear/SiegebreakerHelmet/SiegebreakerHelmet'),
    'RoyalSiegebreaker': ('vae', 'Headgear/RoyalSiegebreakerHelmet/RoyalSiegebreakerHelmet'),
    'Trooper': ('vae', 'Headgear/TrooperHelmet/TrooperHelmet'),
    'RoyalTrooper': ('vae', 'Headgear/RoyalTrooperHelmet/RoyalTrooperHelmet'),
}
SOURCES = {
    'Marine': 'RimWorld art source (PowerArmor)', 'Recon': 'RimWorld art source (ReconArmor)',
    'Cataphract': 'Royalty art source', 'Grenadier': 'Royalty art source', 'Locust': 'Royalty art source',
    'Phoenix': 'Royalty art source', 'PrestigeMarine': 'Royalty art source', 'PrestigeRecon': 'Royalty art source',
    'PrestigeCataphract': 'Royalty art source', 'Siegebreaker': 'Vanilla Armour Expanded', 'RoyalSiegebreaker': 'Vanilla Armour Expanded',
    'Trooper': 'Vanilla Armour Expanded', 'RoyalTrooper': 'Vanilla Armour Expanded', 'Privateer': 'Vanilla Factions Expanded - Pirates',
}


def load_mask(path):
    """(opaque, coloured) boolean masks at 128 px."""
    for ext in ('.png', '.psd'):
        if os.path.exists(path + ext):
            path = path + ext
            break
    else:
        raise FileNotFoundError(path)
    if path.endswith('.psd'):
        from psd_tools import PSDImage
        im = PSDImage.open(path).composite().convert('RGBA')
    else:
        im = Image.open(path).convert('RGBA')
    if im.size != (128, 128):
        im = im.resize((128, 128), Image.LANCZOS)
    a = np.asarray(im).astype(float)
    opaque = a[:, :, 3] >= 128
    luma = 0.299 * a[:, :, 0] + 0.587 * a[:, :, 1] + 0.114 * a[:, :, 2]
    return opaque, opaque & (luma >= OUTLINE_LUMA)


def row_extent(mask, y):
    """Leftmost and rightmost set pixel on screen row y (fractional rows sample the nearest)."""
    yi = int(round(y))
    if yi < 0 or yi >= mask.shape[0]:
        return None
    xs = np.nonzero(mask[yi])[0]
    if len(xs) == 0:
        return None
    return float(xs[0]), float(xs[-1] + 1)


def measure_body(path_of, bt):
    form = TorsoForm(bt)
    out = {}
    for d in DIRS:
        _, col = load_mask(path_of(bt, d))
        rows = np.nonzero(col.any(axis=1))[0]
        out[f'{d}_top_px'] = float(rows.min()) if len(rows) else None
        out[f'{d}_bot_px'] = float(rows.max() + 1) if len(rows) else None
        left, right = [], []
        for v in V:
            y = form.y(v)
            ext = row_extent(col, y)
            if d == 'east':
                c, h = form.d(v)
            elif d == 'north':
                c, h = form._ext(form.N, y, form.y_sh, form.y_hip)
            else:
                c, h = form.a(v)
            if ext is None:
                left.append(None)
                right.append(None)
                continue
            left.append(round((c - h) - ext[0], 2))      # + = armor sticks out past the body on screen-left
            right.append(round(ext[1] - (c + h), 2))     # + = armor sticks out on screen-right
        out[f'{d}_l'] = left
        out[f'{d}_r'] = right
        out[f'{d}_shoulder_top'] = shoulder_top(col, form, d)
    return out


def shoulder_top(col, form, d):
    """Top row (px) of the armor's coloured area over each shoulder: screen-left and
    screen-right bands for south/north, one band across the shoulder for east."""
    if d == 'east':
        c, h = form.d(0.15)
        bands = [(c - 0.5 * h, c + 0.42 * h)]
    else:
        c, h = form.a(0.15) if d == 'south' else form._ext(form.N, form.y(0.15), form.y_sh, form.y_hip)
        bands = [(c - 0.95 * h, c - 0.55 * h), (c + 0.55 * h, c + 0.95 * h)]
    res = []
    for x0, x1 in bands:
        sub = col[:, int(round(x0)):int(round(x1))]
        rows = np.nonzero(sub.any(axis=1))[0]
        res.append(float(rows.min()) if len(rows) else None)
    return res


PHI = [round(0.1 * i, 1) for i in range(-12, 13)]     # head latitudes for the per-row helmet profile


def measure_helmet(path_of):
    out = {}
    for d in DIRS:
        hf = HeadForm(d)
        _, col = load_mask(path_of(d))
        ys, xs = np.nonzero(col)
        if len(xs) == 0:
            continue
        # per-row side extents as radius factors of the head ellipsoid at that latitude:
        # south/north [screen-left, screen-right], east [back, front]
        rows = []
        for ph in PHI:
            y = hf.cy - math.sin(ph) * hf.ry * 0.92
            ext = row_extent(col, y)
            w = hf.rx * max(math.cos(ph), 0.2)
            rows.append(None if ext is None else [round((hf.cx - ext[0]) / w, 3), round((ext[1] - hf.cx) / w, 3)])
        out[f'{d}_rows'] = rows
        x0, x1, y0 = float(xs.min()), float(xs.max() + 1), float(ys.min())
        y1 = float(ys.max() + 1)
        top = (hf.cy - y0) / (hf.ry * 0.92)
        bottom = (y1 - hf.cy) / (hf.ry * 0.92)
        if d == 'east':
            out['east'] = dict(front=round((x1 - hf.cx) / hf.rx, 3), back=round((hf.cx - x0) / hf.rx, 3), top=round(top, 3),
                               bottom=round(bottom, 3))
        else:
            out[d] = dict(left=round((hf.cx - x0) / hf.rx, 3), right=round((x1 - hf.cx) / hf.rx, 3), top=round(top, 3),
                          bottom=round(bottom, 3))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--core', required=True)
    ap.add_argument('--royalty', required=True)
    ap.add_argument('--vae', required=True)
    ap.add_argument('--vfep', required=True)
    ap.add_argument('--out', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'armor_profiles.json'))
    args = ap.parse_args()
    roots = {'core': args.core, 'royalty': args.royalty, 'vae': args.vae, 'vfep': args.vfep}

    result = {
        'source': 'Measured from the worn textures of each armor (RimWorld/Royalty art source, Vanilla Armour Expanded, '
                  'Vanilla Factions Expanded - Pirates). Numbers only - no pixels. See measure_profiles.py.',
        'v': V,
        'phi': PHI,
        'armors': {},
        'helmets': {},
    }
    for key, (src, rel) in ARMORS.items():
        base = os.path.join(roots[src], rel)
        result['armors'][key] = {'from': SOURCES[key],
                                 'bodies': {bt: measure_body(lambda b, d: f'{base}_{b}_{d}', bt) for bt in BODY_TYPES}}
        print('armor', key, file=sys.stderr)
    for key, (src, rel) in HELMETS.items():
        base = os.path.join(roots[src], rel)
        result['helmets'][key] = measure_helmet(lambda d: f'{base}_{d}')
        print('helmet', key, file=sys.stderr)
    with open(args.out, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=1)
    print('wrote', args.out)


if __name__ == '__main__':
    main()
