"""Full-resolution strips of 3 columns (top / bottom half) for close reading, using the
column centres found by measure_page.  python -I tools/zoom_cols.py qian_004 L work/zoom/pref4
-> <prefix>_c1-3_top.jpg ... (column numbers in red along the top)."""
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).parent))
from measure_page import measure, split_opening  # noqa: E402

name, half, prefix = sys.argv[1:4]
cols = measure(name, half)                      # (x px, top, bottom) right to left
im = Image.open(Path(__file__).resolve().parent.parent / 'scans' / 'tsukuba' / f'{name}.png').convert('RGB')
L, R = split_opening(np.asarray(im))
pg = im.crop(L if half == 'L' else R)
H = pg.height
for g in range(0, len(cols), 3):
    grp = cols[g:g + 3]
    x1 = min(grp[0][0] + 100, pg.width)
    x0 = max(grp[-1][0] - 100, 0)
    for tag, (a, b) in (('top', (0, H // 2 + 60)), ('bot', (H // 2 - 60, H))):
        c = pg.crop((x0, a, x1, b))
        d = ImageDraw.Draw(c)
        for k, (x, _, _) in enumerate(grp):
            d.text((x - x0 - 4, 2), str(g + k + 1), fill=(220, 0, 0))
        c.save(f'{prefix}_c{g + 1}-{g + len(grp)}_{tag}.jpg', quality=92)
