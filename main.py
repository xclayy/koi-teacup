#!/usr/bin/env python3
"""
make.fun bounty: ai-excited-01 — "Make the AI judge excited"

Procedural image (stdlib only): a colossal glowing koi fish leaps out of
a tiny teacup on a wooden table at dusk. Scale inversion, one dominant
diagonal focal shape, warm gold light against deep blue/teal dusk,
water arcing behind it, petals drifting in the air.

Writes $MAKEFUN_OUTPUT_DIR/entry.png (default /output).
Deterministic: fixed seed, pure math. No network, no third-party libs.
PNG is encoded by hand (struct + zlib + binascii.crc32).
"""

import binascii
import math
import os
import random
import struct
import zlib

W, H = 1024, 1024
SEED = 20261116
OUT_DIR = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")

buf = bytearray(W * H * 3)
rnd = random.Random(SEED)


# ---------------------------------------------------------------- helpers
def lerp(a, b, t):
    return a + (b - a) * t


def mix(c1, c2, t):
    return (int(lerp(c1[0], c2[0], t)),
            int(lerp(c1[1], c2[1], t)),
            int(lerp(c1[2], c2[2], t)))


def _gradient_rows(y0, y1, stops):
    """Return a list of RGB tuples, one per row, interpolating stops."""
    rows = []
    n = y1 - y0
    for y in range(y0, y1):
        t = (y - y0) / max(1, n - 1)
        for i in range(len(stops) - 1):
            t0, c0 = stops[i]
            t1, c1 = stops[i + 1]
            if t0 <= t <= t1:
                rows.append(mix(c0, c1, (t - t0) / max(1e-9, t1 - t0)))
                break
        else:
            rows.append(stops[-1][1])
    return rows


def fill_rows(y0, y1, colors):
    """Fill rows y0..y1-1 with the given per-row RGB colours (fast)."""
    for k, y in enumerate(range(y0, min(y1, H))):
        r, g, b = colors[k]
        i = y * W * 3
        buf[i:i + W * 3] = bytes((r, g, b)) * W


def fill_row_span(y, x0, x1, color):
    """Opaque horizontal span on one row."""
    if y < 0 or y >= H:
        return
    x0 = max(0, x0)
    x1 = min(W - 1, x1)
    if x1 < x0:
        return
    r, g, b = color
    i = (y * W + x0) * 3
    n = x1 - x0 + 1
    buf[i:i + n * 3] = bytes((r, g, b)) * n


def disc(cx, cy, rad, color, alpha=255):
    """Filled circle, optionally translucent."""
    r, g, b = color
    x0 = max(0, int(cx - rad))
    x1 = min(W - 1, int(cx + rad))
    y0 = max(0, int(cy - rad))
    y1 = min(H - 1, int(cy + rad))
    r2 = rad * rad
    if alpha >= 255:
        for y in range(y0, y1 + 1):
            dy = y - cy
            dx = math.sqrt(max(0.0, r2 - dy * dy))
            xa = max(x0, int(cx - dx))
            xb = min(x1, int(cx + dx))
            i = (y * W + xa) * 3
            n = xb - xa + 1
            buf[i:i + n * 3] = bytes((r, g, b)) * n
    else:
        ia = 255 - alpha
        for y in range(y0, y1 + 1):
            dy = y - cy
            dx = math.sqrt(max(0.0, r2 - dy * dy))
            xa = max(x0, int(cx - dx))
            xb = min(x1, int(cx + dx))
            for x in range(xa, xb + 1):
                i = (y * W + x) * 3
                buf[i] = (r * alpha + buf[i] * ia) // 255
                buf[i + 1] = (g * alpha + buf[i + 1] * ia) // 255
                buf[i + 2] = (b * alpha + buf[i + 2] * ia) // 255


