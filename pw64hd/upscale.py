"""Turn Birdman64's texture dumps into a 4x HD pack.

Per texture (named by Birdman64's content key, <16 hex>.png):
- longest side < 8 px: skipped (the game keeps the original).
- data/nearest.txt (HUD lettering, font sheets): plain 4x pixel enlargement;
  the AI redraws small letters ("SEA LEVEL" became "SEN LEVEL").
- data/smooth.txt (sky, cloud, haze and sea layers): exact bilinear, wrapped,
  sampled 3/8 texel early (see bilinear_shift). The AI invents blocks and
  streaks in soft layers.
- thin strips (<= 8 px one way, >= 64 the other): slices of 2D backgrounds
  (pilot select, title); Lanczos per channel, edge-padded.
- everything else: Real-ESRGAN realesrgan-x4plus. Textures that tile (opposite
  edges match) are wrap-padded so they stay seamless, others edge-padded; each
  result is checked against the original and dropped if it doesn't match.
Colour and alpha are always resized separately, never premultiplied: many
textures are N64 intensity+alpha, and dividing colour by tiny alphas put bright
dots around every cloud.
"""
import os
import shutil
import subprocess
import tempfile

import numpy as np
from PIL import Image, ImageChops, ImageStat

SCALE = 4
MIN_SIDE = 8
MIN_INPUT = 32
BATCH = 40
DATA = os.path.join(os.path.dirname(__file__), "data")


def load_list(name):
    keys = set()
    for line in open(os.path.join(DATA, name), encoding="utf-8-sig"):
        line = line.split("#")[0].strip()
        if line:
            keys.add(line.lower().removesuffix(".png") + ".png")
    return keys


