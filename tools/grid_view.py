"""A page half with a 10 mm grid (labels in mm from the page box's top-left) for placing
free elements by hand.  python -I tools/grid_view.py kun_026 R work/grid_k026R.jpg"""
import sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, str(Path(__file__).parent))
from measure_page import split_opening  # noqa: E402

name, half, out = sys.argv[1:4]
im = Image.open(Path(__file__).resolve().parent.parent / 'scans' / 'tsukuba' / f'{name}.png').convert('RGB')
L, R = split_opening(np.asarray(im))
pg = im.crop(L if half == 'L' else R)
px = pg.height / 251.0
sc = 1000 / pg.height
pg = pg.resize((int(pg.width * sc), 1000), Image.LANCZOS)
d = ImageDraw.Draw(pg)
m = px * sc
for k in range(0, 260, 10):
    c = (255, 0, 0) if k % 50 == 0 else (255, 160, 160)
    d.line([(k * m, 0), (k * m, pg.height)], fill=c, width=1)
    d.line([(0, k * m), (pg.width, k * m)], fill=c, width=1)
    if k % 20 == 0:
        d.text((k * m + 2, 2), str(k), fill=(0, 0, 255))
        d.text((2, k * m + 2), str(k), fill=(0, 0, 255))
pg.save(out, quality=90)
