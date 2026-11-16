#!/usr/bin/env python3
"""The Koi in the Teacup -- make.fun bounty ai-excited-01.

A giant white-and-orange koi leaps in a graceful S-curve out of a tiny
teacup on a wooden table at dusk, arcing toward a low golden sun.
Water splashes, sakura petals drift, warm dusk sky.

Python 3 standard library only. Writes one deterministic PNG to
$MAKEFUN_OUTPUT_DIR/entry.png (or ./output/entry.png).
"""
import math
import os
import struct
import zlib

W = 1024
H = 1024

# ---------------------------------------------------------------- raster
buf = bytearray(W * H * 3)


def px(x, y, r, g, b):
    if 0 <= x < W and 0 <= y < H:
        i = (y * W + x) * 3
        buf[i] = r
        buf[i + 1] = g
        buf[i + 2] = b


def blend(x, y, r, g, b, a):
    """Blend colour over existing pixel, a in 0..1."""
    if 0 <= x < W and 0 <= y < H:
        i = (y * W + x) * 3
        buf[i] = int(buf[i] * (1 - a) + r * a)
        buf[i + 1] = int(buf[i + 1] * (1 - a) + g * a)
        buf[i + 2] = int(buf[i + 2] * (1 - a) + b * a)


def disc(cx, cy, rad, r, g, b, a=1.0):
    rad = int(rad)
    if rad <= 0:
        return
    for y in range(cy - rad, cy + rad + 1):
        dy = y - cy
        dx = int(math.sqrt(max(0, rad * rad - dy * dy)))
        for x in range(cx - dx, cx + dx + 1):
            if a >= 1.0:
                px(x, y, r, g, b)
            else:
                blend(x, y, r, g, b, a)


def ellipse(cx, cy, rx, ry, r, g, b, a=1.0):
    rx = int(rx)
    ry = int(ry)
    if rx <= 0 or ry <= 0:
        return
    for y in range(cy - ry, cy + ry + 1):
        dy = (y - cy) / ry
        rem = 1.0 - dy * dy
        if rem < 0:
            continue
        dx = int(rx * math.sqrt(rem))
        for x in range(cx - dx, cx + dx + 1):
            if a >= 1.0:
                px(x, y, r, g, b)
            else:
                blend(x, y, r, g, b, a)


def rot_ellipse(cx, cy, rx, ry, ang_deg, r, g, b, a=1.0):
    """Filled ellipse rotated by ang_deg, drawn by sampling its disc."""
    ang = math.radians(ang_deg)
    ca, sa = math.cos(ang), math.sin(ang)
    R = int(max(rx, ry)) + 1
    for y in range(cy - R, cy + R + 1):
        for x in range(cx - R, cx + R + 1):
            dx, dy = x - cx, y - cy
            u = dx * ca + dy * sa
            v = -dx * sa + dy * ca
            if (u / rx) ** 2 + (v / ry) ** 2 <= 1.0:
                if a >= 1.0:
                    px(x, y, r, g, b)
                else:
                    blend(x, y, r, g, b, a)


def poly(points, r, g, b, a=1.0):
    """Scanline fill of a simple polygon."""
    if not points:
        return
    ys = [p[1] for p in points]
    ymin, ymax = max(0, int(min(ys))), min(H - 1, int(max(ys)))
    n = len(points)
    for y in range(ymin, ymax + 1):
        xs = []
        for i in range(n):
            x1, y1 = points[i]
            x2, y2 = points[(i + 1) % n]
            if (y1 <= y < y2) or (y2 <= y < y1):
                t = (y - y1) / (y2 - y1)
                xs.append(x1 + t * (x2 - x1))
        xs.sort()
        for k in range(0, len(xs) - 1, 2):
            for x in range(int(math.ceil(xs[k])), int(xs[k + 1]) + 1):
                if a >= 1.0:
                    px(x, y, r, g, b)
                else:
                    blend(x, y, r, g, b, a)


