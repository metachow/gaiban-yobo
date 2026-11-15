"""Cut the same passage from our base copy (Tsukuba) and a second copy of the same blocks, side by side.

The second copy's openings are registered to the Tsukuba opening (scale + shift, found on a reduced
image by phase correlation), then each passage is refined locally by cross-correlation.
Passages are located by their text in KuroNet's character boxes (work/kuronet/<key>.json) or given
as a box in mm-free pixel coordinates of the Tsukuba opening.

    python -I -X utf8 tools/compare_copy.py <second-copy dir> <spec.tsv> <out dir>

spec.tsv: id <TAB> key <TAB> column hint (our 第N列, 0 = any) <TAB> text to find  (or  box=x0,y0,x1,y1)
Second copy: <dir>/NNN.jpg numbered openings; OFFSET maps a Tsukuba opening to its number there.
Writes <out>/<id>.jpg (Tsukuba left, second copy right) and <out>/sheet_N.jpg contact sheets."""
import difflib
import re
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).parent))
from kuronet_sheet import kn_cols, norm  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SCANS = ROOT / 'scans' / 'tsukuba'
OFFSET = {'q': -2, 'k': 27}        # Kyoto RB00033351: qian_007 = 005, kun_002 = 029
FONT = ImageFont.truetype(str(ROOT / 'fonts' / 'BIZ-UDMinchoM.ttc'), 34)
_cache = {}


