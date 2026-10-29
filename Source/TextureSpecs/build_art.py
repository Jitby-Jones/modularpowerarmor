#!/usr/bin/env python3
"""Render the worn module art (modules.py) into the mod's Textures folder.

    pip install -e <rwtexturegen>
    python3 build_art.py                       # everything (replaces Textures/ModularPowerArmor/Worn)
    python3 build_art.py --modules Exoframe --fits Marine --slot body

Writes <Module>_<Fit>_<BodyType>_<dir>.png (body) or <Module>_<Fit>_<dir>.png (helmet), 256 px,
with the CutoutComplex mask next to it (..._<dir>m.png). Masks are written at half size: they
only say which parts take the armor's colour, and those parts are separated by outlines, so a
128 px mask tints exactly the same pixels for a quarter of the memory. A module that shows
nothing in one of its views on an armor (it would sit on one of the armor's own features) gets a
tiny empty texture there, since Graphic_Multi would otherwise fill the missing facing from
another one.
"""
import argparse
import os
import shutil
import sys
import time
from multiprocessing import Pool

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mpa_fit as F  # noqa: E402
import modules as MD  # noqa: E402

TEX = os.path.normpath(os.path.join(HERE, '..', '..', 'Textures', 'ModularPowerArmor', 'Worn'))
FOLDER = {'body': 'Body', 'head': 'Head'}


def jobs(slots, names, fits):
    out = []
    for slot in slots:
        for mod in MD.modules(slot):
            if names and mod.name not in names:
                continue
            for fit in (F.BODY_FITS if slot == 'body' else F.HELMET_FITS):
                if fits and fit not in fits:
                    continue
                for bt in (F.BODY_TYPES if slot == 'body' else [None]):
                    for d in mod.dirs:
                        out.append((slot, mod.name, fit, bt, d))
    return out


def half(mask):
    """Box-filter the mask to half size (each mask texel covers 2x2 texels of the texture)."""
    return mask.convert('RGB').reduce(2)


def run(job):
    slot, name, fit, bt, d = job
    img, mask = MD.render_module(slot, name, fit, d, bt or 'Male')
    if img is None or img.getbbox() is None:
        img = Image.new('RGBA', (4, 4), (0, 0, 0, 0))
        mask = Image.new('RGB', (4, 4), (0, 0, 0))
    else:
        mask = half(mask)
    folder = os.path.join(TEX, FOLDER[slot], f'{name}_{fit}')
    os.makedirs(folder, exist_ok=True)
    base = f'{name}_{fit}_{bt}_{d}' if bt else f'{name}_{fit}_{d}'
    img.save(os.path.join(folder, base + '.png'), optimize=True)
    mask.save(os.path.join(folder, base + 'm.png'), optimize=True)
    return base


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--slot', choices=('body', 'head'), default=None)
    ap.add_argument('--modules', default='')
    ap.add_argument('--fits', default='')
    ap.add_argument('--jobs', type=int, default=os.cpu_count() or 2)
    ap.add_argument('--keep', action='store_true', help="don't clear the Worn folder first")
    a = ap.parse_args()
    slots = [a.slot] if a.slot else ['body', 'head']
    names = set(a.modules.split(',')) if a.modules else set()
    fits = set(a.fits.split(',')) if a.fits else set()
    todo = jobs(slots, names, fits)
    if not (a.keep or names or fits or a.slot) and os.path.isdir(TEX):
        shutil.rmtree(TEX)
    t0 = time.time()
    with Pool(a.jobs) as pool:
        for i, _ in enumerate(pool.imap_unordered(run, todo, chunksize=4)):
            if (i + 1) % 200 == 0:
                print(f'{i + 1}/{len(todo)} {time.time() - t0:.0f}s', flush=True)
    print(f'{len(todo)} textures (+ masks) in {time.time() - t0:.0f}s -> {TEX}')


if __name__ == '__main__':
    main()
