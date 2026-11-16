#!/usr/bin/env python3
"""Draw one exciting image: a colossal blue whale breaching out of a
stormy sea at sunset, silhouetted against a huge low sun, a tiny sailboat
below for scale. Pure standard library, deterministic (fixed seed).

Writes a 1024x1024 PNG to $MAKEFUN_OUTPUT_DIR/entry.png (or /output).
"""
import math
import os
import random
import struct
import zlib

W = H = 1024
SEED = 20261116

rng = random.Random(SEED)

# ---------------------------------------------------------------- canvas
buf = bytearray(W * H * 3)


def put(x, y, c):
    if 0 <= x < W and 0 <= y < H:
        i = (y * W + x) * 3
        buf[i], buf[i + 1], buf[i + 2] = c


def blend(x, y, c, a):
    if 0 <= x < W and 0 <= y < H and a > 0:
        i = (y * W + x) * 3
        if a >= 1.0:
            buf[i], buf[i + 1], buf[i + 2] = c
        else:
            buf[i] = int(round(buf[i] * (1 - a) + c[0] * a))
            buf[i + 1] = int(round(buf[i + 1] * (1 - a) + c[1] * a))
            buf[i + 2] = int(round(buf[i + 2] * (1 - a) + c[2] * a))


def row_fill(y, c):
    if 0 <= y < H:
        i = y * W * 3
        buf[i:i + W * 3] = bytes(c) * W


def span(y, x0, x1, c, a=1.0):
    if y < 0 or y >= H:
        return
    x0 = max(0, int(x0))
    x1 = min(W - 1, int(x1))
    if x1 < x0:
        return
    if a >= 1.0:
        i = (y * W + x0) * 3
        buf[i:(y * W + x1 + 1) * 3] = bytes(c) * (x1 - x0 + 1)
    else:
        for x in range(x0, x1 + 1):
            blend(x, y, c, a)


def circle(cx, cy, r, c, a=1.0):
    cx, cy = int(cx), int(cy)
    r = int(r)
    if r <= 0:
        return
    for dy in range(-r, r + 1):
        dx = int(math.sqrt(r * r - dy * dy))
        span(cy + dy, cx - dx, cx + dx, c, a)


def ellipse(cx, cy, rx, ry, c, a=1.0):
    cx, cy = int(cx), int(cy)
    rx, ry = int(rx), int(ry)
    for dy in range(-int(ry), int(ry) + 1):
        t = dy / ry
        dx = int(rx * math.sqrt(max(0.0, 1 - t * t)))
        span(cy + dy, cx - dx, cx + dx, c, a)


def poly(points, c, a=1.0):
    # Scanline fill of a simple polygon.
    ys = [p[1] for p in points]
    y0, y1 = int(min(ys)), int(max(ys))
    n = len(points)
    for y in range(y0, y1 + 1):
        xs = []
        for k in range(n):
            x0, y0p = points[k]
            x1, y1p = points[(k + 1) % n]
            if (y0p <= y < y1p) or (y1p <= y < y0p):
                t = (y - y0p) / (y1p - y0p)
                xs.append(x0 + t * (x1 - x0))
        xs.sort()
        for k in range(0, len(xs) - 1, 2):
            span(y, xs[k], xs[k + 1], c, a)


def thick_line(x0, y0, x1, y1, w, c, a=1.0):
    steps = int(max(abs(x1 - x0), abs(y1 - y0), 1)) + 1
    for k in range(steps + 1):
        t = k / steps
        circle(int(x0 + (x1 - x0) * t), int(y0 + (y1 - y0) * t), w / 2, c, a)


def lerp(a, b, t):
    return a + (b - a) * t


def lerp3(c1, c2, t):
    return tuple(int(round(lerp(a, b, t))) for a, b in zip(c1, c2))


def bez(p0, p1, p2, t):
    u = 1 - t
    return (u * u * p0[0] + 2 * u * t * p1[0] + t * t * p2[0],
            u * u * p0[1] + 2 * u * t * p1[1] + t * t * p2[1])


# ---------------------------------------------------------------- sky
SKY_STOPS = [
    (0.00, (16, 8, 46)),
    (0.30, (52, 22, 74)),
    (0.55, (124, 42, 92)),
    (0.75, (214, 74, 76)),
    (1.00, (255, 128, 58)),
]
for y in range(H):
    t = y / (H - 1)
    for k in range(len(SKY_STOPS) - 1):
        t0, c0 = SKY_STOPS[k]
        t1, c1 = SKY_STOPS[k + 1]
        if t0 <= t <= t1:
            row_fill(y, lerp3(c0, c1, (t - t0) / (t1 - t0)))
            break

# Stars in the upper sky.
for _ in range(140):
    x = rng.randint(0, W - 1)
    y = rng.randint(0, 300)
    r = rng.choice([1, 1, 1, 2])
    a = rng.uniform(0.25, 0.9)
    circle(x, y, r, (255, 240, 210), a)