def ellipse(cx, cy, rx, ry, ang, color, alpha=255):
    """Filled rotated ellipse, optionally translucent."""
    r, g, b = color
    ca, sa = math.cos(ang), math.sin(ang)
    hx = math.sqrt(rx * rx * ca * ca + ry * ry * sa * sa)
    hy = math.sqrt(rx * rx * sa * sa + ry * ry * ca * ca)
    x0 = max(0, int(cx - hx))
    x1 = min(W - 1, int(cx + hx))
    y0 = max(0, int(cy - hy))
    y1 = min(H - 1, int(cy + hy))
    irx = 1.0 / (rx * rx)
    iry = 1.0 / (ry * ry)
    ia = 255 - alpha
    for y in range(y0, y1 + 1):
        dy = y - cy
        for x in range(x0, x1 + 1):
            dx = x - cx
            px = dx * ca + dy * sa
            py = -dx * sa + dy * ca
            if px * px * irx + py * py * iry <= 1.0:
                i = (y * W + x) * 3
                if alpha >= 255:
                    buf[i] = r
                    buf[i + 1] = g
                    buf[i + 2] = b
                else:
                    buf[i] = (r * alpha + buf[i] * ia) // 255
                    buf[i + 1] = (g * alpha + buf[i + 1] * ia) // 255
                    buf[i + 2] = (b * alpha + buf[i + 2] * ia) // 255


def glow(cx, cy, rad, color, peak_alpha):
    """Soft radial glow, alpha falling off as (1 - d^2/r^2)^2."""
    r, g, b = color
    x0 = max(0, int(cx - rad))
    x1 = min(W - 1, int(cx + rad))
    y0 = max(0, int(cy - rad))
    y1 = min(H - 1, int(cy + rad))
    inv = 1.0 / (rad * rad)
    for y in range(y0, y1 + 1):
        dy = y - cy
        dy2 = dy * dy
        base = y * W
        for x in range(x0, x1 + 1):
            dx = x - cx
            d2 = (dx * dx + dy2) * inv
            if d2 >= 1.0:
                continue
            f = 1.0 - d2
            a = int(peak_alpha * f * f)
            if a <= 0:
                continue
            ia = 255 - a
            i = (base + x) * 3
            buf[i] = (r * a + buf[i] * ia) // 255
            buf[i + 1] = (g * a + buf[i + 1] * ia) // 255
            buf[i + 2] = (b * a + buf[i + 2] * ia) // 255


def bez(p0, p1, p2, p3, t):
    u = 1.0 - t
    return (u * u * u * p0[0] + 3 * u * u * t * p1[0]
            + 3 * u * t * t * p2[0] + t * t * t * p3[0],
            u * u * u * p0[1] + 3 * u * u * t * p1[1]
            + 3 * u * t * t * p2[1] + t * t * t * p3[1])




# ---------------------------------------------------------------- scene
def draw_sky():
    stops = [(0.00, (10, 14, 42)),
             (0.35, (22, 54, 94)),
             (0.62, (46, 107, 116)),
             (0.80, (201, 123, 74)),
             (1.00, (242, 166, 94))]
    fill_rows(0, 800, _gradient_rows(0, 800, stops))
    # stars in the upper sky
    for _ in range(90):
        x = rnd.randrange(0, W)
        y = rnd.randrange(0, 360)
        a = rnd.randrange(100, 235)
        disc(x, y, rnd.choice((1, 1, 2)), (255, 255, 240), a)
    # low sun + warm glow behind the koi's head
    glow(855, 275, 300, (255, 179, 71), 95)
    glow(855, 275, 150, (255, 205, 110), 110)
    disc(855, 275, 46, (255, 233, 168))
    disc(855, 275, 34, (255, 244, 205))


def draw_hills_and_mist():
    # distant dark-teal hills: wide flat humps, only tops show above the table
    ellipse(150, 828, 320, 70, 0.0, (26, 58, 74))
    ellipse(500, 832, 380, 80, 0.0, (26, 58, 74))
    ellipse(880, 828, 300, 65, 0.0, (26, 58, 74))
    # soft mist bands hugging the horizon
    ellipse(300, 772, 260, 16, 0.0, (207, 232, 234), 30)
    ellipse(700, 780, 300, 18, 0.0, (207, 232, 234), 26)
    ellipse(520, 786, 340, 14, 0.0, (230, 220, 200), 22)


