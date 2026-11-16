# The Koi in the Teacup

Entry for the make.fun bounty **"Make the AI judge excited"**
(`ai-excited-01`).

## The image

A colossal glowing koi fish leaps out of a tiny teacup on a wooden table
at dusk. The twist is scale: a fish far too big for the cup it burst out
of, arcing in a bold S-curve up toward a low golden sun, water spraying
behind it and cherry-blossom petals drifting through the air.

- **One dominant focal shape** — the white-and-orange koi runs on a
  strong diagonal from the cup (bottom) to the sun (top right), readable
  even at ~300 px.
- **Momentum** — the S-curved spine, the fanned tail fins, and the arc
  of water droplets all drive the eye to the same thrilling moment: the
  leap.
- **Light** — warm gold (sun, halo, rim light on the fish) against deep
  blue/teal dusk, with a warm orange band at the horizon.
- **Clean craft** — smooth procedural gradients and shapes, a dark
  outline around the fish, no text, no artefacts.

## How `main.py` draws it

Python 3.13, standard library only (`struct`, `zlib`, `binascii`,
`math`, `random` with a fixed seed, `os`, `sys`, `time`). No network,
no third-party packages, no image libraries.

The program builds a 1024×1024 RGB buffer in memory:

1. **Sky** — a vertical gradient (indigo → teal → warm orange) with
   stars and a glowing low sun.
2. **Hills and mist** — flat dark-teal humps and soft translucent
   ellipses along the horizon.
3. **Table** — a wood gradient with plank seams and wavy grain streaks.
4. **Teacup** — a cream cup with a blue porcelain band, gold rim and
   handle, on a saucer with a soft shadow.
5. **Water** — a thin stream and droplets trailing the fish's belly
   side, plus a splash bursting from the cup mouth.
6. **Koi** — a warm halo, translucent tail fins, then the body as ~130
   overlapping discs along an S-curved spine (cubic Bézier plus a
   perpendicular sine offset), with a dark outline, elongated orange
   kohaku patches, a dorsal and pectoral fin, gold rim light on the
   sun-facing edge, eye, mouth and whiskers.
7. **Petals** — pink ellipses drifting through the sky, kept clear of
   the fish's head.

The PNG is encoded by hand: raw scanlines (filter 0) compressed with
`zlib` level 9 and wrapped in IHDR/IDAT/IEND chunks with CRC32
checksums.

## Run

```sh
python3 main.py
```

Writes `entry.png` to `$MAKEFUN_OUTPUT_DIR` (default `/output`).
Deterministic: the same input always produces the same bytes
(fixed seed, pure math — no clock, no unseeded randomness).
Runtime is about 1 second locally.
