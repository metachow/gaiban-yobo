"""Clean a hand-coloured figure page: divide out the paper colour per channel (a smooth
quadratic surface fitted to paper pixels), keep the colouring, set everything outside
the figure (stains, specks, the printed country label) to white, crop to the figure.

    python -I tools/clean_plate.py qian_007 R figures/qian_007.png
prints the crop box in mm from the page's top-left (page box as in measure_page)."""
import sys
from pathlib import Path
import numpy as np
from PIL import Image
from scipy import ndimage as ndi

sys.path.insert(0, __file__.rsplit('clean_plate.py', 1)[0])
from measure_page import split_opening, ROOT  # noqa: E402

PX_MM = 12.41
GAMMA = 1.1         # >1 darkens midtones
INK = 0.11          # darkest ink after cleaning (original scan: ~0.18)
TONE = None         # None: paper -> white; or an RGB paper tone, e.g. (247, 242, 230)
SHARPEN = True
FULL = False        # True: keep the whole page area (maps), no figure/label masking


def paper_surface(img, mask, k=8):
    H, W, _ = img.shape
    sm = img[::k, ::k]
    msk = mask[::k, ::k]
    h, w = msk.shape
    yy, xx = np.mgrid[0:h, 0:w]
    xs, ys = (xx / w).ravel(), (yy / h).ravel()
    A = np.stack([np.ones_like(xs), xs, ys, xs * xs, xs * ys, ys * ys], 1)
    coefs = []
    for c in range(3):
        cf, *_ = np.linalg.lstsq(A[msk.ravel()], sm[..., c].ravel()[msk.ravel()], rcond=None)
        coefs.append(cf)
    Y, X = np.mgrid[0:H, 0:W].astype(np.float32)
    X /= W
    Y /= H
    return np.stack([cf[0] + cf[1] * X + cf[2] * Y + cf[3] * X * X + cf[4] * X * Y + cf[5] * Y * Y
                     for cf in coefs], 2)


