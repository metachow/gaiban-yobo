"""Picture sheets of every place where KuroNet disagrees with our transcription.

For each body page: our columns (ruby/notes flattened) are aligned with KuroNet's columns
(tools/kuronet_fetch.py output, with character boxes from work/kuronet/<key>.json); after
normalising forms and KuroNet's usual look-alike confusions (亜/巫/匣/画, 云/土/六, ム/△ ...),
each remaining differing stretch is cut from the scan using KuroNet's boxes and drawn with
our reading and KuroNet's.  Writes work/kn_sheets/<key>.jpg and work/kn_diffs.tsv
(key, column, ours, kuronet, scan box) for the review."""
import difflib
import json
import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).parent))
from kuronet_compare import NORM, our_columns  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
FONT = ImageFont.truetype(str(ROOT / 'fonts' / 'BIZ-UDMinchoM.ttc'), 26)
SMALL = ImageFont.truetype(str(ROOT / 'fonts' / 'BIZ-UDMinchoM.ttc'), 16)

for group in ['亜巫匣画亞', '云土六士', 'ム△', 'ゾヅ', '候侯', '二々', '韃靼粗趙', 'ビじゼ', '己巳已', '徳德',
              '爲為', '鑽讃', '璃瑪', 'ゝヽ']:
    for c in group[1:]:
        NORM[c] = NORM.get(group[0], group[0])


def norm(s):
    return ''.join(NORM.get(c, c) for c in s)


def kn_cols(key):
    cur = json.loads((ROOT / 'work' / 'kuronet' / f'{key}.json').read_text(encoding='utf-8'))
    a = []
    for e in cur['selections'][0]['members']:
        x, y, w, h = map(int, e['@id'].split('xywh=')[1].split(','))
        a.append((x + w / 2, y + h / 2, (x, y, w, h), e['metadata'][0]['value'][0]['resource']['marker']['text']))
    a.sort(key=lambda t: -t[0])
    cols = []
    for c in a:
        if cols and abs(cols[-1]['x'] - c[0]) < 55:
            cols[-1]['items'].append(c)
            n = len(cols[-1]['items'])
            cols[-1]['x'] = (cols[-1]['x'] * (n - 1) + c[0]) / n
        else:
            cols.append({'x': c[0], 'items': [c]})
    return [sorted(c['items'], key=lambda t: t[1]) for c in cols]


def best(ours_col, kcols):
    no = norm(ours_col)
    top = (0, [])
    for i in range(len(kcols)):
        for j in (i, i + 1):
            if j < len(kcols):
                items = kcols[i] + (kcols[j] if j > i else [])
                r = difflib.SequenceMatcher(None, no, norm(''.join(t[3] for t in items))).ratio()
                if r > top[0]:
                    top = (r, items)
    return top


def main():
    out_dir = ROOT / 'work' / 'kn_sheets'
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = ['key\tcol\tours\tkuronet\tbox']
    total = 0
    for kp in sorted((ROOT / 'work' / 'kuronet').glob('*.json')):
        key = kp.stem
        vol = 'qian' if key[0] == 'q' else 'kun'
        tp = ROOT / 'text' / vol / f'{key}.txt'
        if not tp.exists() or key in ('q004L', 'q005RL', 'k026R'):
            continue
        scan = Image.open(ROOT / 'scans' / 'tsukuba' / f'{vol}_{key[1:4]}.png').convert('RGB')
        kcols = kn_cols(key)
        tiles = []
        for c, oc in enumerate(our_columns(tp), 1):
            r, items = best(oc, kcols)
            if r < 0.5:
                continue
            ks = ''.join(t[3] for t in items)
            sm = difflib.SequenceMatcher(None, norm(oc), norm(ks), autojunk=False)
            for tag, i1, i2, j1, j2 in sm.get_opcodes():
                if tag == 'equal':
                    continue
                o, k = oc[i1:i2], ks[j1:j2]
                if len(o) > 6 or len(k) > 6:        # a whole 割注 read in another order: skip
                    continue
                # box: KuroNet's boxes of the stretch, or the neighbours' gap for a deletion
                boxes = [t[2] for t in items[max(j1 - 1, 0):min(max(j2, j1 + 1) + 1, len(items))]]
                x0 = min(b[0] for b in boxes) - 30
                y0 = min(b[1] for b in boxes) - 10
                x1 = max(b[0] + b[2] for b in boxes) + 30
                y1 = max(b[1] + b[3] for b in boxes) + 10
                crop = scan.crop((x0, y0, x1, y1))
                crop.thumbnail((150, 300))
                tile = Image.new('RGB', (260, 320), 'white')
                tile.paste(crop, (0, 20))
                d = ImageDraw.Draw(tile)
                d.text((2, 0), f'{c}列 #{total + 1}', fill=(150, 0, 0), font=SMALL)
                d.text((158, 40), '本', fill=(0, 0, 160), font=SMALL)
                d.text((158, 60), o or '∅', fill=(0, 0, 160), font=FONT)
                d.text((158, 170), 'KN', fill=(0, 120, 0), font=SMALL)
                d.text((158, 190), k or '∅', fill=(0, 120, 0), font=FONT)
                tiles.append(tile)
                total += 1
                rows.append(f'{key}\t{c}\t{o}\t{k}\t{x0},{y0},{x1},{y1}\t#{total}')
        if tiles:
            per = 8
            sheet = Image.new('RGB', (per * 260, -(-len(tiles) // per) * 320), (230, 230, 230))
            for i, t in enumerate(tiles):
                sheet.paste(t, ((i % per) * 260, (i // per) * 320))
            sheet.save(out_dir / f'{key}.jpg', quality=85)
    (ROOT / 'work' / 'kn_diffs.tsv').write_text('\n'.join(rows), encoding='utf-8')
    print('differences shown:', total)


if __name__ == '__main__':
    main()
