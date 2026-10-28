#!/usr/bin/env python3
"""Generates the placeholder textures for Modular Power Armor.

    python3 Source/Textures/generate_textures.py [--preview OUT.png]

Writes item icons, worn overlays (north/south/east), UI icons and About/Preview.png.
Everything is drawn at 4x and downscaled for clean edges.

Worn overlays use RimWorld's apparel canvas: 128x128 on a 1.5-tile mesh, centred on the
body (body overlays) or on the head (helmet overlays). The head sits about 29px above the
body centre. Coordinates below assume the vanilla male body; other body types are handled by
the bodyTypeAdjustments in each module's render node. Replace any of these files with real
art at the same path and size and the mod will use it.
"""
import argparse
import os

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
TEX = os.path.join(ROOT, "Textures", "ModularPowerArmor")
SS = 4

OUTLINE = (30, 33, 37, 255)
STEEL = (128, 136, 144, 255)
STEEL_LIGHT = (176, 184, 191, 255)
STEEL_DARK = (86, 93, 101, 255)
GUNMETAL = (66, 72, 80, 255)
GUNMETAL_LIGHT = (100, 108, 118, 255)
CYAN = (110, 225, 255, 255)
CYAN_CORE = (215, 250, 255, 255)
GREEN = (120, 225, 120, 255)
GREEN_DARK = (58, 140, 70, 255)
GREEN_CORE = (210, 255, 205, 255)
RED = (214, 58, 52, 255)
RED_CORE = (255, 190, 180, 255)
MED_WHITE = (226, 230, 232, 255)
MED_SHADE = (176, 183, 188, 255)
PURPLE = (185, 125, 255, 255)
PURPLE_CORE = (238, 215, 255, 255)
TILE = (190, 118, 80, 255)
TILE_LIGHT = (222, 160, 118, 255)
TILE_DARK = (138, 80, 56, 255)
GOLD = (214, 178, 84, 255)
AMBER = (255, 176, 64, 255)


class Canvas:
    def __init__(self, size):
        self.size = size
        self.img = Image.new("RGBA", (size * SS, size * SS), (0, 0, 0, 0))
        self.draw = ImageDraw.Draw(self.img)
        self.glow_layer = Image.new("RGBA", self.img.size, (0, 0, 0, 0))
        self.glow_draw = ImageDraw.Draw(self.glow_layer)

    @staticmethod
    def _b(box):
        return [v * SS for v in box]

    @staticmethod
    def _p(points):
        return [(x * SS, y * SS) for x, y in points]

    def rect(self, box, fill, outline=OUTLINE, width=1.5, radius=1.5):
        self.draw.rounded_rectangle(self._b(box), radius=radius * SS, fill=fill,
                                    outline=outline, width=int(width * SS) if outline else 0)

    def ellipse(self, box, fill, outline=OUTLINE, width=1.5):
        self.draw.ellipse(self._b(box), fill=fill, outline=outline,
                          width=int(width * SS) if outline else 0)

    def poly(self, points, fill, outline=OUTLINE, width=1.5):
        self.draw.polygon(self._p(points), fill=fill, outline=outline,
                          width=int(width * SS) if outline else 0)

    def line(self, points, color, width, outline=OUTLINE, outline_width=1.2):
        pts = self._p(points)
        if outline:
            self.draw.line(pts, fill=outline, width=int((width + 2 * outline_width) * SS), joint="curve")
            for x, y in pts:
                r = (width / 2 + outline_width) * SS
                self.draw.ellipse([x - r, y - r, x + r, y + r], fill=outline)
        self.draw.line(pts, fill=color, width=int(width * SS), joint="curve")
        for x, y in pts:
            r = width / 2 * SS
            self.draw.ellipse([x - r, y - r, x + r, y + r], fill=color)

    def dot(self, center, radius, color):
        x, y = center
        self.draw.ellipse(self._b([x - radius, y - radius, x + radius, y + radius]), fill=color)

    def glow(self, center, radius, color, strength=150):
        x, y = center
        c = (color[0], color[1], color[2], strength)
        self.glow_draw.ellipse(self._b([x - radius, y - radius, x + radius, y + radius]), fill=c)

    def glow_rect(self, box, color, strength=150):
        c = (color[0], color[1], color[2], strength)
        self.glow_draw.rounded_rectangle(self._b(box), radius=2 * SS, fill=c)

    def render(self):
        blurred = self.glow_layer.filter(ImageFilter.GaussianBlur(2.5 * SS))
        combined = Image.alpha_composite(blurred, self.img)
        return combined.resize((self.size, self.size), Image.LANCZOS)

    def save(self, rel_path):
        path = os.path.join(TEX, rel_path + ".png")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.render().save(path)
        return path