def clean(name, half, out_path, margin_px=70):
    rgb = np.asarray(Image.open(f'{ROOT}scans/tsukuba/{name}.png').convert('RGB'), np.float32)
    L, R = split_opening(rgb.astype(np.uint8))
    x0, y0, x1, y1 = L if half == 'L' else R
    pg = rgb[y0:y1, x0:x1]
    H, W, _ = pg.shape
    # paper pixels: bright and close to the median paper colour
    med = np.median(pg.reshape(-1, 3), 0)
    mask = (np.abs(pg - med).max(2) < 22)
    for _ in range(2):
        paper = paper_surface(pg, mask)
        rel = pg / paper
        mask = np.abs(rel - 1).max(2) < 0.07
    # levels with a fixed black point: (x - black) / (paper - black). Plain division
    # lifts the ink (48 -> 60 at the 1st percentile) and the lines look washed out.
    black = np.percentile(pg.reshape(-1, 3)[::7], 0.2, axis=0)
    rel = np.clip((pg - black) / (paper * 0.985 - black), 0, 1)
    rel = rel ** GAMMA                          # keep the midtones (pale washes) dense
    # paper fibres: within a few % of the paper they read as dirt on clean paper --
    # fade them out; pale washes (> 8 % off paper) are untouched
    d = 1 - rel.min(2)
    w = np.clip((d - 0.035) / 0.045, 0, 1)
    rel = 1 - (1 - rel) * w[..., None]
    rel = INK + (1 - INK) * rel                 # ink: deep but not pure black
    if TONE is not None:                        # paper -> a uniform light paper tone
        rel = rel * (np.array(TONE, np.float32) / 255)
    # figure mask: anything clearly off-white, joined generously, largest blobs only
    base = np.array(TONE if TONE is not None else (255, 255, 255), np.float32) / 255
    dev = (1 - (rel / base).min(2)) > 0.10
    mm = int(PX_MM)
    if half == 'R':      # gutter left, fold + page stack right
        dev[:, :7 * mm] = dev[:, -13 * mm:] = False
    else:
        dev[:, :13 * mm] = dev[:, -7 * mm:] = False
    dev[:7 * mm] = dev[-6 * mm:] = False
    dev = ndi.binary_opening(dev, iterations=2)
    # the printed label: small, uncoloured blobs in the upper right quarter
    lab, n = ndi.label(ndi.binary_closing(dev, iterations=2))
    objs = ndi.find_objects(lab)
    sat = (rel.max(2) - rel.min(2)) / base.mean()
    # the figures' main mass (big blobs), with everything inside their outline
    big = np.zeros_like(dev)
    for i, sl in enumerate(objs, 1):
        if max(sl[0].stop - sl[0].start, sl[1].stop - sl[1].start) > 25 * PX_MM:
            big[sl] |= lab[sl] == i
    zone = ndi.binary_fill_holes(ndi.binary_dilation(big, iterations=int(1 * PX_MM)))
    label = np.zeros_like(dev)
    edge = W - 13 * PX_MM if half == 'R' else W - 7 * PX_MM     # inner edge of the page stack
    for i, sl in enumerate(objs, 1):
        h, w = sl[0].stop - sl[0].start, sl[1].stop - sl[1].start
        cy, cx = (sl[0].start + sl[0].stop) / 2, (sl[1].start + sl[1].stop) / 2
        band = 40 if cy < 50 * PX_MM else 30           # label strip width from the page edge, mm
        if cx < edge - band * PX_MM or cy > 0.45 * H or w > 14 * PX_MM or h > 60 * PX_MM:
            continue
        if zone[int(cy), int(cx)]:                # centre inside a figure
            continue
        blob = lab[sl] == i
        if sat[sl][blob].mean() > 0.12:          # coloured: part of the figure
            continue
        label[sl] |= blob
    boxes_path = Path(ROOT, 'work', 'label_boxes.json')
    boxes = __import__('json').loads(boxes_path.read_text()) if boxes_path.exists() else {}
    if boxes.get(name):         # a fixed label box: its uncoloured ink is the label
        bx0, by0, bx1, by1 = [int(v * PX_MM) for v in boxes[name]]
        inbox = np.zeros_like(dev)
        inbox[by0:by1, bx0:bx1] = True
        coloured = ndi.binary_dilation(sat > 0.12, iterations=3) & ~ndi.binary_dilation(
            (rel / base).mean(2) < 0.45, iterations=2)           # colour, but not the ink's fringes
        label = dev & inbox & ~coloured
    dev &= ~label
    self_label = label
    Path(ROOT, 'work', 'labels').mkdir(parents=True, exist_ok=True)
    Image.fromarray(label).save(Path(ROOT, 'work', 'labels', f'{name}.png'))
    joined = ndi.binary_dilation(dev, iterations=25)
    lab, n = ndi.label(joined)
    sizes = ndi.sum(joined, lab, range(1, n + 1))
    keep = [i + 1 for i, s in enumerate(sizes) if s > 0.15 * sizes.max()]
    fig = np.isin(lab, keep)
    fig = ndi.binary_fill_holes(fig)
    if FULL:            # maps: keep the whole page except the page stack and the fold
        fig = np.zeros_like(fig)
        if half == 'L':
            fig[3 * mm:-3 * mm, 12 * mm:-int(1.5 * mm)] = True
        else:
            fig[3 * mm:-3 * mm, int(1.5 * mm):-12 * mm] = True
        self_label = np.zeros_like(fig)
    # soft edge between figure and white
    alpha = ndi.gaussian_filter(ndi.binary_erosion(fig, iterations=12).astype(np.float32), 4)
    alpha[ndi.binary_dilation(self_label, iterations=6)] = 0      # label even if close to the figure
    out = rel * alpha[..., None] + base * (1 - alpha[..., None])
    ys, xs = np.where(fig)
    t, b, l, r = ys.min(), ys.max(), xs.min(), xs.max()
    crop = Image.fromarray((out[t:b + 1, l:r + 1] * 255 + 0.5).astype(np.uint8))
    if SHARPEN:     # mild unsharp mask on lightness only (no new detail is invented)
        from PIL import ImageFilter
        ycc = crop.convert('YCbCr').split()
        y = ycc[0].filter(ImageFilter.UnsharpMask(radius=1.5, percent=55, threshold=5))
        crop = Image.merge('YCbCr', (y, ycc[1], ycc[2])).convert('RGB')
    crop.save(out_path)
    info = dict(page_w=W / PX_MM, page_h=H / PX_MM,
                x=l / PX_MM, y=t / PX_MM, w=(r - l + 1) / PX_MM, h=(b - t + 1) / PX_MM)
    # label columns: runs of the label mask's column projection (gap >= 0.6 mm)
    lab_mask = self_label & ~fig
    prof = lab_mask.sum(0) > 0
    runs, x = [], 0
    while x < W:
        if prof[x]:
            s = x
            gap = 0
            while x < W and gap < 0.6 * PX_MM:
                gap = 0 if prof[x] else gap + 1
                x += 1
            e = x - gap
            ys = np.where(lab_mask[:, s:e].any(1))[0]
            if e - s > 1.0 * PX_MM:
                runs.append([s / PX_MM, e / PX_MM, ys.min() / PX_MM, ys.max() / PX_MM])
        x += 1
    info['label_cols'] = [[round(v, 1) for v in rr] for rr in runs]
    print(name, half, ' '.join(f'{k}={v:.1f}' for k, v in info.items() if k != 'label_cols'),
          info['label_cols'])
    return info


if __name__ == '__main__':
    args = sys.argv[1:]
    if '--tone' in args:
        i = args.index('--tone')
        TONE = tuple(int(v) for v in args[i + 1].split(','))
        del args[i:i + 2]
    if '--gamma' in args:
        i = args.index('--gamma')
        GAMMA = float(args[i + 1])
        del args[i:i + 2]
    clean(args[0], args[1], args[2])
