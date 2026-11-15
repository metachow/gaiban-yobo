"""Cover art for both volumes.

* figures/cover_paper.jpg, figures/slip_paper.jpg: generated (seeded) paper textures in the
  colours measured on the original covers (書衣 柿渋色 ~ (168,148,113); 題簽 pale).
* figures/slip_ink_<vol>.png: the printed 題簽 title (its worn frame is redrawn in TikZ) cut from the cover scan as an
  ink layer (RGBA: ink colour, alpha from density), without the stains of the copy.
Cover box and 題簽 box measured on scans qian_003 / kun_001 (12.41 px/mm).
"""
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parent.parent
FIG = ROOT / 'figures'
PX = 12.41
DPI = 200
COVER = {'qian': ('qian_003', (1674, 182)), 'kun': ('kun_001', (1665, 188))}   # scan, cover top-left px
SLIP = (5.0, 2.5, 47.5, 189.0)        # 題簽 box on the cover, mm (x0, y0, x1, y1)


def paper(w, h, base, fibre_tone, seed, cloud_amp=0.10, fibres=900):
    rng = np.random.default_rng(seed)
    a = np.empty((h, w, 3))
    a[:] = base
    cloud = Image.fromarray((rng.random((h // 24 + 1, w // 24 + 1)) * 255).astype('uint8'))
    cloud = np.asarray(cloud.resize((w, h), Image.BICUBIC).filter(ImageFilter.GaussianBlur(20)), float) / 255
    a *= (1 - cloud_amp / 2 + cloud_amp * cloud)[..., None]
    fib = Image.new('L', (w, h), 0)
    px = fib.load()
    for _ in range(int(w * h / fibres)):
        x, y = rng.integers(0, w), rng.integers(0, h)
        ang = rng.normal(np.pi / 2, 0.6)
        ln = rng.integers(6, 30)
        val = int(rng.integers(40, 120))
        for t in range(ln):
            xx, yy = int(x + t * np.cos(ang)), int(y + t * np.sin(ang))
            if 0 <= xx < w and 0 <= yy < h:
                px[xx, yy] = max(px[xx, yy], val)
    fib = np.asarray(fib.filter(ImageFilter.GaussianBlur(0.7)), float) / 255
    a = a * (1 - 0.3 * fib[..., None]) + np.array(fibre_tone) * 0.3 * fib[..., None]
    a += rng.normal(0, 2.2, a.shape)
    return Image.fromarray(np.clip(a, 0, 255).astype('uint8'))


def slip_ink(vol):
    scan, (cx, cy) = COVER[vol]
    im = Image.open(ROOT / 'scans' / 'tsukuba' / f'{scan}.png').convert('RGB')
    x0, y0, x1, y1 = SLIP
    box = (int(cx + x0 * PX), int(cy + y0 * PX), int(cx + x1 * PX), int(cy + y1 * PX))
    g = np.asarray(im.crop(box).convert('L'), np.float32)
    bg = ndi.grey_closing(g, size=(45, 45))             # local paper level (ink removed)
    bg = ndi.uniform_filter(bg, 25)
    d = np.clip((bg - g) / np.maximum(bg, 1), 0, 1)       # relative darkness
    H, W = d.shape
    yy, xx = np.mgrid[0:H, 0:W]
    edge = np.minimum.reduce([xx, W - 1 - xx, yy, H - 1 - yy]) / PX      # mm from the slip edge
    band = (edge > 0.8) & (edge < 6.5)                    # printed frame with cloud pattern
    centre = edge >= 6.5                                  # title
    alpha = np.zeros_like(d)
    for region, lo, hi, minsize in ((centre, 0.30, 0.55, 2.0),):   # frame: too worn, drawn in TikZ
        a = np.clip((d - lo) / (hi - lo), 0, 1) * region
        lab, n = ndi.label(a > 0.3)
        sizes = ndi.sum(a > 0.3, lab, range(1, n + 1))
        keep = np.isin(lab, [i + 1 for i, s in enumerate(sizes) if s >= minsize * PX * PX])
        a *= ndi.binary_dilation(keep, iterations=3)       # drop stains and specks
        alpha = np.maximum(alpha, a)
    rgba = np.zeros(g.shape + (4,), np.uint8)
    rgba[..., :3] = (38, 32, 26)
    rgba[..., 3] = (alpha ** 0.9 * 255).astype(np.uint8)
    out = FIG / f'slip_ink_{vol}.png'
    Image.fromarray(rgba, 'RGBA').save(out)
    return out


def main():
    FIG.mkdir(exist_ok=True)
    w, h = round(182 / 25.4 * DPI), round(251 / 25.4 * DPI)
    paper(w, h, (168, 148, 113), (196, 178, 140), 11, cloud_amp=0.14, fibres=700).save(
        FIG / 'cover_paper.jpg', quality=90)
    sw, sh = round((SLIP[2] - SLIP[0]) / 25.4 * DPI), round((SLIP[3] - SLIP[1]) / 25.4 * DPI)
    paper(sw, sh, (226, 220, 204), (205, 198, 180), 12, cloud_amp=0.06).save(FIG / 'slip_paper.jpg', quality=92)
    for vol in COVER:
        print(slip_ink(vol))


if __name__ == '__main__':
    main()