def blank(rel_path, size=128):
    path = os.path.join(TEX, rel_path + ".png")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    Image.new("RGBA", (size, size), (0, 0, 0, 0)).save(path)


# ---------------------------------------------------------------- shared parts

def plate(c, box, radius=2.5, rivets=True, fill=STEEL, light=STEEL_LIGHT, dark=STEEL_DARK):
    x0, y0, x1, y1 = box
    c.rect(box, fill, radius=radius)
    c.rect([x0 + 1.5, y0 + 1.2, x1 - 1.5, y0 + 3.2], light, outline=None, radius=1)
    c.rect([x0 + 1.5, y1 - 3.0, x1 - 1.5, y1 - 1.3], dark, outline=None, radius=1)
    if rivets and x1 - x0 > 10:
        for x in (x0 + 3.2, x1 - 3.2):
            for y in (y0 + 3.4, y1 - 3.4):
                c.dot((x, y), 0.9, OUTLINE)


def tube(c, points, color=GREEN, dark=GREEN_DARK, core=GREEN_CORE, width=4.0, bands=True):
    c.line(points, dark, width + 1.2)
    c.line(points, color, width - 0.6, outline=None)
    c.line(points, core, 1.2, outline=None)
    for p in points:
        c.glow(p, 4, color, 90)
    if bands:
        for (xa, ya), (xb, yb) in zip(points, points[1:]):
            for t in (0.25, 0.5, 0.75):
                x, y = xa + (xb - xa) * t, ya + (yb - ya) * t
                c.dot((x, y), width / 2 + 0.4, dark)
                c.dot((x, y), width / 2 - 0.6, color)


def leds(c, start, count, step, colors, radius=1.1):
    x, y = start
    for i in range(count):
        col = colors[i % len(colors)]
        c.glow((x + i * step, y), 2.4, col, 170)
        c.dot((x + i * step, y), radius, col)


