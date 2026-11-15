"""Cut a seal from a page half as an ink layer on the paper tone: box in mm from the page
box's top-left.  python -I tools/cut_seal.py kun_026 R x0 y0 x1 y1 figures/seal_x.png"""
import sys
from pathlib import Path
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
sys.path.insert(0, str(Path(__file__).parent))
from measure_page import split_opening  # noqa: E402

name, half = sys.argv[1:3]
x0, y0, x1, y1 = map(float, sys.argv[3:7])
out = sys.argv[7]
im = Image.open(Path(__file__).resolve().parent.parent / 'scans' / 'tsukuba' / f'{name}.png').convert('RGB')
L, R = split_opening(np.asarray(im))
pg = im.crop(L if half == 'L' else R)
px = pg.height / 251.0
c = np.asarray(pg.crop((int(x0 * px), int(y0 * px), int(x1 * px), int(y1 * px)))).astype(np.float32)
g = c.mean(2)
paper = ndi.grey_closing(g, size=(41, 41))
dens = np.clip((paper - g) / 150.0, 0, 1)            # 0 paper .. 1 ink
dens = np.clip((dens - 0.12) / 0.6, 0, 1)
tone = np.array([246, 240, 226], np.float32)
ink = np.array([40, 34, 28], np.float32)
res = tone * (1 - dens[..., None]) + ink * dens[..., None]
Image.fromarray(res.astype(np.uint8)).save(out)
print(out, f'{x1 - x0:.1f} x {y1 - y0:.1f} mm')
