"""Split one column of a page into glyph segments (gaps in the row projection of the ink)
and write an index strip, so single characters can be cut by number.
    python -I tools/seg_col.py qian_004 L 2          -> work/glyph/q004L_c2_index.jpg
    python -I tools/seg_col.py qian_004 L 2 5 6      -> also cut segments 5 and 6 (joined)
                                                       -> work/glyph/q004L_c2_5-6.png
Column numbers as in measure_page (right to left)."""
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi

sys.path.insert(0, str(Path(__file__).parent))
from measure_page import measure, split_opening  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'work' / 'glyph'


def segments(name, half, col):
    cols = measure(name, half)
    im = Image.open(ROOT / 'scans' / 'tsukuba' / f'{name}.png').convert('RGB')
    L, R = split_opening(np.asarray(im))
    pg = im.crop(L if half == 'L' else R)
    x = cols[col - 1][0]
    pitch = abs(cols[0][0] - cols[1][0]) if len(cols) > 1 else 180
    x0, x1 = int(x - 0.48 * pitch), int(x + 0.48 * pitch)
    band = pg.crop((x0, 0, x1, pg.height))
    g = np.asarray(band.convert('L'), float)
    # ink, ignoring red seals (red >> blue)
    rgb = np.asarray(band, float)
    red = (rgb[..., 0] - rgb[..., 2]) > 45
    ink = (g < np.median(g) - 60) & ~red
    ink = ndi.binary_opening(ink, iterations=1)
    prof = ndi.uniform_filter1d(ink.sum(1).astype(float), 5) > 1.5
    segs, y = [], 0
    while y < len(prof):
        if prof[y]:
            s = y
            while y < len(prof) and prof[y]:
                y += 1
            if y - s > 8:
                segs.append((s, y))
        y += 1
    # merge segments separated by tiny gaps (parts of one character)
    merged = []
    for s, e in segs:
        if merged and s - merged[-1][1] < 6:
            merged[-1] = (merged[-1][0], e)
        else:
            merged.append((s, e))
    return band, merged


def main():
    name, half, col = sys.argv[1], sys.argv[2], int(sys.argv[3])
    pick = [int(v) for v in sys.argv[4:]]
    band, segs = segments(name, half, col)
    OUT.mkdir(parents=True, exist_ok=True)
    key = f'{name[0]}{name.split("_")[1]}{half}'
    if pick:
        s = segs[min(pick) - 1][0]
        e = segs[max(pick) - 1][1]
        c = band.crop((0, max(s - 12, 0), band.width, min(e + 12, band.height)))
        tag = f'{min(pick)}-{max(pick)}' if len(pick) > 1 else str(pick[0])
        c.save(OUT / f'{key}_c{col}_{tag}.png')
        print(OUT / f'{key}_c{col}_{tag}.png')
        return
    # index strip: the column cut into pieces side by side, numbered
    pieces = []
    for k, (s, e) in enumerate(segs, 1):
        c = band.crop((0, max(s - 6, 0), band.width, min(e + 6, band.height)))
        c.thumbnail((110, 110))
        tile = Image.new('RGB', (120, 128), 'white')
        tile.paste(c, ((120 - c.width) // 2, 16))
        ImageDraw.Draw(tile).text((3, 2), str(k), fill=(220, 0, 0))
        pieces.append(tile)
    per = 12
    rows = -(-len(pieces) // per)
    sheet = Image.new('RGB', (per * 120, rows * 128), 'white')
    for k, t in enumerate(pieces):
        sheet.paste(t, ((k % per) * 120, (k // per) * 128))
    sheet.save(OUT / f'{key}_c{col}_index.jpg', quality=90)
    print(f'{len(segs)} segments ->', OUT / f'{key}_c{col}_index.jpg')


if __name__ == '__main__':
    main()