def processor_box(c, box, led_row_y=None):
    x0, y0, x1, y1 = box
    c.rect(box, GUNMETAL, radius=2.5)
    c.rect([x0 + 1.5, y0 + 1.2, x1 - 1.5, y0 + 3.0], GUNMETAL_LIGHT, outline=None, radius=1)
    # vent grille
    for y in range(int(y0 + 6), int(y1 - 4), 3):
        c.line([(x0 + 3, y), (x1 - 3, y)], STEEL_DARK, 0.9, outline=None)
    if led_row_y is not None:
        n = max(2, int((x1 - x0 - 6) // 4))
        leds(c, (x0 + 4, led_row_y), n, 4, [CYAN, GREEN, CYAN, AMBER])


def med_canister(c, box):
    x0, y0, x1, y1 = box
    c.rect(box, MED_WHITE, radius=3)
    c.rect([x0 + 1.4, y1 - 3.2, x1 - 1.4, y1 - 1.3], MED_SHADE, outline=None, radius=1)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    arm = min(x1 - x0, y1 - y0) * 0.28
    c.rect([cx - arm, cy - arm * 0.35, cx + arm, cy + arm * 0.35], RED, outline=None, radius=0.5)
    c.rect([cx - arm * 0.35, cy - arm, cx + arm * 0.35, cy + arm], RED, outline=None, radius=0.5)
    c.rect([x0 + 1, y0 - 2.2, x1 - 1, y0 + 0.5], STEEL_DARK, radius=1)


def fin_stack(c, box, horizontal=True):
    x0, y0, x1, y1 = box
    c.rect(box, GUNMETAL, radius=2)
    if horizontal:
        y = y0 + 3
        while y < y1 - 2:
            c.line([(x0 + 2, y), (x1 - 2, y)], STEEL_LIGHT, 1.1, outline=None)
            y += 3
    else:
        x = x0 + 3
        while x < x1 - 2:
            c.line([(x, y0 + 2), (x, y1 - 2)], STEEL_LIGHT, 1.1, outline=None)
            x += 3
    c.line([(x0 + 1.5, y1 - 2), (x1 - 1.5, y1 - 2)], CYAN, 1.2, outline=None)
    c.glow(((x0 + x1) / 2, y1 - 2), 4, CYAN, 110)


# ---------------------------------------------------------------- worn: body
# Male body, south view: shoulders ~y46-52 spanning x40-88, torso x44-84, hips ~y86, legs to ~y112.

def body_plating():
    s = Canvas(128)
    plate(s, [40, 44, 52, 54], radius=4)            # right pauldron (viewer's left)
    plate(s, [76, 44, 88, 54], radius=4)            # left pauldron
    s.poly([(51, 52), (77, 52), (75, 73), (64, 77), (53, 73)], STEEL)   # chest plate
    s.poly([(53, 53.5), (75, 53.5), (74.4, 56)], STEEL_LIGHT, outline=None)
    s.line([(64, 55), (64, 74)], STEEL_DARK, 1.0, outline=None)
    for p in [(55, 56), (73, 56), (56, 70), (72, 70)]:
        s.dot(p, 0.9, OUTLINE)
    s.save("Worn/Body/Plating_south")

    n = Canvas(128)
    plate(n, [40, 44, 52, 54], radius=4)
    plate(n, [76, 44, 88, 54], radius=4)
    plate(n, [51, 52, 77, 76], radius=3)            # back plate
    n.save("Worn/Body/Plating_north")

    e = Canvas(128)
    plate(e, [55, 44, 71, 54], radius=4)            # near pauldron
    e.poly([(70, 52), (78, 54), (77, 72), (70, 75)], STEEL)   # chest plate seen from the side
    e.poly([(71, 53.5), (77, 55), (76.8, 57)], STEEL_LIGHT, outline=None)
    e.save("Worn/Body/Plating_east")


def body_thermal_fins():
    blank("Worn/Body/ThermalFins_south")
    n = Canvas(128)
    fin_stack(n, [47, 50, 59, 78])
    fin_stack(n, [69, 50, 81, 78])
    n.line([(59, 64), (69, 64)], CYAN, 1.6)
    n.save("Worn/Body/ThermalFins_north")

    e = Canvas(128)
    fin_stack(e, [36, 50, 47, 78], horizontal=False)
    e.line([(47, 60), (52, 60)], CYAN, 1.5)
    e.save("Worn/Body/ThermalFins_east")


def body_trauma_suite():
    s = Canvas(128)
    med_canister(s, [77, 74, 87, 88])                # on the wearer's left hip
    s.line([(82, 74), (80, 64)], RED, 1.2)
    s.save("Worn/Body/TraumaSuite_south")

    n = Canvas(128)
    med_canister(n, [41, 74, 51, 88])
    n.line([(46, 74), (48, 64)], RED, 1.2)
    n.save("Worn/Body/TraumaSuite_north")

    e = Canvas(128)
    med_canister(e, [47, 74, 58, 88])                # back of the hip
    e.save("Worn/Body/TraumaSuite_east")


def body_coprocessor():
    blank("Worn/Body/CoProcessor_south")
    n = Canvas(128)
    processor_box(n, [50, 47, 78, 80], led_row_y=76)
    n.rect([58, 52, 70, 64], GUNMETAL_LIGHT, radius=1.5)
    n.glow((64, 58), 5, CYAN, 160)
    n.dot((64, 58), 2.4, CYAN)
    n.dot((64, 58), 1.0, CYAN_CORE)
    n.save("Worn/Body/CoProcessor_north")

    e = Canvas(128)
    processor_box(e, [33, 47, 48, 80])
    leds(e, (37, 76), 3, 3.5, [CYAN, GREEN, AMBER], radius=1.0)
    e.save("Worn/Body/CoProcessor_east")


def body_biogel_servos():
    s = Canvas(128)
    tube(s, [(42, 54), (41, 70), (43, 86)])
    tube(s, [(86, 54), (87, 70), (85, 86)])
    tube(s, [(50, 90), (51, 106)], width=3.4)
    tube(s, [(78, 90), (77, 106)], width=3.4)
    s.save("Worn/Body/BiogelServos_south")

    n = Canvas(128)
    tube(n, [(42, 54), (41, 70), (43, 86)])
    tube(n, [(86, 54), (87, 70), (85, 86)])
    tube(n, [(50, 90), (51, 106)], width=3.4)
    tube(n, [(78, 90), (77, 106)], width=3.4)
    n.save("Worn/Body/BiogelServos_north")

    e = Canvas(128)
    tube(e, [(63, 52), (61, 70), (63, 86)])
    tube(e, [(65, 90), (66, 108)], width=3.4)
    e.save("Worn/Body/BiogelServos_east")


def body_exoframe():
    s = Canvas(128)
    s.line([(46, 85), (82, 85)], GUNMETAL, 2.2)                # hip bar peeking out at the waist
    for x in (46, 82):
        s.line([(x, 86), (x, 108)], STEEL_DARK, 2.6)           # struts along the outer thighs
        s.line([(x, 86), (x, 108)], STEEL_LIGHT, 0.9, outline=None)
        s.ellipse([x - 3.2, 82, x + 3.2, 88.4], GUNMETAL)
        s.dot((x, 85.2), 1.0, AMBER)
    s.save("Worn/Body/Exoframe_south")

    n = Canvas(128)
    n.rect([45, 44, 83, 49], GUNMETAL, radius=2)         # shoulder yoke
    n.rect([44, 85, 84, 90], GUNMETAL, radius=2)         # hip bar
    n.rect([61, 42, 67, 96], STEEL_DARK, radius=2)       # spine
    for y in range(47, 94, 6):
        n.rect([59.5, y, 68.5, y + 3.2], STEEL, radius=1.2)
    for x in (47, 81):
        n.line([(x, 90), (x, 112)], STEEL_DARK, 2.6)
        n.line([(x, 90), (x, 112)], STEEL_LIGHT, 0.9, outline=None)
    n.dot((64, 87.5), 1.2, AMBER)
    n.glow((64, 87.5), 3, AMBER, 140)
    n.save("Worn/Body/Exoframe_north")

    e = Canvas(128)
    e.rect([39, 42, 45, 94], STEEL_DARK, radius=2)       # spine behind the back
    for y in range(46, 92, 6):
        e.rect([37.5, y, 46.5, y + 3.2], STEEL, radius=1.2)
    e.line([(44, 88), (56, 90)], GUNMETAL, 2.6)          # hip arm
    e.ellipse([52.5, 86.5, 59.5, 93.5], GUNMETAL)
    e.dot((56, 90), 1.0, AMBER)
    e.line([(56, 92), (57, 112)], STEEL_DARK, 2.6)       # leg strut
    e.line([(56, 92), (57, 112)], STEEL_LIGHT, 0.9, outline=None)
    e.save("Worn/Body/Exoframe_east")


# ---------------------------------------------------------------- worn: helmet
# Head canvas: head/helmet roughly x38-90, y30-90, eyes around y58-62.

def head_plating():
    s = Canvas(128)
    s.poly([(42, 44), (50, 37), (78, 37), (86, 44), (84, 47), (44, 47)], STEEL)   # brow plate
    s.poly([(50, 38.6), (78, 38.6), (80, 40.5), (48, 40.5)], STEEL_LIGHT, outline=None)
    for x in (50, 64, 78):
        s.dot((x, 43.5), 0.9, OUTLINE)
    s.save("Worn/Head/Plating_south")

    n = Canvas(128)
    plate(n, [44, 36, 84, 50], radius=5)
    n.save("Worn/Head/Plating_north")

    e = Canvas(128)
    e.poly([(50, 40), (58, 35), (82, 37), (88, 44), (86, 47), (52, 47)], STEEL)
    e.poly([(58, 36.6), (81, 38.6), (83, 40.5), (56, 39)], STEEL_LIGHT, outline=None)
    e.save("Worn/Head/Plating_east")


def head_neural_link():
    s = Canvas(128)
    s.line([(42, 60), (40, 72), (44, 82)], GUNMETAL, 1.4)
    s.ellipse([37.5, 54.5, 46.5, 63.5], GUNMETAL)
    s.glow((42, 59), 5, CYAN, 170)
    s.dot((42, 59), 2.2, CYAN)
    s.dot((42, 59), 0.9, CYAN_CORE)
    s.save("Worn/Head/NeuralLink_south")

    n = Canvas(128)
    n.line([(86, 60), (88, 72), (84, 82)], GUNMETAL, 1.4)
    n.ellipse([81.5, 54.5, 90.5, 63.5], GUNMETAL)
    n.glow((86, 59), 5, CYAN, 170)
    n.dot((86, 59), 2.2, CYAN)
    n.save("Worn/Head/NeuralLink_north")

    e = Canvas(128)
    e.line([(58, 60), (50, 70), (44, 80)], GUNMETAL, 1.4)
    e.ellipse([53.5, 54.5, 62.5, 63.5], GUNMETAL)
    e.glow((58, 59), 5, CYAN, 170)
    e.dot((58, 59), 2.2, CYAN)
    e.dot((58, 59), 0.9, CYAN_CORE)
    e.save("Worn/Head/NeuralLink_east")


def head_coprocessor():
    blank("Worn/Head/CoProcessor_south")
    n = Canvas(128)
    processor_box(n, [54, 54, 74, 70])
    leds(n, (58, 66), 4, 4, [CYAN, GREEN, CYAN, AMBER], radius=0.9)
    n.save("Worn/Head/CoProcessor_north")

    e = Canvas(128)
    processor_box(e, [32, 52, 43, 70])
    leds(e, (35.5, 66), 2, 4, [CYAN, AMBER], radius=0.9)
    e.save("Worn/Head/CoProcessor_east")


def head_stress_dampener():
    s = Canvas(128)
    s.line([(44, 46), (54, 42), (64, 41), (74, 42), (84, 46)], GOLD, 1.8)
    for p in [(54, 42), (64, 41), (74, 42)]:
        s.glow(p, 3.5, PURPLE, 170)
        s.dot(p, 1.5, PURPLE)
        s.dot(p, 0.6, PURPLE_CORE)
    s.save("Worn/Head/StressDampener_south")

    n = Canvas(128)
    n.line([(44, 46), (54, 42), (64, 41), (74, 42), (84, 46)], GOLD, 1.8)
    n.glow((64, 41), 3.5, PURPLE, 170)
    n.dot((64, 41), 1.5, PURPLE)
    n.save("Worn/Head/StressDampener_north")

    e = Canvas(128)
    e.line([(50, 44), (62, 40), (76, 40), (86, 44)], GOLD, 1.8)
    for p in [(62, 40), (76, 40)]:
        e.glow(p, 3.5, PURPLE, 170)
        e.dot(p, 1.5, PURPLE)
        e.dot(p, 0.6, PURPLE_CORE)
    e.save("Worn/Head/StressDampener_east")


def head_targeting_uplink():
    def antenna(c, base, tip):
        c.line([base, tip], STEEL_DARK, 1.3)
        c.glow(tip, 3, RED, 180)
        c.dot(tip, 1.4, RED)

    s = Canvas(128)
    antenna(s, (40, 52), (35, 16))
    s.rect([36, 50, 44, 58], GUNMETAL, radius=1.5)          # antenna mount
    s.line([(44, 56), (51, 59)], GUNMETAL, 1.6)             # optic arm
    s.ellipse([46, 54, 58, 66], GUNMETAL)                   # optic over the right eye
    s.glow((52, 60), 5, RED, 170)
    s.ellipse([49, 57, 55, 63], RED, outline=None)
    s.dot((51, 59), 1.0, RED_CORE)
    s.save("Worn/Head/TargetingUplink_south")

    n = Canvas(128)
    antenna(n, (88, 52), (93, 16))
    n.rect([84, 50, 92, 58], GUNMETAL, radius=1.5)
    n.save("Worn/Head/TargetingUplink_north")

    e = Canvas(128)
    antenna(e, (50, 50), (44, 14))
    e.rect([46, 48, 54, 56], GUNMETAL, radius=1.5)
    e.line([(54, 54), (80, 57)], GUNMETAL, 1.6)             # rail along the helmet side
    e.ellipse([79, 52, 91, 64], GUNMETAL)
    e.glow((85, 58), 5, RED, 170)
    e.ellipse([82.5, 55.5, 88.5, 61.5], RED, outline=None)
    e.dot((84.5, 57.5), 1.0, RED_CORE)
    e.save("Worn/Head/TargetingUplink_east")


def head_visor():
    s = Canvas(128)
    s.glow_rect([42, 52, 86, 66], CYAN, 140)
    s.rect([43, 54, 85, 64], GUNMETAL, radius=4)
    s.rect([45.5, 56, 82.5, 62], CYAN, outline=None, radius=3)
    s.rect([47, 56.8, 81, 58.2], CYAN_CORE, outline=None, radius=1)
    for x in (55, 64, 73):
        s.line([(x, 56.3), (x, 61.7)], (60, 150, 190, 255), 0.6, outline=None)
    s.save("Worn/Head/Visor_south")

    blank("Worn/Head/Visor_north")

    e = Canvas(128)
    e.glow_rect([68, 52, 92, 66], CYAN, 140)
    e.poly([(68, 54), (88, 54), (91, 59), (88, 64), (68, 64)], GUNMETAL)
    e.poly([(71, 56), (86.6, 56), (88.5, 59), (86.6, 62), (71, 62)], CYAN, outline=None)
    e.rect([72, 56.8, 85, 58.2], CYAN_CORE, outline=None, radius=1)
    e.save("Worn/Head/Visor_east")


# ---------------------------------------------------------------- item icons (64x64)

def icon_plating():
    c = Canvas(64)
    plate(c, [12, 20, 44, 46], radius=3)
    plate(c, [20, 14, 52, 40], radius=3)
    c.poly([(22, 15.6), (50, 15.6), (49.6, 17.6), (22.4, 17.6)], STEEL_LIGHT, outline=None)
    c.save("Items/AdditionalPlating")


def icon_bionic_sync():
    c = Canvas(64)
    c.rect([14, 14, 50, 50], (52, 60, 70, 255), radius=4)
    for y in (22, 32, 42):
        c.line([(18, y), (28, y), (32, 32)], GOLD, 1.3, outline=None)
        c.line([(46, y), (36, y), (32, 32)], GOLD, 1.3, outline=None)
    c.glow((32, 32), 9, CYAN, 190)
    c.ellipse([25, 25, 39, 39], GUNMETAL)
    c.dot((32, 32), 4.4, CYAN)
    c.dot((32, 32), 1.8, CYAN_CORE)
    for x in range(18, 48, 6):
        c.rect([x, 9.5, x + 2.5, 14], GOLD, radius=0.5)
        c.rect([x, 50, x + 2.5, 54.5], GOLD, radius=0.5)
    c.save("Items/BionicSynchronization")


def icon_thermal():
    c = Canvas(64)
    fin_stack(c, [12, 14, 40, 50])
    c.line([(40, 24), (50, 24), (50, 44), (40, 44)], CYAN, 2.4)
    c.glow((50, 34), 5, CYAN, 120)
    c.save("Items/ThermalRegulator")


def icon_ablative():
    c = Canvas(64)
    import math
    for cx, cy in [(22, 22), (38, 22), (14, 36), (30, 36), (46, 36), (22, 50), (38, 50)]:
        pts = [(cx + 8.2 * math.cos(math.radians(a)), cy + 8.2 * math.sin(math.radians(a)))
               for a in range(30, 390, 60)]
        c.poly(pts, TILE)
        inner = [(cx + 5 * math.cos(math.radians(a)), cy + 5 * math.sin(math.radians(a)))
                 for a in range(30, 390, 60)]
        c.poly(inner, TILE_LIGHT, outline=None)
        c.dot((cx + 1.2, cy + 1.8), 1.6, TILE_DARK)
    c.save("Items/AblativeShielding")


def icon_trauma():
    c = Canvas(64)
    med_canister(c, [16, 16, 40, 52])
    c.line([(40, 26), (50, 18)], STEEL_DARK, 2.2)
    c.rect([46, 12, 54, 22], RED, radius=1.5)
    c.save("Items/TraumaSuite")


def icon_coprocessor():
    c = Canvas(64)
    for x in range(17, 47, 5):
        c.rect([x, 8, x + 2.5, 14], GOLD, radius=0.5)
        c.rect([x, 50, x + 2.5, 56], GOLD, radius=0.5)
    for y in range(17, 47, 5):
        c.rect([8, y, 14, y + 2.5], GOLD, radius=0.5)
        c.rect([50, y, 56, y + 2.5], GOLD, radius=0.5)
    c.rect([13, 13, 51, 51], GUNMETAL, radius=3)
    c.rect([15, 14.6, 49, 17], GUNMETAL_LIGHT, outline=None, radius=1)
    c.rect([22, 22, 42, 42], (44, 50, 58, 255), radius=2)
    c.glow((32, 32), 8, CYAN, 180)
    c.rect([27, 27, 37, 37], CYAN, outline=None, radius=1.5)
    c.rect([29.5, 29.5, 34.5, 34.5], CYAN_CORE, outline=None, radius=1)
    c.save("Items/CoProcessor")


def icon_stress():
    c = Canvas(64)
    c.line([(10, 40), (20, 30), (32, 27), (44, 30), (54, 40)], GOLD, 3.0)
    for p in [(20, 30), (32, 27), (44, 30)]:
        c.glow(p, 6, PURPLE, 190)
        c.ellipse([p[0] - 4, p[1] - 4, p[0] + 4, p[1] + 4], GUNMETAL)
        c.dot(p, 2.6, PURPLE)
        c.dot(p, 1.0, PURPLE_CORE)
    c.save("Items/StressDampener")


def icon_targeting():
    c = Canvas(64)
    c.line([(18, 46), (14, 10)], STEEL_DARK, 2.0)
    c.glow((14, 10), 4, RED, 190)
    c.dot((14, 10), 2.2, RED)
    c.rect([12, 40, 26, 52], GUNMETAL, radius=2)
    c.line([(26, 46), (34, 40)], GUNMETAL, 2.6)
    c.ellipse([30, 26, 54, 50], GUNMETAL)
    c.glow((42, 38), 9, RED, 170)
    c.ellipse([35, 31, 49, 45], RED, outline=None)
    c.ellipse([38, 34, 43, 39], RED_CORE, outline=None)
    c.save("Items/TargetingUplink")


def icon_visor():
    c = Canvas(64)
    c.glow_rect([6, 22, 58, 42], CYAN, 150)
    c.poly([(8, 26), (56, 26), (54, 40), (32, 44), (10, 40)], GUNMETAL)
    c.poly([(12, 29), (52, 29), (50.6, 37.4), (32, 40.6), (13.4, 37.4)], CYAN, outline=None)
    c.rect([15, 30, 49, 32], CYAN_CORE, outline=None, radius=1)
    c.save("Items/MultispectralVisor")


def icon_biogel():
    c = Canvas(64)
    tube(c, [(14, 50), (20, 32), (16, 14)], width=6)
    tube(c, [(32, 52), (30, 32), (34, 12)], width=6)
    tube(c, [(50, 50), (44, 32), (48, 14)], width=6)
    c.rect([10, 48, 54, 56], STEEL_DARK, radius=2)
    c.rect([10, 8, 54, 16], STEEL_DARK, radius=2)
    c.save("Items/BiogelServos")


def icon_exoframe():
    c = Canvas(64)
    c.rect([12, 10, 52, 16], GUNMETAL, radius=2)
    c.rect([12, 40, 52, 46], GUNMETAL, radius=2)
    c.rect([29, 6, 35, 50], STEEL_DARK, radius=2)
    for y in range(12, 48, 6):
        c.rect([27, y, 37, y + 3.2], STEEL, radius=1.2)
    for x in (16, 48):
        c.line([(x, 46), (x, 58)], STEEL_DARK, 3.0)
        c.ellipse([x - 3.6, 40, x + 3.6, 47.2], GUNMETAL)
        c.dot((x, 43.6), 1.2, AMBER)
    c.save("Items/Exoframe")


# ---------------------------------------------------------------- UI

def ui_modify_armor():
    c = Canvas(64)
    # helmet silhouette
    c.poly([(12, 34), (14, 20), (24, 11), (40, 11), (50, 20), (52, 34), (48, 50), (16, 50)], STEEL)
    c.poly([(16, 31), (48, 31), (46, 39), (18, 39)], GUNMETAL)
    c.rect([20, 33, 44, 37], CYAN, outline=None, radius=1.5)
    c.glow((32, 35), 8, CYAN, 120)
    # wrench
    c.line([(36, 58), (54, 40)], STEEL_LIGHT, 4.0)
    c.ellipse([48, 30, 62, 44], STEEL_LIGHT)
    c.ellipse([53, 32.5, 60, 39.5], (0, 0, 0, 0), outline=None)
    c.save("UI/ModifyArmor")


def ui_category():
    c = Canvas(32)
    c.rect([6, 6, 26, 26], GUNMETAL, radius=2, width=1.2)
    c.glow((16, 16), 5, CYAN, 170)
    c.rect([11, 11, 21, 21], CYAN, outline=None, radius=1.5)
    for v in (9, 14, 19):
        c.rect([v, 2.5, v + 2, 6], GOLD, outline=None, radius=0.5)
        c.rect([v, 26, v + 2, 29.5], GOLD, outline=None, radius=0.5)
    c.save("UI/ModuleCategory")


# ---------------------------------------------------------------- preview

def mannequin(size, facing):
    """Rough marine-armor stand-in used only for previews."""
    c = Canvas(size)
    armor, armor_dark = (98, 108, 92, 255), (70, 78, 66, 255)
    if facing == "east":
        c.rect([52, 86, 66, 114], armor_dark, radius=4)
        c.rect([46, 44, 74, 90], armor, radius=10)
        c.rect([56, 50, 68, 84], armor_dark, radius=5)
    else:
        c.rect([48, 86, 62, 114], armor_dark, radius=4)
        c.rect([66, 86, 80, 114], armor_dark, radius=4)
        c.rect([36, 48, 46, 84], armor_dark, radius=5)
        c.rect([82, 48, 92, 84], armor_dark, radius=5)
        c.rect([42, 44, 86, 90], armor, radius=10)
    body = c.render()
    h = Canvas(size)
    if facing == "east":
        h.ellipse([42, 36, 90, 88], armor)
        h.rect([74, 54, 90, 64], (40, 44, 40, 255), radius=3)
    else:
        h.ellipse([40, 34, 88, 88], armor)
        if facing == "south":
            h.rect([46, 54, 82, 64], (40, 44, 40, 255), radius=3)
    head = h.render()
    return body, head


def preview_sheet(out_path):
    """Every overlay on a stand-in pawn, for eyeballing alignment."""
    body_mods = ["Plating", "ThermalFins", "TraumaSuite", "CoProcessor", "BiogelServos", "Exoframe"]
    head_mods = ["Plating", "NeuralLink", "CoProcessor", "StressDampener", "TargetingUplink", "Visor"]
    cell = 128
    sheet = Image.new("RGBA", (cell * 3 * 2, cell * len(body_mods)), (46, 50, 46, 255))
    for row, (bm, hm) in enumerate(zip(body_mods, head_mods)):
        for col, facing in enumerate(["south", "east", "north"]):
            body, head = mannequin(128, facing)
            frame = Image.new("RGBA", (cell, cell), (0, 0, 0, 0))
            frame.alpha_composite(body)
            ov = Image.open(os.path.join(TEX, f"Worn/Body/{bm}_{facing}.png"))
            frame.alpha_composite(ov)
            head_frame = Image.new("RGBA", (cell, cell), (0, 0, 0, 0))
            head_frame.alpha_composite(head)
            frame.alpha_composite(head_frame, (0, -29))
            sheet.alpha_composite(frame, (col * cell, row * cell))

            body, head = mannequin(128, facing)
            frame = Image.new("RGBA", (cell, cell), (0, 0, 0, 0))
            frame.alpha_composite(body)
            head_frame = Image.new("RGBA", (cell, cell), (0, 0, 0, 0))
            head_frame.alpha_composite(head)
            head_frame.alpha_composite(Image.open(os.path.join(TEX, f"Worn/Head/{hm}_{facing}.png")))
            frame.alpha_composite(head_frame, (0, -29))
            sheet.alpha_composite(frame, ((3 + col) * cell, row * cell))
    sheet.save(out_path)


def about_preview():
    width, height = 1280, 720
    img = Image.new("RGBA", (width, height), (24, 27, 31, 255))
    d = ImageDraw.Draw(img)
    for y in range(height):
        shade = int(24 + 18 * (y / height))
        d.line([(0, y), (width, y)], fill=(shade, shade + 3, shade + 7, 255))
    font_dir = "/usr/share/fonts/truetype/dejavu"
    try:
        title_font = ImageFont.truetype(os.path.join(font_dir, "DejaVuSans-Bold.ttf"), 72)
        sub_font = ImageFont.truetype(os.path.join(font_dir, "DejaVuSans.ttf"), 30)
    except OSError:
        title_font = sub_font = ImageFont.load_default()
    d.text((80, 70), "Modular Power Armor", font=title_font, fill=(225, 232, 238, 255))
    d.text((84, 170), "Install modifications into power armor like bionics into pawns.", font=sub_font,
           fill=(150, 205, 230, 255))
    icons = ["AdditionalPlating", "BionicSynchronization", "ThermalRegulator", "AblativeShielding",
             "TraumaSuite", "CoProcessor", "StressDampener", "TargetingUplink", "MultispectralVisor",
             "BiogelServos", "Exoframe"]
    x, y = 80, 270
    for i, name in enumerate(icons):
        icon = Image.open(os.path.join(TEX, f"Items/{name}.png")).resize((128, 128), Image.LANCZOS)
        px, py = x + (i % 6) * 190, y + (i // 6) * 190
        d.rounded_rectangle([px - 14, py - 14, px + 142, py + 142], radius=16, fill=(44, 50, 58, 255),
                            outline=(80, 92, 104, 255), width=3)
        img.alpha_composite(icon, (px, py))
    img.convert("RGB").save(os.path.join(ROOT, "About", "Preview.png"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--preview", help="also write an overlay alignment sheet to this path")
    args = parser.parse_args()

    for fn in (body_plating, body_thermal_fins, body_trauma_suite, body_coprocessor, body_biogel_servos,
               body_exoframe, head_plating, head_neural_link, head_coprocessor, head_stress_dampener,
               head_targeting_uplink, head_visor, icon_plating, icon_bionic_sync, icon_thermal, icon_ablative,
               icon_trauma, icon_coprocessor, icon_stress, icon_targeting, icon_visor, icon_biogel,
               icon_exoframe, ui_modify_armor, ui_category):
        fn()
    about_preview()
    if args.preview:
        preview_sheet(args.preview)
    print("Textures written to", TEX)


if __name__ == "__main__":
    main()