def draw_table():
    stops = [(0.0, (122, 74, 38)), (1.0, (84, 48, 26))]
    fill_rows(800, H, _gradient_rows(800, H, stops))
    # bright edge where the table meets the sky
    fill_row_span(800, 0, W - 1, (160, 106, 53))
    fill_row_span(801, 0, W - 1, (140, 90, 45))
    # plank seams + highlights
    for y in (850, 900, 950, 1000):
        fill_row_span(y, 0, W - 1, (74, 42, 18))
        fill_row_span(y + 1, 0, W - 1, (74, 42, 18))
        fill_row_span(y + 2, 0, W - 1, (138, 90, 48))
    # wavy wood grain streaks
    for _ in range(22):
        y0 = rnd.randrange(812, 1012)
        ph = rnd.uniform(0, 6.28)
        amp = rnd.uniform(0.5, 2.0)
        for x in range(0, W, 2):
            y = y0 + int(amp * math.sin(x * 0.01 + ph))
            if 802 <= y < H:
                i = (y * W + x) * 3
                a = 28
                ia = 255 - a
                buf[i] = (46 * a + buf[i] * ia) // 255
                buf[i + 1] = (24 * a + buf[i + 1] * ia) // 255
                buf[i + 2] = (8 * a + buf[i + 2] * ia) // 255


def draw_cup():
    # soft shadow under the saucer
    ellipse(430, 862, 115, 16, 0.0, (42, 21, 8), 80)
    # saucer
    ellipse(430, 848, 100, 23, 0.0, (243, 230, 200))
    ellipse(430, 846, 80, 17, 0.0, (251, 243, 221))
    # cup body: row spans, taller and slightly tapered, shaded top to bottom
    cream_top = (250, 240, 216)
    cream_bot = (224, 202, 168)
    for y in range(790, 850):
        if y <= 836:
            hw = 52 - (y - 790) * 12 / 46.0
        else:
            f = (y - 836) / 13.0
            hw = 40 * math.sqrt(max(0.0, 1.0 - f * f))
        col = mix(cream_top, cream_bot, (y - 790) / 59.0)
        fill_row_span(y, int(430 - hw), int(430 + hw), col)
    # blue porcelain band + thin gold line
    for y in range(802, 813):
        hw = 52 - (y - 790) * 12 / 46.0
        fill_row_span(y, int(430 - hw), int(430 + hw), (47, 93, 138))
    for y in (813, 814):
        hw = 52 - (y - 790) * 12 / 46.0
        fill_row_span(y, int(430 - hw), int(430 + hw), (217, 164, 65))
    # mouth: gold rim ring around pale tea/water
    ellipse(430, 790, 53, 12, 0.0, (217, 164, 65))
    ellipse(430, 790, 49, 9, 0.0, (183, 223, 232))
    # handle: arc of small discs on the right side
    for k in range(13):
        ang = math.radians(-75 + k * 12.5)
        disc(486 + 17 * math.cos(ang), 816 + 17 * math.sin(ang),
             6, (246, 234, 208))


def koi_radius(t):
    base = 16 + 52 * math.sin(math.pi * (0.08 + 0.80 * t))
    taper = 1.0 if t >= 0.08 else 0.55 + 0.45 * (t / 0.08)
    return base * taper


KOI_P0 = (465, 790)   # tail, just above the cup mouth
KOI_P1 = (630, 690)
KOI_P2 = (600, 470)
KOI_P3 = (825, 320)   # head, up by the sun


def koi_spine(t):
    """Spine of the fish: cubic bezier plus a perpendicular sine offset
    that bends it into an S (zero offset at tail, mid-body and head)."""
    x, y = bez(KOI_P0, KOI_P1, KOI_P2, KOI_P3, t)
    dx = KOI_P3[0] - KOI_P0[0]
    dy = KOI_P3[1] - KOI_P0[1]
    m = math.hypot(dx, dy)
    nx, ny = dy / m, -dx / m
    off = 58 * math.sin(2 * math.pi * t)
    return x + nx * off, y + ny * off


def koi_tangent(t):
    e = 0.01
    x0, y0 = koi_spine(max(0.0, t - e))
    x1, y1 = koi_spine(min(1.0, t + e))
    m = math.hypot(x1 - x0, y1 - y0) or 1.0
    return (x1 - x0) / m, (y1 - y0) / m