# ---------------------------------------------------------------- sun
SUN = (572, 428)
SUN_R = 148
# Warm glow, radial falloff.
for dy in range(-360, 361):
    for dx in range(-360, 361):
        d = math.sqrt(dx * dx + dy * dy)
        if d < 360:
            a = max(0.0, (1 - d / 360.0)) ** 2 * 0.55
            blend(SUN[0] + dx, SUN[1] + dy, (255, 150, 70), a)
circle(SUN[0], SUN[1], SUN_R, (255, 214, 122))
circle(SUN[0], SUN[1], SUN_R - 22, (255, 232, 160))
# Sun disc shading: slightly darker rim.
for dy in range(-SUN_R, SUN_R + 1):
    dx = int(math.sqrt(SUN_R * SUN_R - dy * dy))
    span(SUN[1] + dy, SUN[0] - dx, SUN[0] + dx, (255, 214, 122))

# ---------------------------------------------------------------- clouds
# Dark silhouetted clouds with warm-lit undersides.
# Dark silhouetted clouds with warm-lit undersides, drawn as clusters of
# overlapping puffs so they read as clouds, not bars.
CLOUDS = [
    (180, 150, (38, 18, 58)),
    (830, 120, (38, 18, 58)),
    (760, 300, (46, 20, 62)),
    (120, 330, (52, 24, 66)),
]
for cx, cy, col in CLOUDS:
    for ox, oy, rx, ry in [(-70, 6, 70, 16), (0, -4, 95, 22), (75, 6, 65, 15)]:
        ellipse(cx + ox, cy + oy, rx, ry, col, 0.9)
    ellipse(cx, cy + 12, 110, 8, (255, 120, 70), 0.16)

# ---------------------------------------------------------------- whale
# Spine: quadratic bezier from tail base (in the water) to head tip.
P0 = (648, 700)
P1 = (742, 400)
P2 = (408, 178)

# Radius profile along the spine (t -> radius).
R_PROFILE = [(0.00, 52), (0.15, 96), (0.35, 112), (0.55, 104),
             (0.75, 78), (0.90, 46), (1.00, 20)]


def radius_at(t):
    for k in range(len(R_PROFILE) - 1):
        t0, r0 = R_PROFILE[k]
        t1, r1 = R_PROFILE[k + 1]
        if t0 <= t <= t1:
            return lerp(r0, r1, (t - t0) / (t1 - t0))
    return R_PROFILE[-1][1]


BODY = (30, 48, 92)
BODY_DARK = (20, 34, 68)
BELLY = (150, 184, 216)

# Tail flukes first (behind the body), swept back, half in the water.
poly([(648, 690), (806, 800), (716, 812), (664, 742)], BODY_DARK)
poly([(648, 690), (498, 822), (596, 830), (636, 744)], BODY_DARK)

# Body: overlapping circles along the spine, tail -> head.
spine = []
N = 220
for k in range(N + 1):
    t = k / N
    spine.append((bez(P0, P1, P2, t), radius_at(t)))
for (x, y), r in spine:
    circle(int(x), int(y), int(r), BODY)

# Dark dorsal shading on the upper side of the body.
for k in range(N + 1):
    t = k / N
    if 0.15 <= t <= 0.95:
        (x, y), r = spine[k]
        # Offset toward the upper-right (sun side is behind; shade the top).
        circle(int(x + r * 0.12), int(y - r * 0.28), int(r * 0.72), BODY_DARK, 0.22)

# Pale belly stripe along the lower-left side.
for k in range(N + 1):
    t = k / N
    if 0.20 <= t <= 0.96:
        (x, y), r = spine[k]
        circle(int(x - r * 0.26), int(y + r * 0.30), int(r * 0.42), BELLY, 0.38)

# Pectoral fin, a slim tapered blade sweeping down from mid-body.
poly([(592, 492), (478, 616), (548, 630)], BODY_DARK)

# Head details: eye and a hint of a jaw line near the tip.
head = bez(P0, P1, P2, 0.97)
# Tangent at head, pointing outward.
hx, hy = head
eye = (int(hx - 26), int(hy + 6))
circle(eye[0], eye[1], 9, (8, 12, 24))
circle(eye[0] + 3, eye[1] - 3, 3, (255, 255, 255))
thick_line(int(hx + 8), int(hy + 26), int(hx - 52), int(hy + 52), 5, BODY_DARK, 0.7)

# Water streaming off the body: pale streaks along the lower edge.
for k in range(26):
    t = rng.uniform(0.25, 0.85)
    (x, y), r = spine[int(t * N)]
    ang = rng.uniform(0.35, 1.1)
    ln = rng.uniform(26, 70)
    x2 = x - r * 0.55 + math.cos(ang) * ln * 0.4
    y2 = y + r * 0.55 + math.sin(ang) * ln
    thick_line(int(x - r * 0.5), int(y + r * 0.5),
              int(x2), int(y2), rng.uniform(2, 4),
              (200, 225, 245), rng.uniform(0.35, 0.7))

