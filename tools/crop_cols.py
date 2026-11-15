"""Reading crops for transcription: for a text half-page, find the main columns and cut
groups of 3 columns (right to left) x top/bottom halves, plus a ruler of column numbers.
    python -I tools/crop_cols.py qian_007 L      -> work/cols/q007L_c1-3_top.jpg ...
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
from scipy.signal import find_peaks

sys.path.insert(0, str(Path(__file__).parent))
from measure_page import split_opening  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PX = 12.41


def columns(gray):
    m = gray < np.median(gray) - 70
    m[:, :70] = m[:, -70:] = False
    m[:50] = m[-50:] = False
    m = ndi.binary_opening(m, iterations=1)
    prof = ndi.uniform_filter1d(m.sum(0).astype(float), 41)
    pk, _ = find_peaks(prof, height=prof.max() * 0.22, distance=int(10 * PX))
    rows = np.where(m.sum(1) > 3)[0]
    return sorted(pk, reverse=True), rows.min(), rows.max()


def main(name, half, scale=0.8):
    vol, n = name.split('_')
    key = f'{vol[0]}{n}{half}'
    im = Image.open(ROOT / 'scans' / 'tsukuba' / f'{name}.png').convert('RGB')
    L, R = split_opening(np.asarray(im))
    box = L if half == 'L' else R
    pg = im.crop(box)
    gray = np.asarray(pg.convert('L'), float)
    cols, top, bot = columns(gray)
    out = ROOT / 'work' / 'cols'
    out.mkdir(parents=True, exist_ok=True)
    pitch = 14.5 * PX
    mid = (top + bot) // 2
    files = []
    for g in range(0, len(cols), 3):
        grp = cols[g:g + 3]
        x1 = int(min(grp[0] + 0.62 * pitch, pg.width))
        x0 = int(max(grp[-1] - 0.62 * pitch, 0))
        for tag, (a, b) in (('top', (max(top - 60, 0), mid + 90)), ('bot', (mid - 90, min(bot + 60, pg.height)))):
            c = pg.crop((x0, a, x1, b))
            c = c.resize((int(c.width * scale), int(c.height * scale)), Image.LANCZOS)
            d = ImageDraw.Draw(c)
            for k, x in enumerate(grp):       # column numbers along the top edge
                d.text(((x - x0) * scale - 4, 2), str(g + k + 1), fill=(220, 0, 0))
            f = out / f'{key}_c{g + 1}-{g + len(grp)}_{tag}.jpg'
            c.save(f, quality=90)
            files.append(f.name)
    print(key, len(cols), 'columns', ' '.join(files))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
