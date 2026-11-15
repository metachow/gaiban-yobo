"""Cut one glyph from a page by column number and a y range in page pixels (as read off the
full-resolution strips of tools/zoom_cols.py, which are not scaled; bottom strips start at
H/2 - 60).  python -I tools/cut_glyph.py qian_005 R 1 80 175 work/glyph/x.png"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from measure_page import measure, split_opening  # noqa: E402

name, half, col, y0, y1, out = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5]), sys.argv[6]
cols = measure(name, half)
im = Image.open(Path(__file__).resolve().parent.parent / 'scans' / 'tsukuba' / f'{name}.png').convert('RGB')
L, R = split_opening(np.asarray(im))
pg = im.crop(L if half == 'L' else R)
x = cols[col - 1][0]
w = 105                                  # half a column pitch (~14.5 mm = 180 px)
Path(out).parent.mkdir(parents=True, exist_ok=True)
pg.crop((int(x - w), y0, int(x + w), y1)).save(out)