def gray(im, f):
    g = im.convert('L').resize((im.width // f, im.height // f), Image.LANCZOS)
    a = np.asarray(g, dtype=np.float32)
    return 255 - a                  # ink positive


def phase_peak(a, b):
    """shift (dy, dx) that moves b onto a, and peak strength."""
    h = max(a.shape[0], b.shape[0])
    w = max(a.shape[1], b.shape[1])
    A = np.zeros((h, w), np.float32)
    B = np.zeros((h, w), np.float32)
    A[:a.shape[0], :a.shape[1]] = a - a.mean()
    B[:b.shape[0], :b.shape[1]] = b - b.mean()
    R = np.fft.fft2(A) * np.conj(np.fft.fft2(B))
    r = np.fft.ifft2(R / (np.abs(R) + 1e-6)).real
    i = np.unravel_index(np.argmax(r), r.shape)
    dy, dx = i
    if dy > h // 2:
        dy -= h
    if dx > w // 2:
        dx -= w
    return dy, dx, r[i]


def register(tsu, other):
    """-> s, ty, tx with  other_xy = (tsu_xy - t) / s ... expressed as tsu = s*other + t."""
    f = 8
    a = gray(tsu, f)
    best = None
    for s in np.arange(0.92, 1.081, 0.004):
        o = other.convert('L').resize((int(other.width * s / f), int(other.height * s / f)), Image.LANCZOS)
        b = 255 - np.asarray(o, dtype=np.float32)
        dy, dx, p = phase_peak(a, b)
        if best is None or p > best[0]:
            best = (p, s, dy * f, dx * f)
    return best[1], best[2], best[3]


def opening(key):
    vol = {'q': 'qian', 'k': 'kun'}[key[0]]
    n = int(key[1:4])
    return SCANS / f'{vol}_{n:03d}.png', n + OFFSET[key[0]]


def load(key, other_dir):
    tp, on = opening(key)
    if tp not in _cache:
        tsu = Image.open(tp).convert('RGB')
        oth = Image.open(Path(other_dir) / f'{on:03d}.jpg').convert('RGB')
        s, ty, tx = register(tsu, oth)
        print(f'{tp.name} <- {on:03d}.jpg  scale {s:.3f}  shift {tx:+.0f},{ty:+.0f}', flush=True)
        _cache[tp] = (tsu, oth, s, ty, tx)
    return _cache[tp]


def find_box(key, hint, text):
    m = re.match(r'box=(\d+),(\d+),(\d+),(\d+)', text)
    if m:
        return tuple(map(int, m.groups())), ''
    kk = key if (ROOT / 'work' / 'kuronet' / f'{key}.json').exists() else key[:4] + 'RL'
    cols = kn_cols(kk)
    if key[-1] in 'RL' and kk.endswith('RL'):        # opening-wide file: keep this page's columns
        mid = 2808
        cols = [c for c in cols if (c[0][0] > mid) == (key[-1] == 'R')]
    q = norm(text)
    cands = []
    for ci, col in enumerate(cols):
        s = norm(''.join(t[3] for t in col))
        sm = difflib.SequenceMatcher(None, s, q, autojunk=False)
        blk = sm.find_longest_match(0, len(s), 0, len(q))
        score = blk.size / max(1, len(q))
        # extend to the whole query around the longest block
        i0 = max(0, blk.a - blk.b)
        i1 = min(len(col), i0 + len(q))
        near = 0 if not hint else -abs(ci + 1 - hint) * 0.02     # hint = KuroNet column, 1-based
        cands.append((score + near, ci, i0, i1))
    score, ci, i0, i1 = max(cands)
    items = cols[ci][i0:i1] or cols[ci]
    xs = [t[2] for t in items]
    x0 = min(x for x, y, w, h in xs)
    x1 = max(x + w for x, y, w, h in xs)
    y0 = min(y for x, y, w, h in xs)
    y1 = max(y + h for x, y, w, h in xs)
    cw = x1 - x0
    found = ''.join(t[3] for t in items)
    return (int(x0 - 0.45 * cw), int(y0 - 0.9 * cw), int(x1 + 0.75 * cw), int(y1 + 0.9 * cw)), found


def refine(tsu, oth, s, ty, tx, box):
    x0, y0, x1, y1 = box
    # predicted box in the other copy
    px0, py0 = (x0 - tx) / s, (y0 - ty) / s
    pw, ph = (x1 - x0) / s, (y1 - y0) / s
    f = 2
    tpl = gray(tsu.crop(box), f)
    m = 80
    win = (int(px0 - m), int(py0 - m), int(px0 + pw + m), int(py0 + ph + m))
    w = oth.crop(win).resize((int((win[2] - win[0]) * s / f), int((win[3] - win[1]) * s / f)), Image.LANCZOS)
    wa = 255 - np.asarray(w.convert('L'), dtype=np.float32)
    th, tw = tpl.shape
    t = (tpl - tpl.mean()) / (tpl.std() + 1e-6)
    best = (-9, 0, 0)
    for dy in range(0, wa.shape[0] - th + 1, 2):
        for dx in range(0, wa.shape[1] - tw + 1, 2):
            p = wa[dy:dy + th, dx:dx + tw]
            c = float(((p - p.mean()) * t).mean() / (p.std() + 1e-6))
            if c > best[0]:
                best = (c, dy, dx)
    c, dy, dx = best
    ox0 = win[0] + dx * f / s
    oy0 = win[1] + dy * f / s
    return (int(ox0), int(oy0), int(ox0 + pw), int(oy0 + ph)), c


def pair(tsu, oth, s, box, obox, label):
    a = tsu.crop(box)
    b = oth.crop(obox).resize(a.size, Image.LANCZOS)
    k = 1.0 if a.height <= 900 else 900 / a.height
    a = a.resize((int(a.width * k), int(a.height * k)), Image.LANCZOS)
    b = b.resize(a.size, Image.LANCZOS)
    out = Image.new('RGB', (a.width * 2 + 30, a.height + 50), 'white')
    out.paste(a, (0, 50))
    out.paste(b, (a.width + 30, 50))
    d = ImageDraw.Draw(out)
    d.text((4, 4), label, font=FONT, fill=(200, 0, 0))
    return out


def main():
    other_dir, spec, out = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])
    out.mkdir(parents=True, exist_ok=True)
    tiles = []
    for line in spec.read_text(encoding='utf-8').splitlines():
        if not line.strip() or line.startswith('#'):
            continue
        iid, key, hint, text = line.split('\t')[:4]
        tsu, oth, s, ty, tx = load(key, other_dir)
        box, found = find_box(key, int(hint), text)
        obox, c = refine(tsu, oth, s, ty, tx, box)
        print(f'{iid} {key} col~{hint} want {text} | KuroNet {found} | ncc {c:.2f}', flush=True)
        t = pair(tsu, oth, s, box, obox, f'{iid}  {key}')
        t.save(out / f'{iid}.jpg', quality=90)
        tiles.append(t)
    # contact sheets, about 1900 px wide
    n, row, rows, sheet_i = 0, [], [], 1

    def flush_rows(rows, i):
        W = max(sum(t.width for t in r) + 20 * (len(r) - 1) for r in rows)
        H = sum(max(t.height for t in r) for r in rows) + 20 * (len(rows) - 1)
        sh = Image.new('RGB', (W, H), (235, 235, 235))
        y = 0
        for r in rows:
            x = 0
            for t in r:
                sh.paste(t, (x, y))
                x += t.width + 20
            y += max(t.height for t in r) + 20
        sh.save(out / f'sheet_{i}.jpg', quality=88)

    for t in tiles:
        if row and sum(x.width for x in row) + t.width > 2600:
            rows.append(row)
            row = []
        row.append(t)
        if len(rows) == 2:
            flush_rows(rows, sheet_i)
            sheet_i += 1
            rows = []
    if row:
        rows.append(row)
    if rows:
        flush_rows(rows, sheet_i)


if __name__ == '__main__':
    main()