def line(x1, y1, x2, y2, r, g, b, width=1, a=1.0):
    steps = int(max(abs(x2 - x1), abs(y2 - y1))) + 1
    for i in range(steps + 1):
        t = i / max(1, steps)
        x = int(x1 + (x2 - x1) * t)
        y = int(y1 + (y2 - y1) * t)
        disc(x, y, max(1, width // 2), r, g, b, a)


def lerp(a, b, t):
    return a + (b - a) * t


def lerp3(c1, c2, t):
    return (int(lerp(c1[0], c2[0], t)), int(lerp(c1[1], c2[1], t)),
            int(lerp(c1[2], c2[2], t)))


# ---------------------------------------------------------------- sky
SKY_STOPS = [
    (0.00, (24, 20, 66)),    # deep indigo, top
    (0.35, (74, 44, 108)),   # violet dusk
    (0.60, (168, 74, 88)),   # rose
    (0.80, (248, 128, 62)),  # warm orange near horizon
    (1.00, (255, 176, 84)),
]
HORIZON = 818


def sky_at(y):
    t = y / HORIZON
    for i in range(len(SKY_STOPS) - 1):
        t0, c0 = SKY_STOPS[i]
        t1, c1 = SKY_STOPS[i + 1]
        if t0 <= t <= t1:
            return lerp3(c0, c1, (t - t0) / max(1e-9, t1 - t0))
    return SKY_STOPS[-1][1]


for y in range(HORIZON + 1):
    c = sky_at(y)
    for x in range(W):
        px(x, y, *c)

# faint stars high up (fixed positions, deterministic)
STARS = [(80, 60), (170, 120), (260, 45), (350, 95), (470, 55), (560, 110),
         (640, 40), (900, 90), (950, 170), (120, 210), (700, 150), (40, 140),
         (830, 220), (420, 170), (980, 260), (210, 260), (540, 200)]
for sx, sy in STARS:
    disc(sx, sy, 2, 255, 240, 210, 0.85)

# ---------------------------------------------------------------- sun
SUN_C, SUN_R = (778, 618), 82
# glow: concentric translucent discs
for k in range(6, 0, -1):
    disc(SUN_C[0], SUN_C[1], SUN_R + k * 26, 255, 170, 70, 0.10)
disc(SUN_C[0], SUN_C[1], SUN_R + 10, 255, 196, 110, 0.9)
disc(SUN_C[0], SUN_C[1], SUN_R, 255, 214, 96)
disc(SUN_C[0], SUN_C[1], SUN_R - 22, 255, 232, 150)
# low dark hills on the horizon, left side only (sun stays clear)
for x in range(0, 560):
    hill = 806 - int(26 * math.sin(x / 190.0) ** 2) - int(10 * math.sin(x / 47.0 + 1.3))
    for y in range(hill, HORIZON + 1):
        blend(x, y, 52, 30, 66, 0.85)

# ---------------------------------------------------------------- table
for y in range(HORIZON, H):
    t = (y - HORIZON) / (H - HORIZON)
    c = lerp3((96, 60, 36), (58, 34, 20), t)
    for x in range(W):
        px(x, y, *c)
# plank seams + grain
for gy in (856, 902, 948, 994):
    for x in range(W):
        px(x, gy, 44, 26, 15)
        px(x, gy + 1, 120, 76, 46)
for gx, gy0, glen in [(140, 880, 60), (620, 930, 90), (820, 870, 70),
                      (300, 970, 80), (60, 930, 50), (920, 990, 60)]:
    for i in range(glen):
        px(gx + i, gy0 + int(3 * math.sin(i / 18.0)), 70, 42, 24)
# warm light pool on the table under the sun
for y in range(HORIZON, H):
    for x in range(560, W):
        d = math.hypot(x - 778, y - 900) / 420.0
        if d < 1.0:
            blend(x, y, 255, 170, 80, 0.16 * (1 - d))

# ---------------------------------------------------------------- koi spine
# S-curve from the teacup (tail, bottom-left) up to the head (top-right,
# reaching for the sun). Control points give a real S, not a straight arc.
CTRL = [(318, 782), (352, 690), (430, 600), (540, 540),
        (640, 480), (724, 420), (792, 372)]
SEG = 240  # samples along the spine


def spine(t):
    """Catmull-Rom through CTRL, t in 0..1. Returns (x, y)."""
    n = len(CTRL) - 1
    f = t * n
    i = min(n - 1, int(f))
    u = f - i
    p0 = CTRL[max(0, i - 1)]
    p1 = CTRL[i]
    p2 = CTRL[i + 1]
    p3 = CTRL[min(n, i + 2)]
    x = 0.5 * ((2 * p1[0]) + (-p0[0] + p2[0]) * u
               + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * u * u
               + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * u * u * u)
    y = 0.5 * ((2 * p1[1]) + (-p0[1] + p2[1]) * u
               + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * u * u
               + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * u * u * u)
    return x, y


def radius(t):
    """Body half-width: thin tail, fat belly, tapered head."""
    if t < 0.12:
        return lerp(16, 34, t / 0.12)
    if t < 0.45:
        return lerp(34, 64, (t - 0.12) / 0.33)
    if t < 0.8:
        return lerp(64, 46, (t - 0.45) / 0.35)
    return lerp(46, 30, (t - 0.8) / 0.2)


SPINE = [spine(i / SEG) for i in range(SEG + 1)]

# dark outline first (slightly wider), then white body
for (x, y), t in zip(SPINE, [i / SEG for i in range(SEG + 1)]):
    disc(int(x), int(y), int(radius(t)) + 4, 176, 52, 28)
for (x, y), t in zip(SPINE, [i / SEG for i in range(SEG + 1)]):
    disc(int(x), int(y), int(radius(t)), 250, 247, 238)

# bold orange-red patches, kept inside the body (smaller than local radius),
# stretched along the spine so they read as koi markings, not polka dots
PATCHES = [
    (0.30, 0.0, 46, 26), (0.52, -4, 48, 26), (0.70, 0.0, 44, 26),
    (0.88, 4, 30, 20), (0.16, 0, 24, 16),
]
for t, off, prx, pry in PATCHES:
    x, y = spine(t)
    x2, y2 = spine(min(1.0, t + 0.02))
    dx, dy = x2 - x, y2 - y
    L = math.hypot(dx, dy) or 1.0
    nx, ny = -dy / L, dx / L
    ang = math.degrees(math.atan2(dy, dx))
    rot_ellipse(int(x + nx * off), int(y + ny * off), prx, pry, ang,
                232, 84, 34)
# a few small orange speckles
for t, off, pr in [(0.44, -20, 12), (0.62, 18, 11), (0.80, -16, 10),
                   (0.24, 10, 10), (0.95, 0, 12)]:
    x, y = spine(t)
    x2, y2 = spine(min(1.0, t + 0.02))
    dx, dy = x2 - x, y2 - y
    L = math.hypot(dx, dy) or 1.0
    disc(int(x - dy / L * off), int(y + dx / L * off), pr, 232, 84, 34)


def spine_frame(t):
    """Spine point + unit tangent + unit normal (pointing up-left)."""
    x, y = spine(t)
    x2, y2 = spine(min(1.0, t + 0.01))
    dx, dy = x2 - x, y2 - y
    L = math.hypot(dx, dy) or 1.0
    tx_, ty_ = dx / L, dy / L
    nx, ny = -ty_, tx_
    if ny > 0:  # keep the normal pointing upward
        nx, ny = -nx, -ny
    return x, y, tx_, ty_, nx, ny


# dorsal fin: a soft swept fin hugging the upper edge of the belly
_d1 = spine_frame(0.40)
_d2 = spine_frame(0.58)
_b1 = (_d1[0] + _d1[4] * (radius(0.40) - 4), _d1[1] + _d1[5] * (radius(0.40) - 4))
_b2 = (_d2[0] + _d2[4] * (radius(0.58) - 4), _d2[1] + _d2[5] * (radius(0.58) - 4))
_mid = spine_frame(0.49)
_tip = (_mid[0] + _mid[4] * (radius(0.49) + 52),
        _mid[1] + _mid[5] * (radius(0.49) + 52))
_tip2 = (_mid[0] + _mid[4] * (radius(0.49) + 34)
         + _mid[2] * 34,
         _mid[1] + _mid[5] * (radius(0.49) + 34) + _mid[3] * 34)
poly([(int(_b1[0]), int(_b1[1])), (int(_tip[0]), int(_tip[1])),
      (int(_tip2[0]), int(_tip2[1])), (int(_b2[0]), int(_b2[1]))],
     238, 120, 60, 0.95)
poly([(int(_b1[0]), int(_b1[1])),
      (int(lerp(_b1[0], _tip[0], 0.55)), int(lerp(_b1[1], _tip[1], 0.55))),
      (int(_b2[0]), int(_b2[1]))], 250, 247, 238, 0.75)

# pectoral fin under the head, swept back
hx, hy = spine(0.94)
poly([(int(hx) - 6, int(hy) + 26), (int(hx) - 66, int(hy) + 96),
      (int(hx) - 18, int(hy) + 78)], 244, 150, 92, 0.95)
poly([(int(hx) - 10, int(hy) + 30), (int(hx) - 52, int(hy) + 84),
      (int(hx) - 20, int(hy) + 70)], 250, 247, 238, 0.8)

# forked tail: two long flowing lobes streaming back from the tail base
tx, ty = spine(0.0)
rot_ellipse(int(tx) - 33, int(ty) - 37, 65, 17, -38, 240, 110, 52, 0.95)
rot_ellipse(int(tx) - 33, int(ty) - 37, 42, 7, -38, 250, 247, 238, 0.8)
rot_ellipse(int(tx) - 28, int(ty) + 28, 60, 16, 42, 232, 84, 34, 0.95)
rot_ellipse(int(tx) - 28, int(ty) + 28, 38, 6, 42, 250, 247, 238, 0.8)

# head: eye + gill line + mouth
ex, ey = int(hx) + 16, int(hy) - 12
disc(ex, ey, 10, 30, 22, 18)
disc(ex + 3, ey - 3, 3, 255, 255, 255)
# gill curve
for a in range(0, 121, 6):
    ang = math.radians(a - 60)
    gx = int(hx) - 6 + int(20 * math.cos(ang))
    gy = int(hy) + 4 + int(26 * math.sin(ang))
    disc(gx, gy, 2, 200, 90, 50, 0.8)
line(int(hx) + 26, int(hy) + 16, int(hx) + 40, int(hy) + 20, 176, 52, 28, 3)

# ---------------------------------------------------------------- splash
# water bursting out of the cup where the koi launched
SPLASH = [(398, 742, 26), (360, 752, 18), (438, 750, 20), (330, 766, 14),
          (470, 764, 15), (392, 716, 14), (420, 726, 11), (352, 726, 11)]
for sx, sy, sr in SPLASH:
    disc(sx, sy, sr, 214, 232, 244, 0.95)
    disc(sx - sr // 3, sy - sr // 3, max(2, sr // 3), 255, 255, 255, 0.9)
# droplets trailing the leap (fixed positions along the arc)
DROPS = [(330, 660, 9), (300, 700, 7), (392, 590, 8), (470, 520, 6),
         (560, 460, 8), (650, 410, 6), (700, 350, 7), (470, 640, 5),
         (540, 580, 5), (610, 500, 5), (360, 620, 6), (760, 430, 5)]
for dx_, dy_, dr in DROPS:
    disc(dx_, dy_, dr, 190, 214, 236, 0.95)
    disc(dx_ - 2, dy_ - 2, max(1, dr // 3), 255, 255, 255, 0.95)
# splash arcs over the cup rim
for a in range(200, 341, 8):
    ang = math.radians(a)
    ax = int(398 + 58 * math.cos(ang))
    ay = int(756 + 26 * math.sin(ang))
    disc(ax, ay, 4, 226, 238, 246, 0.9)

# ---------------------------------------------------------------- teacup
# saucer
ellipse(398, 838, 108, 20, 210, 208, 200)
ellipse(398, 834, 100, 17, 244, 242, 236)
# cup body: trapezoid, white porcelain
poly([(330, 762), (466, 762), (448, 836), (348, 836)], 238, 236, 230)
poly([(336, 768), (460, 768), (446, 830), (350, 830)], 250, 249, 243)
# blue pattern band + dots
for x in range(338, 460, 4):
    ytop = 786
    px(x, ytop, 52, 96, 158)
    px(x, ytop + 1, 52, 96, 158)
for bx in (362, 398, 434):
    disc(bx, 806, 5, 52, 96, 158)
# rim
ellipse(398, 762, 68, 12, 250, 249, 243)
ellipse(398, 762, 68, 12, 200, 198, 190, 0.0)  # no-op keeps shape explicit
for x in range(330, 467):
    dx = (x - 398) / 68.0
    if abs(dx) <= 1.0:
        y = 762 - int(12 * math.sqrt(1 - dx * dx))
        px(x, y, 190, 188, 182)
# tea surface inside the rim
ellipse(398, 762, 58, 9, 196, 120, 52)
ellipse(398, 761, 50, 7, 214, 138, 66)
# handle: arc on the right side
for a in range(-80, 101, 4):
    ang = math.radians(a)
    hx2 = int(462 + 22 * math.cos(ang))
    hy2 = int(800 + 30 * math.sin(ang))
    disc(hx2, hy2, 5, 244, 242, 236)
# foot shadow under the saucer
ellipse(398, 852, 104, 10, 40, 24, 14, 0.55)

# ---------------------------------------------------------------- petals
PETALS = [(150, 300, -30), (230, 180, 25), (620, 240, -50), (880, 300, 40),
          (120, 520, 15), (920, 520, -25), (560, 180, 60), (300, 420, -15),
          (840, 160, 20), (700, 640, -40), (180, 640, 35), (950, 420, -60)]
for px_, py_, ang in PETALS:
    rot_ellipse(px_, py_, 15, 8, ang, 250, 158, 182)
    rot_ellipse(px_, py_, 11, 5, ang, 255, 190, 205)

# ---------------------------------------------------------------- PNG encode
def chunk(typ, data):
    c = struct.pack(">I", len(data)) + typ + data
    c += struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF)
    return c


def write_png(path):
    raw = b"".join(b"\x00" + bytes(buf[y * W * 3:(y + 1) * W * 3])
                   for y in range(H))
    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    png = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
           + chunk(b"IDAT", zlib.compress(raw, 9))
           + chunk(b"IEND", b""))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(png)
    return len(png)


def main():
    outdir = os.environ.get("MAKEFUN_OUTPUT_DIR") or "output"
    path = os.path.join(outdir, "entry.png")
    size = write_png(path)
    print(f"wrote {path} ({W}x{H}, {size} bytes)")


if __name__ == "__main__":
    main()
