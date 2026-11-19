"""
make_sample_images.py
---------------------
Draws the KWARKO logo and simple illustrated photos for the sample dorms
(building exterior + two room interiors per dorm) using Pillow.

The images are already included in assets/, so you normally don't need to run
this. It runs automatically if the sample images are missing, and you can run it
yourself with:   python make_sample_images.py

Tip for your presentation: replace the files in assets/images/ with real photos
(keep the same file names) or upload real photos from the Landlord Dashboard.
"""

import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

BASE_DIR = Path(__file__).resolve().parent
IMG_DIR = BASE_DIR / "assets" / "images"
W, H = 960, 640

NAVY = (11, 36, 71)
ORANGE = (242, 140, 40)


# ---------------------------------------------------------------- helpers
def mix(c1, c2, t):
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))


def shade(c, f):
    return tuple(max(0, min(255, int(v * f))) for v in c)


def vgrad(img, box, top, bottom):
    d = ImageDraw.Draw(img)
    x0, y0, x1, y1 = box
    for y in range(y0, y1):
        d.line([(x0, y), (x1, y)], fill=mix(top, bottom, (y - y0) / max(1, y1 - y0 - 1)))


def get_font(size):
    for name in ("DejaVuSans-Bold.ttf", "arialbd.ttf", "Arial Bold.ttf",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def soft_shadow(img, box, opacity=70, blur=14):
    layer = Image.new("L", img.size, 0)
    ImageDraw.Draw(layer).ellipse(box, fill=opacity)
    layer = layer.filter(ImageFilter.GaussianBlur(blur))
    img.paste((20, 20, 30), (0, 0), layer)


def vignette(img):
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).rectangle([0, 0, W, H], outline=60, width=40)
    mask = mask.filter(ImageFilter.GaussianBlur(60))
    img.paste((10, 20, 40), (0, 0), mask)


# ---------------------------------------------------------------- rooms
WALLS = [(234, 240, 248), (247, 238, 225), (228, 241, 234), (241, 234, 242), (250, 245, 232)]
BLANKETS = [ORANGE, (25, 55, 109), (84, 140, 200), (196, 92, 72), (90, 150, 120), (150, 110, 170)]
WOODS = [(196, 154, 108), (172, 126, 86), (214, 180, 138)]


def draw_bed(img, x0, x1, base_y, blanket, wood, height=1.0):
    """Side view of a single bed whose legs touch base_y."""
    d = ImageDraw.Draw(img)
    s = height
    d.rounded_rectangle([x1 - 26, base_y - int(170 * s), x1, base_y], 8, fill=shade(wood, 0.85))   # headboard
    d.rounded_rectangle([x0, base_y - int(105 * s), x0 + 22, base_y], 6, fill=shade(wood, 0.85))   # footboard
    d.rectangle([x0 + 10, base_y - int(55 * s), x1 - 10, base_y - int(30 * s)], fill=shade(wood, 0.7))  # rail
    d.rounded_rectangle([x0 + 18, base_y - int(95 * s), x1 - 22, base_y - int(55 * s)], 10, fill=(246, 246, 244))
    d.rounded_rectangle([x1 - 120, base_y - int(122 * s), x1 - 34, base_y - int(88 * s)], 14, fill=(255, 255, 255),
                        outline=(225, 225, 225))
    d.rounded_rectangle([x0 + 14, base_y - int(100 * s), x1 - 135, base_y - int(48 * s)], 12, fill=blanket)
    d.line([(x0 + 40, base_y - int(78 * s)), (x1 - 150, base_y - int(78 * s))], fill=shade(blanket, 0.85), width=3)