def pad_amount(n):
    return max(4, n // 4, (MIN_INPUT - n + 1) // 2)


def tiles(a, axis):
    """Does the texture wrap seamlessly along axis (opposite edges match about
    as well as neighbouring rows/columns do)?"""
    a = a.astype(np.float32)
    if a.shape[axis] < 4:
        return False
    seam = np.abs(np.take(a, 0, axis) - np.take(a, -1, axis)).mean()
    inner = np.abs(np.diff(a, axis=axis)).mean()
    return seam <= 1.5 * inner + 2.0


def prep(src_path, dst_path):
    im = Image.open(src_path).convert("RGBA")
    w, h = im.size
    px, py = pad_amount(w), pad_amount(h)
    a = np.asarray(im)
    opaque = a[..., 3].min() == 255
    mode_y = "wrap" if opaque and tiles(a, 0) else "edge"
    mode_x = "wrap" if opaque and tiles(a, 1) else "edge"
    a = np.pad(a, ((py, py), (0, 0), (0, 0)), mode=mode_y)
    a = np.pad(a, ((0, 0), (px, px), (0, 0)), mode=mode_x)
    Image.fromarray(a, "RGBA").save(dst_path)
    return w, h, px, py


def bilinear_shift(src_png, scale, delta):
    """Exact bilinear upscale (wrap), each channel separately: HD pixel j samples
    the original at (j+0.5)/scale - 0.5 + delta texels. Birdman64 applies the
    N64 half-texel offset in original texels for original textures but in HD
    texels for pack textures, so pack textures are sampled 3/8 texel late;
    delta = -3/8 cancels that. Without it the sky's horizon band starts its
    fade in the wrong place and shows as a ribbon."""
    a = np.asarray(Image.open(src_png).convert("RGBA")).astype(np.float64)
    h, w = a.shape[:2]

    def coords(n):
        x = (np.arange(n * scale) + 0.5) / scale - 0.5 + delta
        i0 = np.floor(x).astype(int)
        return i0 % n, (i0 + 1) % n, x - i0

    y0, y1, ty = coords(h)
    x0, x1, tx = coords(w)
    rows = a[y0] * (1 - ty)[:, None, None] + a[y1] * ty[:, None, None]
    out = rows[:, x0] * (1 - tx)[None, :, None] + rows[:, x1] * tx[None, :, None]
    return Image.fromarray(np.clip(np.round(out), 0, 255).astype(np.uint8), "RGBA")


def strip_lanczos(src_path, dst_path, work):
    tmp = os.path.join(work, "strip.png")
    w, h, px, py = prep(src_path, tmp)
    big = Image.open(tmp).convert("RGBA")
    size = (big.width * SCALE, big.height * SCALE)
    r, g, b, a = big.split()
    big = Image.merge("RGBA", [c.resize(size, Image.LANCZOS) for c in (r, g, b)] + [a.resize(size, Image.BILINEAR)])
    big.crop((px * SCALE, py * SCALE, (px + w) * SCALE, (py + h) * SCALE)).save(dst_path, optimize=True)


def finish(src_path, up_path, out_path, geom):
    w, h, px, py = geom
    s = SCALE
    up = Image.open(up_path).convert("RGBA").crop((px * s, py * s, (px + w) * s, (py + h) * s))
    orig = Image.open(src_path).convert("RGBA")
    a = orig.getchannel("A")
    if a.getextrema()[0] == 255:
        up.putalpha(255)
    elif set(np.unique(np.asarray(a)).tolist()) <= {0, 255}:
        up.putalpha(up.getchannel("A").point(lambda v: 255 if v >= 128 else 0))

    def flat(im):
        bg = Image.new("RGBA", im.size, (0, 0, 0, 255))
        bg.alpha_composite(im)
        return bg.convert("RGB")
    diff = ImageStat.Stat(ImageChops.difference(flat(orig), flat(up.resize(orig.size, Image.BOX)))).mean
    if sum(diff) / 3 > 40:
        return False
    up.save(out_path, optimize=True)
    return True


def esrgan_batch(esrgan, names, src, dst, work):
    pin, pout = os.path.join(work, "in"), os.path.join(work, "out")
    for d in (pin, pout):
        shutil.rmtree(d, ignore_errors=True)
        os.makedirs(d)
    geoms = {f: prep(os.path.join(src, f), os.path.join(pin, f)) for f in names}
    subprocess.run([esrgan, "-i", pin, "-o", pout, "-n", "realesrgan-x4plus", "-s", str(SCALE),
                    "-f", "png", "-j", "1:1:1"], cwd=os.path.dirname(esrgan),
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    failed = []
    for f in names:
        up = os.path.join(pout, f)
        if not (os.path.exists(up) and finish(os.path.join(src, f), up, os.path.join(dst, f), geoms[f])):
            failed.append(f)
    return failed


def build_pack(src, dst, esrgan, log=print):
    os.makedirs(dst, exist_ok=True)
    nearest, smooth = load_list("nearest.txt"), load_list("smooth.txt")
    work = tempfile.mkdtemp(prefix="pw64hd_")
    ai, counts = [], dict(skipped=0, pixel=0, sky=0, strip=0)
    for f in sorted(os.listdir(src)):
        if not f.lower().endswith(".png") or os.path.exists(os.path.join(dst, f)):
            continue
        p, out, k = os.path.join(src, f), os.path.join(dst, f), f.lower()
        im = Image.open(p).convert("RGBA")
        if max(im.size) < MIN_SIDE:
            counts["skipped"] += 1
        elif k in nearest:
            im.resize((im.width * SCALE, im.height * SCALE), Image.NEAREST).save(out, optimize=True)
            counts["pixel"] += 1
        elif k in smooth:
            bilinear_shift(p, SCALE, -0.5 + 0.5 / SCALE).save(out, optimize=True)
            counts["sky"] += 1
        elif min(im.size) <= 8 and max(im.size) >= 64:
            strip_lanczos(p, out, work)
            counts["strip"] += 1
        else:
            ai.append(f)
    log(f"  {counts['pixel']} lettering, {counts['sky']} sky, {counts['strip']} background strips done; "
        f"{len(ai)} for the AI upscaler ({counts['skipped']} tiny ones left as they are)")
    retry = []
    for i in range(0, len(ai), BATCH):
        retry += esrgan_batch(esrgan, ai[i:i + BATCH], src, dst, work)
        log(f"  AI upscaling {min(i + BATCH, len(ai))}/{len(ai)}", end="\r")
    log("")
    still = []
    for f in retry:  # a Vulkan "device lost" blanks the rest of a batch: retry singly
        still += esrgan_batch(esrgan, [f], src, dst, work)
    shutil.rmtree(work, ignore_errors=True)
    return len(still)