# ---------------------------------------------------------------- sea
SEA_TOP = 716
for y in range(SEA_TOP, H):
    t = (y - SEA_TOP) / (H - SEA_TOP)
    row_fill(y, lerp3((10, 46, 82), (4, 16, 38), t))

# Wavy sea surface line.
for x in range(W):
    y = SEA_TOP + int(6 * math.sin(x * 0.018) + 3 * math.sin(x * 0.043 + 1.7))
    circle(x, y, 2, (120, 170, 205), 0.5)

# Swell bands: long sine strokes catching the sunset.
for band, yy, amp, col, a in [
        (0, 780, 10, (255, 140, 80), 0.30),
        (1, 850, 14, (255, 110, 70), 0.22),
        (2, 930, 18, (120, 170, 205), 0.25)]:
    for x in range(0, W, 2):
        y = yy + int(amp * math.sin(x * 0.011 + band * 2.1))
        circle(x, y, 2, col, a)

# Foam ring where the whale bursts through the surface.
foam_cx, foam_cy = 655, 726
for _ in range(260):
    ang = rng.uniform(0, 2 * math.pi)
    rr = rng.uniform(0.55, 1.0)
    fx = int(foam_cx + math.cos(ang) * 175 * rr)
    fy = int(foam_cy + math.sin(ang) * 30 * rr)
    circle(fx, fy, rng.randint(2, 7), (235, 245, 250),
           rng.uniform(0.5, 0.95))
ellipse(foam_cx, foam_cy, 175, 26, (235, 245, 250), 0.35)

# ---------------------------------------------------------------- spray
# Frozen droplets bursting around the whale's head and flanks.
for _ in range(220):
    t = rng.uniform(0.30, 1.0)
    (x, y), r = spine[int(t * N)]
    side = rng.choice([-1, 1])
    d = r * rng.uniform(1.02, 1.5)
    ang = rng.uniform(-0.6, 1.2) if side > 0 else rng.uniform(1.9, 3.8)
    sx = int(x + math.cos(ang) * d)
    sy = int(y + math.sin(ang) * d - rng.uniform(0, 26))
    circle(sx, sy, rng.randint(1, 4), (240, 248, 252),
           rng.uniform(0.45, 0.95))
# A few bright spray arcs arcing off the head.
for _ in range(4):
    t = rng.uniform(0.75, 1.0)
    (x, y), r = spine[int(t * N)]
    a0 = rng.uniform(2.6, 3.6)
    for k in range(10):
        a = a0 + k * 0.09
        rr = r * (1.15 + k * 0.09)
        circle(int(x + math.cos(a) * rr), int(y + math.sin(a) * rr - k * 3),
               3, (245, 250, 255), 0.8)

# ---------------------------------------------------------------- sailboat (scale)
boat_x, boat_y = 232, 836
poly([(boat_x - 34, boat_y), (boat_x + 34, boat_y),
      (boat_x + 22, boat_y + 14), (boat_x - 22, boat_y + 14)], (16, 20, 34))
thick_line(boat_x, boat_y, boat_x, boat_y - 52, 3, (16, 20, 34))
poly([(boat_x + 2, boat_y - 50), (boat_x + 2, boat_y - 4),
      (boat_x + 34, boat_y - 4)], (245, 240, 225))
poly([(boat_x - 2, boat_y - 42), (boat_x - 2, boat_y - 4),
      (boat_x - 26, boat_y - 4)], (225, 225, 210))
# Reflection.
for k in range(5):
    span(boat_y + 18 + k * 4, boat_x - 26 + k * 3, boat_x + 26 - k * 3,
         (255, 160, 90), 0.25 - k * 0.04)

# ---------------------------------------------------------------- birds
for bx, by, s in [(300, 168, 12), (352, 142, 9), (706, 210, 11),
                  (760, 246, 8), (250, 210, 9)]:
    thick_line(bx - s, by, bx, by - 5, 2, (20, 16, 34))
    thick_line(bx, by - 5, bx + s, by, 2, (20, 16, 34))

# ---------------------------------------------------------------- foreground wave
fg = [(0, 1024)]
for x in range(0, W + 1, 16):
    fg.append((x, 972 + int(14 * math.sin(x * 0.012 + 0.8))))
fg.append((1024, 1024))
poly(fg, (3, 12, 28))
for x in range(0, W, 6):
    y = 972 + int(14 * math.sin(x * 0.012 + 0.8))
    circle(x, y, 2, (140, 190, 220), 0.35)

# ---------------------------------------------------------------- PNG write
def chunk(typ, data):
    c = struct.pack(">I", len(data)) + typ + data
    return c + struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF)


raw = b"".join(b"\x00" + bytes(buf[y * W * 3:(y + 1) * W * 3])
               for y in range(H))
png = (b"\x89PNG\r\n\x1a\n"
       + chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0))
       + chunk(b"IDAT", zlib.compress(raw, 9))
       + chunk(b"IEND", b""))

out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
os.makedirs(out_dir, exist_ok=True)
path = os.path.join(out_dir, "entry.png")
with open(path, "wb") as f:
    f.write(png)
print("wrote", path, len(png), "bytes")