def draw_koi():
    sun_dir = (0.7, -0.7)  # light comes from the upper right

    # halo of warm light around the whole fish
    for t in (0.2, 0.4, 0.6, 0.8):
        x, y = koi_spine(t)
        glow(x, y, 210, (255, 190, 110), 42)

    # flowing tail fins (drawn first so the body covers their bases),
    # fanning up-left into the air, clear of the saucer
    ellipse(378, 772, 50, 14, math.radians(-18), (242, 163, 94), 185)
    ellipse(372, 812, 46, 13, math.radians(28), (247, 201, 138), 180)
    ellipse(405, 738, 42, 12, math.radians(-48), (232, 127, 58), 185)

    # dark outline, then the white body, as overlapping discs
    outline = (22, 40, 62)
    body = (250, 244, 232)
    n = 130
    pts = [koi_spine(i / (n - 1)) for i in range(n)]
    for (x, y), t in zip(pts, [i / (n - 1) for i in range(n)]):
        disc(x, y, koi_radius(t) + 4, outline)
    for (x, y), t in zip(pts, [i / (n - 1) for i in range(n)]):
        disc(x, y, koi_radius(t), body)

    # orange kohaku patches along the body: elongated, off-centre,
    # each with a satellite blob so no marking is a perfect circle
    for t, rx, ryf, off, sat in (
            (0.32, 46, 0.42, 8, 30), (0.55, 50, 0.44, -10, 34),
            (0.76, 44, 0.42, 7, 28), (0.90, 30, 0.40, -6, 20)):
        x, y = koi_spine(t)
        tx, ty = koi_tangent(t)
        nx, ny = -ty, tx
        ang = math.atan2(ty, tx)
        ellipse(x + nx * off, y + ny * off, rx, koi_radius(t) * ryf,
                ang, (224, 90, 30))
        ellipse(x + tx * sat + nx * off * 0.5,
                y + ty * sat + ny * off * 0.5,
                rx * 0.45, koi_radius(t) * ryf * 0.7,
                ang, (214, 74, 28))

    # dorsal fin on the upper mid-body
    x, y = koi_spine(0.45)
    tx, ty = koi_tangent(0.45)
    nx, ny = -ty, tx
    if nx * sun_dir[0] + ny * sun_dir[1] < 0:
        nx, ny = -nx, -ny
    ellipse(x + nx * koi_radius(0.45) * 0.85,
            y + ny * koi_radius(0.45) * 0.85,
            26, 10, math.atan2(ty, tx), (232, 100, 42), 220)
    # pectoral fin near the head, lower side
    x, y = koi_spine(0.85)
    tx, ty = koi_tangent(0.85)
    nx, ny = ty, -tx
    if nx * sun_dir[0] + ny * sun_dir[1] > 0:
        nx, ny = -nx, -ny
    ellipse(x + nx * koi_radius(0.85) * 0.8,
            y + ny * koi_radius(0.85) * 0.8,
            20, 9, math.atan2(ty, tx), (242, 176, 106), 200)

    # gold rim light along the sun-facing edge
    for i in range(n):
        t = i / (n - 1)
        x, y = pts[i]
        tx, ty = koi_tangent(t)
        nx, ny = -ty, tx
        if nx * sun_dir[0] + ny * sun_dir[1] < 0:
            nx, ny = -nx, -ny
        disc(x + nx * koi_radius(t) * 0.92,
             y + ny * koi_radius(t) * 0.92, 5, (255, 210, 122), 180)
    for i in range(0, n, 3):
        t = i / (n - 1)
        x, y = pts[i]
        tx, ty = koi_tangent(t)
        nx, ny = -ty, tx
        if nx * sun_dir[0] + ny * sun_dir[1] < 0:
            nx, ny = -nx, -ny
        disc(x + nx * koi_radius(t) * 0.99,
             y + ny * koi_radius(t) * 0.99, 3, (255, 233, 173), 255)

    # eye, mouth, whiskers
    hx, hy = KOI_P3
    disc(hx + 14, hy - 10, 9, (16, 20, 24))
    disc(hx + 11, hy - 13, 3, (255, 255, 255))
    tx, ty = koi_tangent(1.0)
    ellipse(hx + tx * 38, hy + ty * 38, 10, 5,
            math.atan2(ty, tx), (122, 47, 22), 200)
    for (cx0, cy0, cx1, cy1, cx2, cy2) in (
            (hx + 20, hy + 6, hx + 44, hy + 18, hx + 52, hy + 42),
            (hx + 12, hy + 12, hx + 30, hy + 30, hx + 30, hy + 56)):
        for k in range(13):
            t = k / 12.0
            u = 1 - t
            x = u * u * cx0 + 2 * u * t * cx1 + t * t * cx2
            y = u * u * cy0 + 2 * u * t * cy1 + t * t * cy2
            disc(x, y, 2.5, (247, 217, 160), 220)


