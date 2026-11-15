"""Label box per figure page (mm, page top-left), from the detected label blobs
(work/labels/<key>.png): start at the topmost blob near the fore-edge and grow by
blobs within 6 mm; manual corrections in text/label_fix.yaml override.
Writes work/label_boxes.json and work/labelbox_<n>.jpg (boxes drawn on the scans)."""
import json
import sys
from pathlib import Path

import numpy as np
import yaml
from PIL import Image, ImageDraw
from scipy import ndimage as ndi

sys.path.insert(0, str(Path(__file__).parent))
from measure_page import split_opening  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PX = 12.41
KEYS = [f'qian_{i:03d}' for i in range(7, 28)] + [f'kun_{i:03d}' for i in range(3, 26)]


def auto_box(mask):
    lab, n = ndi.label(ndi.binary_dilation(mask, iterations=3))
    objs = [(i + 1, sl) for i, sl in enumerate(ndi.find_objects(lab))]
    if not objs:
        return None
    W = mask.shape[1]
    objs = [(i, sl) for i, sl in objs if sl[1].start > W - 60 * PX]
    if not objs:
        return None
    # seed: the topmost blob that is not a speck
    big = [o for o in objs if max(o[1][0].stop - o[1][0].start, o[1][1].stop - o[1][1].start) > 2.5 * PX]
    i, sl = min(big or objs, key=lambda o: o[1][0].start)
    box = [sl[1].start, sl[0].start, sl[1].stop, sl[0].stop]
    grown = True
    while grown:
        grown = False
        for _, s in objs:
            b = [s[1].start, s[0].start, s[1].stop, s[0].stop]
            if b[0] >= box[0] and b[1] >= box[1] and b[2] <= box[2] and b[3] <= box[3]:
                continue
            g = 6 * PX
            if b[0] < box[2] + g and b[2] > box[0] - g and b[1] < box[3] + g and b[3] > box[1] - g:
                box = [min(box[0], b[0]), min(box[1], b[1]), max(box[2], b[2]), max(box[3], b[3])]
                grown = True
    pad = 1.5 * PX
    return [round((box[0] - pad) / PX, 1), round((box[1] - pad) / PX, 1),
            round((box[2] + pad) / PX, 1), round((box[3] + pad) / PX, 1)]


def main():
    fix_path = ROOT / 'text' / 'label_fix.yaml'
    fixes = yaml.safe_load(fix_path.read_text(encoding='utf-8')) if fix_path.exists() else {}
    fixes = fixes or {}
    boxes = {}
    tiles = []
    for k in KEYS:
        m = np.asarray(Image.open(ROOT / 'work' / 'labels' / f'{k}.png')) > 0
        box = fixes.get(k) or auto_box(m)
        boxes[k] = box
        im = Image.open(ROOT / 'scans' / 'tsukuba' / f'{k}.png').convert('RGB')
        L, R = split_opening(np.asarray(im))
        pg = im.crop(R)
        d = ImageDraw.Draw(pg)
        if box:
            d.rectangle([v * PX for v in box], outline=(255, 0, 0), width=8)
        W = pg.width
        c = pg.crop((W - int(100 * PX), 0, W, int(130 * PX))).resize((300, 390), Image.LANCZOS)
        tiles.append((k + (' *' if k in fixes else ''), c))
    (ROOT / 'work' / 'label_boxes.json').write_text(json.dumps(boxes, indent=1))
    cols, W, H = 8, 300, 408
    for part in range(2):
        sub = tiles[part * 22:(part + 1) * 22]
        rows = -(-len(sub) // cols)
        sh = Image.new('RGB', (cols * W, rows * H), 'white')
        d = ImageDraw.Draw(sh)
        for i, (k, c) in enumerate(sub):
            x, y = (i % cols) * W, (i // cols) * H
            sh.paste(c, (x, y + 18))
            d.text((x + 4, y + 3), k, fill='black')
        sh.save(ROOT / 'work' / f'labelbox_{part}.jpg', quality=85)


if __name__ == '__main__':
    main()
