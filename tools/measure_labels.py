"""Geometry of each country label from its mask (work/labels/<key>.png). Every label has
the same structure: continent (small) at the right, country name (large) at the left,
its reading between. Columns touch in x, so take bands from the ink's extent:
right 6 mm = continent, left 8.5 mm = name. Writes work/label_geom.json (mm):
{key: {region: [x_centre, y_top, y_bottom], name: [x_centre, y_top, y_bottom]}}."""
import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parent.parent
PX = 12.41


def extent(sub, a, b):
    ys = np.where(sub[:, max(a, 0):b].sum(1) > 0)[0]
    return ys.min(), ys.max()


def main():
    boxes = json.loads((ROOT / 'work' / 'label_boxes.json').read_text())
    geom = {}
    for key, box in boxes.items():
        m = np.asarray(Image.open(ROOT / 'work' / 'labels' / f'{key}.png')) > 0
        x0, y0, x1, y1 = [int(v * PX) for v in box]
        sub = ndi.binary_opening(m[y0:y1, x0:x1], iterations=1)
        lab, n = ndi.label(sub)
        sizes = ndi.sum(sub, lab, range(1, n + 1))
        sub = np.isin(lab, [i + 1 for i, s in enumerate(sizes) if s > 40])     # drop specks
        xs = np.where(sub.sum(0) > 0)[0]
        xa, xb = xs.min(), xs.max()
        r6, l8 = int(6 * PX), int(8.5 * PX)
        ry = extent(sub, xb - r6, xb + 1)
        ny = extent(sub, xa, xa + l8)
        g = {'region': [round((x0 + xb - r6 / 2) / PX, 1), round((y0 + ry[0]) / PX, 1), round((y0 + ry[1]) / PX, 1)],
             'name': [round((x0 + xa + l8 / 2) / PX, 1), round((y0 + ny[0]) / PX, 1), round((y0 + ny[1]) / PX, 1)]}
        geom[key] = g
        print(key, g)
    (ROOT / 'work' / 'label_geom.json').write_text(json.dumps(geom, indent=1))


if __name__ == '__main__':
    main()