def draw_water():
    sun_dir = (0.7, -0.7)
    # continuous thin stream trailing the belly side of the fish
    for i in range(101):
        t = 0.05 + 0.70 * i / 100.0
        x, y = koi_spine(t)
        tx, ty = koi_tangent(t)
        nx, ny = ty, -tx
        if nx * sun_dir[0] + ny * sun_dir[1] > 0:
            nx, ny = -nx, -ny
        disc(x + nx * (koi_radius(t) + 18),
             y + ny * (koi_radius(t) + 18), 5, (168, 220, 232), 130)
    # droplets arcing off the stream
    for i in range(130):
        t = 0.03 + 0.75 * rnd.random()
        x, y = koi_spine(t)
        tx, ty = koi_tangent(t)
        nx, ny = ty, -tx
        if nx * sun_dir[0] + ny * sun_dir[1] > 0:
            nx, ny = -nx, -ny
        off = koi_radius(t) + 14 + rnd.random() * 38
        jx = rnd.uniform(-10, 10)
        jy = rnd.uniform(-10, 10)
        disc(x + nx * off + jx, y + ny * off + jy,
             2.5 + 4.5 * rnd.random(), (216, 241, 247),
             rnd.randrange(170, 245))
    # splash bursting out of the cup mouth
    for _ in range(26):
        ang = math.radians(rnd.uniform(-160, -20))
        d = rnd.uniform(12, 95)
        disc(430 + d * math.cos(ang), 788 + d * math.sin(ang),
             2 + 4 * rnd.random(), (230, 246, 250),
             rnd.randrange(180, 245))
    # a few big foreground drops near the cup
    for _ in range(8):
        disc(rnd.uniform(330, 520), rnd.uniform(700, 830),
             4 + 4 * rnd.random(), (216, 241, 247),
             rnd.randrange(150, 220))


def draw_petals():
    head = (825, 320)
    for _ in range(46):
        x = rnd.uniform(40, 984)
        y = rnd.uniform(60, 760)
        if math.hypot(x - head[0], y - head[1]) < 85:
            continue
        rx = rnd.uniform(8, 14)
        ry = rnd.uniform(5, 8)
        ang = rnd.uniform(0, math.pi)
        col = rnd.choice(((249, 184, 204), (247, 163, 189),
                          (251, 211, 224)))
        ellipse(x, y, rx, ry, ang, col, rnd.randrange(200, 256))


# ---------------------------------------------------------------- PNG out
def chunk(typ, data):
    out = struct.pack(">I", len(data)) + typ + data
    out += struct.pack(">I", binascii.crc32(typ + data) & 0xFFFFFFFF)
    return out


def write_png(path):
    raw = bytearray()
    prev = bytes(W * 3)
    for y in range(H):
        row = bytes(buf[y * W * 3:(y + 1) * W * 3])
        # filter 0 (None) — simple; zlib level 9 does the heavy lifting
        raw.append(0)
        raw += row
    comp = zlib.compress(bytes(raw), 9)
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", comp)
    png += chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)
    return len(png)


def main():
    draw_sky()
    draw_hills_and_mist()
    draw_table()
    draw_cup()
    draw_water()
    draw_koi()
    draw_petals()
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, "entry.png")
    size = write_png(path)
    print("wrote %s (%dx%d, %d bytes)" % (path, W, H, size))


if __name__ == "__main__":
    main()
