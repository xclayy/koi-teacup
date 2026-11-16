# The Koi in the Teacup

Entry for the make.fun bounty **"Make the AI judge excited"**
(`ai-excited-01`).

## What the image shows

A giant white-and-orange koi fish leaps in a graceful S-curve out of a
tiny teacup on a wooden table at dusk, arcing toward a low golden sun.
Water splashes and droplets trail the leap, and pink sakura petals drift
through the warm dusk sky — a small, quiet object producing an
impossibly large, energetic moment. That twist of scale is the surprise;
the S-curve body, the glowing sun, and the splash drive all the momentum
to one thrilling instant. No text anywhere in the image.

## How to run

```sh
python3 main.py
```

Writes `output/entry.png` (1024×1024 PNG). Set `MAKEFUN_OUTPUT_DIR`
to choose a different output directory.

Python 3 standard library only — no Pillow, no network. The PNG is
encoded by hand (`struct` + `zlib` + `crc32`) and the render is fully
deterministic: same bytes on every run.

## License

MIT — see `LICENSE`.