def draw_room(rng, kind):
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img)
    wall, wood = rng.choice(WALLS), rng.choice(WOODS)
    floor_y = 410
    vgrad(img, (0, 0, W, floor_y), shade(wall, 1.03), shade(wall, 0.92))
    vgrad(img, (0, floor_y, W, H), shade(wood, 1.0), shade(wood, 0.8))
    for i in range(-9, 10):                                   # floor planks
        d.line([(W // 2 + i * 60, floor_y), (W // 2 + i * 130, H)], fill=shade(wood, 0.8), width=2)
    for y in (floor_y + 45, floor_y + 105, floor_y + 180):
        d.line([(0, y), (W, y)], fill=shade(wood, 0.88), width=1)
    d.rectangle([0, floor_y - 14, W, floor_y], fill=shade(wall, 0.8))   # baseboard

    # window with sky, sun, hills and curtains
    wx0, wy0, wx1, wy1 = (70, 70, 320, 300) if kind != "twin" else (360, 60, 600, 270)
    vgrad(img, (wx0, wy0, wx1, wy1), (120, 185, 238), (214, 236, 250))
    d.ellipse([wx1 - 90, wy0 + 25, wx1 - 40, wy0 + 75], fill=(255, 236, 170))
    d.polygon([(wx0, wy1), (wx0, wy1 - 60), (wx0 + 90, wy1 - 95), (wx0 + 180, wy1 - 55), (wx1, wy1 - 80), (wx1, wy1)],
              fill=(120, 175, 120))
    d.rectangle([wx0, wy0, wx1, wy1], outline=(255, 255, 255), width=12)
    d.line([((wx0 + wx1) // 2, wy0), ((wx0 + wx1) // 2, wy1)], fill=(255, 255, 255), width=8)
    d.rectangle([wx0 - 14, wy1, wx1 + 14, wy1 + 14], fill=(250, 250, 250))
    curtain = rng.choice([ORANGE, (84, 140, 200), (210, 200, 180), (160, 190, 160)])
    d.line([(wx0 - 60, wy0 - 22), (wx1 + 60, wy0 - 22)], fill=(90, 90, 90), width=5)
    for cx in (wx0 - 55, wx1 + 5):
        d.rectangle([cx, wy0 - 20, cx + 50, wy1 + 40], fill=curtain)
        for k in range(1, 4):
            d.line([(cx + k * 12, wy0 - 20), (cx + k * 12, wy1 + 40)], fill=shade(curtain, 0.85), width=2)

    # wall art
    ax = 420 if kind != "twin" else 680
    d.rectangle([ax, 100, ax + 130, 220], fill=(255, 255, 255), outline=shade(wood, 0.6), width=6)
    d.ellipse([ax + 20, 120, ax + 70, 170], fill=ORANGE)
    d.polygon([(ax + 18, 205), (ax + 70, 150), (ax + 112, 205)], fill=NAVY)

    blanket = rng.choice(BLANKETS)
    if kind == "bunk":                       # double-deck bed for bedspace rooms
        x0, x1 = 520, 920
        soft_shadow(img, (x0 - 10, 570, x1 + 20, 610))
        for x in (x0 - 6, x1 - 18):
            d.rectangle([x, 150, x + 18, 590], fill=shade(wood, 0.75))
        draw_bed(img, x0, x1, 590, blanket, wood, 0.75)
        draw_bed(img, x0, x1, 360, rng.choice(BLANKETS), wood, 0.75)
        for y in range(380, 590, 40):         # ladder
            d.line([(x0 + 30, y), (x0 + 70, y)], fill=shade(wood, 0.6), width=6)
        d.line([(x0 + 30, 340), (x0 + 30, 590)], fill=shade(wood, 0.6), width=6)
        d.line([(x0 + 70, 340), (x0 + 70, 590)], fill=shade(wood, 0.6), width=6)
    else:
        soft_shadow(img, (540, 570, 940, 610))
        draw_bed(img, 540, 920, 590, blanket, wood)

    if kind == "twin":                       # second bed + night stand
        soft_shadow(img, (30, 570, 400, 610))
        draw_bed(img, 40, 380, 590, rng.choice(BLANKETS), wood)
        d.rectangle([420, 470, 500, 590], fill=shade(wood, 0.9))
        d.rectangle([430, 500, 490, 520], fill=shade(wood, 0.7))
        d.ellipse([440, 455, 480, 472], fill=(80, 80, 80))
        d.line([(460, 455), (460, 400)], fill=(80, 80, 80), width=4)
        d.polygon([(435, 400), (485, 400), (475, 365), (445, 365)], fill=(255, 230, 180))
    else:                                    # study desk, lamp, laptop, chair and plant
        soft_shadow(img, (40, 575, 380, 610))
        d.rectangle([50, 430, 360, 448], fill=shade(wood, 0.75))
        d.rectangle([62, 448, 76, 595], fill=shade(wood, 0.6))
        d.rectangle([334, 448, 348, 595], fill=shade(wood, 0.6))
        d.rectangle([250, 448, 334, 540], fill=shade(wood, 0.82))
        d.ellipse([280, 488, 304, 500], fill=shade(wood, 0.5))
        d.polygon([(120, 430), (210, 430), (220, 424), (110, 424)], fill=(60, 60, 70))   # laptop base
        d.polygon([(125, 424), (205, 424), (195, 368), (135, 368)], fill=(70, 75, 90))   # laptop screen
        d.polygon([(132, 420), (198, 420), (190, 374), (140, 374)], fill=(140, 190, 235))
        d.ellipse([280, 418, 320, 432], fill=(60, 60, 60))
        d.line([(300, 420), (280, 360)], fill=(60, 60, 60), width=5)
        d.polygon([(255, 360), (305, 355), (290, 330), (262, 333)], fill=ORANGE)
        d.rounded_rectangle([150, 470, 230, 500], 8, fill=NAVY)                          # chair
        d.rectangle([186, 500, 194, 590], fill=(70, 70, 70))
        d.rounded_rectangle([140, 380, 160, 500], 6, fill=NAVY)
        d.polygon([(420, 590), (480, 590), (488, 530), (412, 530)], fill=(200, 110, 70))  # plant
        for (lx, ly, r) in [(450, 490, 34), (420, 505, 26), (480, 505, 26), (450, 460, 26)]:
            d.ellipse([lx - r, ly - r, lx + r, ly + r], fill=rng.choice([(70, 140, 90), (90, 160, 100), (60, 120, 80)]))
    vignette(img)
    return img


# ---------------------------------------------------------------- exterior
BUILDING_COLORS = [(244, 232, 210), (220, 232, 245), (236, 214, 200), (232, 236, 228), (250, 242, 225)]


def draw_tree(d, x, ground, rng):
    d.rectangle([x - 8, ground - 110, x + 8, ground], fill=(110, 80, 55))
    for (dx, dy, r) in [(0, -150, 52), (-38, -118, 40), (38, -118, 40), (0, -105, 42)]:
        d.ellipse([x + dx - r, ground + dy - r, x + dx + r, ground + dy + r],
                  fill=rng.choice([(70, 140, 90), (85, 155, 95), (60, 125, 80)]))


def draw_exterior(rng, name, style):
    img = Image.new("RGB", (W, H))
    vgrad(img, (0, 0, W, H), (105, 165, 228), (215, 233, 250))
    clouds = Image.new("L", img.size, 0)
    cd = ImageDraw.Draw(clouds)
    for _ in range(5):
        cx, cy = rng.randint(0, W), rng.randint(30, 170)
        for k in range(4):
            cd.ellipse([cx + k * 35 - 50, cy - 25 - (k % 2) * 15, cx + k * 35 + 30, cy + 25], fill=200)
    img.paste((255, 255, 255), (0, 0), clouds.filter(ImageFilter.GaussianBlur(6)))
    d = ImageDraw.Draw(img)
    ground = 540
    d.polygon([(0, ground), (0, 400), (150, 360), (330, 410), (520, 350), (760, 400), (W, 370), (W, ground)],
              fill=(176, 202, 226))                                  # far hills / city
    d.rectangle([0, ground - 18, W, ground], fill=(110, 170, 100))   # grass
    d.rectangle([0, ground, W, H], fill=(200, 200, 205))             # sidewalk
    d.rectangle([0, ground + 50, W, H], fill=(120, 124, 132))        # road
    for x in range(0, W, 120):
        d.rectangle([x + 20, ground + 80, x + 80, ground + 88], fill=(240, 240, 240))

    color = rng.choice(BUILDING_COLORS)
    floors = rng.choice([3, 4]) if style == "apartment" else 2
    floor_h = 92
    bx0, bx1 = 230, 730
    by0 = ground - floors * floor_h - 20
    soft_shadow(img, (bx0 - 20, ground - 20, bx1 + 80, ground + 20), 90, 10)
    d.polygon([(bx1, by0), (bx1 + 60, by0 - 28), (bx1 + 60, ground - 28), (bx1, ground)], fill=shade(color, 0.78))
    d.rectangle([bx0, by0, bx1, ground], fill=color)
    if style == "apartment":
        d.rectangle([bx0 - 8, by0 - 18, bx1 + 8, by0], fill=shade(color, 0.7))
        d.polygon([(bx0 - 8, by0 - 18), (bx0 + 52, by0 - 46), (bx1 + 68, by0 - 46), (bx1 + 8, by0 - 18)],
                  fill=shade(color, 0.85))
    else:
        roof = rng.choice([(176, 72, 52), NAVY, (90, 100, 110)])
        d.polygon([(bx0 - 30, by0 + 4), ((bx0 + bx1) // 2 + 30, by0 - 120), (bx1 + 90, by0 - 20), (bx1 + 30, by0 + 4)],
                  fill=roof)
        d.polygon([(bx0 - 30, by0 + 4), ((bx0 + bx1) // 2 + 30, by0 - 120), (bx1 + 30, by0 + 4)], fill=shade(roof, 1.15))

    win_glass = (150, 195, 235)
    for f in range(1, floors):                                  # upper floors
        y = ground - (f + 1) * floor_h + 8
        for c in range(5):
            x = bx0 + 30 + c * 95
            lit = rng.random() < 0.3
            d.rectangle([x, y, x + 62, y + 58], fill=(255, 224, 150) if lit else win_glass,
                        outline=(255, 255, 255), width=5)
            d.line([(x + 31, y), (x + 31, y + 58)], fill=(255, 255, 255), width=3)
        if style == "apartment" and f % 2 == 1:                # balcony rail
            d.rectangle([bx0 + 20, y + 62, bx1 - 20, y + 68], fill=shade(color, 0.6))
    # ground floor: door, awning and sign board
    cx = (bx0 + bx1) // 2
    d.rectangle([cx - 45, ground - 105, cx + 45, ground], fill=(120, 80, 50))
    d.rectangle([cx - 35, ground - 95, cx + 35, ground - 40], fill=win_glass)
    for x in (bx0 + 30, bx1 - 122):
        d.rectangle([x, ground - 90, x + 92, ground - 30], fill=win_glass, outline=(255, 255, 255), width=5)
    d.polygon([(cx - 80, ground - 112), (cx + 80, ground - 112), (cx + 95, ground - 90), (cx - 95, ground - 90)],
              fill=ORANGE)
    sign_y = ground - floor_h - 12 if floors > 1 else by0 + 10
    font_size = 30
    font = get_font(font_size)
    while d.textlength(name, font=font) > (bx1 - bx0 - 80) and font_size > 12:
        font_size -= 2
        font = get_font(font_size)
    tw = d.textlength(name, font=font)
    d.rounded_rectangle([cx - tw / 2 - 18, sign_y - 4, cx + tw / 2 + 18, sign_y + font_size + 14], 8, fill=NAVY)
    d.text((cx - tw / 2, sign_y + 4), name, font=font, fill=(255, 255, 255))

    draw_tree(d, 140, ground, rng)
    draw_tree(d, 850, ground, rng)
    d.rectangle([0, ground - 34, bx0 - 40, ground - 26], fill=(240, 240, 240))   # low fence
    vignette(img)
    return img


# ---------------------------------------------------------------- logo
def draw_logo(size=512):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    s = size / 512
    d.rounded_rectangle([0, 0, size - 1, size - 1], int(120 * s), fill=NAVY)
    d.line([(96 * s, 250 * s), (256 * s, 110 * s), (416 * s, 250 * s)], fill=ORANGE, width=int(46 * s), joint="curve")
    font = get_font(int(230 * s))
    tw = d.textlength("K", font=font)
    d.text(((size - tw) / 2, 205 * s), "K", font=font, fill=(255, 255, 255))
    return img


def generate_all():
    """Create the logo and every sample photo used by the seed data."""
    from database import SAMPLE_PROPERTIES, sample_image_paths

    IMG_DIR.mkdir(parents=True, exist_ok=True)
    draw_logo().save(BASE_DIR / "assets" / "logo.png")
    for idx, prop in enumerate(SAMPLE_PROPERTIES, start=1):
        rng = random.Random(idx * 7)
        types = [room[1] for room in prop["rooms"]]
        exterior, room1, room2 = sample_image_paths(idx)
        draw_exterior(rng, prop["name"], prop["style"]).save(BASE_DIR / exterior, quality=86)
        draw_room(rng, "bunk" if "Bedspace" in types else "single").save(BASE_DIR / room1, quality=86)
        draw_room(rng, "twin" if "Shared" in types else "single").save(BASE_DIR / room2, quality=86)


def ensure_sample_images():
    """Called by app.py: only generates the images if they are missing."""
    if not (BASE_DIR / "assets" / "logo.png").exists() or not (IMG_DIR / "dorm01_1.jpg").exists():
        generate_all()


if __name__ == "__main__":
    generate_all()
    print("Sample images created in", IMG_DIR)
