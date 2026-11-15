"""Measure a text half-page of an opening: page box, column centres, first/last ink row
of each column, and the main glyph size.  Usage:
    python -I tools/measure_page.py qian_007 L [--plot work/m.png]
L/R = left/right half of the opening.  Prints mm values (page box origin top-left)."""
import sys
import numpy as np
from PIL import Image
from scipy import ndimage as ndi

ROOT = __file__.rsplit('tools', 1)[0]


def page_box(rgb):
    """Paper is warm (R-B large), the backdrop is neutral grey."""
    a = rgb.astype(float)
    warm = (a[..., 0] - a[..., 2]) > 18
    rows = np.where(warm.mean(1) > 0.3)[0]
    cols = np.where(warm.mean(0) > 0.3)[0]
    return cols[0], rows[0], cols[-1], rows[-1]


def split_opening(rgb):
    x0, y0, x1, y1 = page_box(rgb)
    # the gutter: darkest narrow column band near the middle
    g = rgb[y0:y1, :, :].mean(2).mean(0)
    mid = (x0 + x1) // 2
    win = g[mid - 250: mid + 250]
    gx = mid - 250 + int(np.argmin(ndi.uniform_filter1d(win, 9)))
    return (x0, y0, gx, y1), (gx, y0, x1, y1)


def ink(gray, thr=None):
    if thr is None:
        paper = np.median(gray)
        thr = paper - 70
    return gray < thr


def measure(name, half, plot=None):
    rgb = np.asarray(Image.open(f'{ROOT}scans/tsukuba/{name}.png').convert('RGB'))
    L, R = split_opening(rgb)
    x0, y0, x1, y1 = L if half == 'L' else R
    pg = rgb[y0:y1, x0:x1]
    gray = pg.mean(2)
    m = ink(gray)
    # ignore the page stack / fold at the outer edge and the gutter
    m[:, :60] = False
    m[:, -60:] = False
    m[:40] = False
    m[-40:] = False
    m = ndi.binary_opening(m, iterations=1)
    prof = ndi.uniform_filter1d(m.sum(0).astype(float), 41)
    # peaks = main columns (ruby columns are much weaker)
    from scipy.signal import find_peaks
    pk, props = find_peaks(prof, height=prof.max() * 0.25, distance=150)
    cols = sorted(pk, reverse=True)
    out = []
    for c in cols:
        band = m[:, max(c - 45, 0): c + 45]
        rows = np.where(band.sum(1) > 2)[0]
        out.append((c, rows[0], rows[-1]))
    h, w = gray.shape
    dpi_mm = h / 251.0      # page height 25.1 cm (catalogue)
    print(f'{name} {half}: page {w}x{h}px = {w/dpi_mm:.1f}x{h/dpi_mm:.1f} mm '
          f'(origin {x0},{y0}; {dpi_mm:.2f} px/mm)')
    for k, (c, t, b) in enumerate(out, 1):
        print(f'  col {k}: x={c/dpi_mm:6.1f} mm  top={t/dpi_mm:6.1f}  bottom={b/dpi_mm:6.1f}')
    if len(out) > 1:
        xs = [c for c, _, _ in out]
        print(f'  pitch {np.mean(-np.diff(xs))/dpi_mm:.2f} mm')
    if plot:
        im = Image.fromarray(pg).convert('RGB')
        from PIL import ImageDraw
        d = ImageDraw.Draw(im)
        for c, t, b in out:
            d.line([(c, t), (c, b)], fill=(255, 0, 0), width=5)
        im.thumbnail((900, 1300))
        im.save(plot)
    return out


if __name__ == '__main__':
    plot = sys.argv[sys.argv.index('--plot') + 1] if '--plot' in sys.argv else None
    measure(sys.argv[1], sys.argv[2], plot)
