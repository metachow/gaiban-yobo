"""Picture sheets of every 振り仮名 in the body text, for proofreading the ruby.

Our columns are aligned with KuroNet's (work/kuronet/<key>.json, character boxes in the scan);
each ruby base is cut from the scan with room on its right for the ruby, enlarged, and drawn
beside our reading.  Writes work/ruby/<key>.jpg (numbered tiles) and work/ruby/list.tsv
(id, key, column, base, ruby, box).  Labels on the plates: work/ruby/labels.jpg."""
import difflib
import json
import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).parent))
from kuronet_sheet import kn_cols, norm  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'work' / 'ruby'
FONT = ImageFont.truetype(str(ROOT / 'fonts' / 'BIZ-UDMinchoM.ttc'), 30)
SMALL = ImageFont.truetype(str(ROOT / 'fonts' / 'BIZ-UDMinchoM.ttc'), 17)
TW, TH = 250, 330


def is_kanji(c):
    o = ord(c)
    return 0x3400 <= o <= 0x9FFF or 0xF900 <= o <= 0xFAFF or 0x20000 <= o <= 0x3FFFF or c in '々〻'


def flat_column(line):
    """-> flat text (ruby dropped, 割注 right half then left half, marks dropped), ruby groups
    [(start, end, ruby)] as indices into the flat text."""
    line = re.sub(r'^\^\d+(\.\d+)?', '', line)
    flat, groups, mark = [], [], None
    stops = {0}                    # a ruby base never runs back across 割注 edges or marks
    i = 0
    while i < len(line):
        ch = line[i]
        if ch == '｜':
            mark = len(flat)
        elif ch == '《':
            j = line.index('》', i)
            end = len(flat)
            start = mark if mark is not None else end
            if mark is None:
                taken = {k for g in groups for k in range(g[0], g[1])}
                while start > 0 and start not in stops and is_kanji(flat[start - 1]) and start - 1 not in taken:
                    start -= 1
            groups.append((start, end, line[i + 1:j]))
            mark = None
            i = j
        elif ch in '〔〕|。、　':
            stops.add(len(flat))
        else:
            flat.append(ch)
        i += 1
    return ''.join(flat), groups


def our_cols(path):
    return [flat_column(l) for l in path.read_text(encoding='utf-8').splitlines() if l and not l.startswith('#')]


def best(flat, kcols):
    no = norm(flat)
    top = (0, [])
    for i in range(len(kcols)):
        for j in (i, i + 1):
            if j < len(kcols):
                items = kcols[i] + (kcols[j] if j > i else [])
                items = sorted(items, key=lambda t: t[1])
                r = difflib.SequenceMatcher(None, no, norm(''.join(t[3] for t in items))).ratio()
                if r > top[0]:
                    top = (r, items)
    return top


def tile(crop, label, base, ruby):
    crop = crop.copy()
    s = min(160 / crop.width, (TH - 30) / crop.height, 3.0)
    crop = crop.resize((max(1, int(crop.width * s)), max(1, int(crop.height * s))), Image.LANCZOS)
    t = Image.new('RGB', (TW, TH), 'white')
    t.paste(crop, (0, 24))
    d = ImageDraw.Draw(t)
    d.text((2, 2), label, fill=(150, 0, 0), font=SMALL)
    y = 30
    for c in base:
        d.text((170, y), c, fill=(0, 0, 0), font=FONT)
        y += 34
    y = 30
    for c in ruby:
        d.text((210, y), c, fill=(0, 0, 170), font=SMALL)
        y += 20
    return t


def save_sheet(tiles, path, per=8):
    sheet = Image.new('RGB', (per * TW, -(-len(tiles) // per) * TH), (225, 225, 225))
    for i, t in enumerate(tiles):
        sheet.paste(t, ((i % per) * TW, (i // per) * TH))
    sheet.save(path, quality=88)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows = ['id\tkey\tcol\tbase\truby\tbox\tnote']
    n = 0
    for tp in sorted((ROOT / 'text').glob('*/*.txt')):
        key = tp.stem
        cols = our_cols(tp)
        if not any(g for _, g in cols):
            continue
        kp = ROOT / 'work' / 'kuronet' / f'{key}.json'
        if not kp.exists():
            print('no KuroNet boxes:', key)
            continue
        vol = 'qian' if key[0] == 'q' else 'kun'
        scan = Image.open(ROOT / 'scans' / 'tsukuba' / f'{vol}_{key[1:4]}.png').convert('RGB')
        kcols = kn_cols(key)
        tiles = []
        for c, (flat, groups) in enumerate(cols, 1):
            if not groups:
                continue
            r, items = best(flat, kcols)
            sm = difflib.SequenceMatcher(None, norm(flat), norm(''.join(t[3] for t in items)), autojunk=False)
            m = {}
            for a, b, size in sm.get_matching_blocks():
                for k in range(size):
                    m[a + k] = b + k
            for s, e, ruby in groups:
                idx = [m[k] for k in range(s, e) if k in m]
                note = ''
                if not idx:             # no matched base character: take the neighbours
                    before = [m[k] for k in range(s) if k in m][-1:]
                    after = [m[k] for k in range(e, len(flat)) if k in m][:1]
                    idx = before + after
                    note = 'approx'
                if not idx or r < 0.4:
                    rows.append(f'-\t{key}\t{c}\t{flat[s:e]}\t{ruby}\t\tnot located')
                    continue
                # the base with one neighbour above and below, across the column's width
                k0, k1 = max(min(idx) - 1, 0), min(max(idx) + 1, len(items) - 1)
                bx = [items[k][2] for k in range(k0, k1 + 1)]
                core = [items[k][2] for k in range(min(idx), max(idx) + 1)]
                w = sorted(b[2] for b in core)[len(core) // 2]
                xc = sum(b[0] + b[2] / 2 for b in core) / len(core)
                y0 = min(b[1] for b in bx)
                y1 = max(b[1] + b[3] for b in bx)
                box = (int(xc - 0.85 * w), int(y0 - 15), int(xc + 1.45 * w), int(y1 + 15))
                n += 1
                tiles.append(tile(scan.crop(box), f'#{n} {c}列' + (' ≈' if note else ''), flat[s:e], ruby))
                rows.append(f'{n}\t{key}\t{c}\t{flat[s:e]}\t{ruby}\t{",".join(map(str, box))}\t{note}')
        if tiles:
            save_sheet(tiles, OUT / f'{key}.jpg')
    # plate labels: the label crops already cut for reading, beside our text
    import yaml
    labels = yaml.safe_load((ROOT / 'text' / 'labels.yaml').read_text(encoding='utf-8'))
    tiles = []
    for name, val in labels.items():
        p = ROOT / 'work' / 'labels' / f'{name}.png'
        country = val[1]
        mm = re.match(r'(.*?)《(.*?)》', country)
        if not p.exists() or '《' not in country:
            continue
        base = re.sub(r'《[^》]*》|｜', '', country)
        ruby = '・'.join(re.findall(r'《([^》]*)》', country))
        n += 1
        tiles.append(tile(Image.open(p).convert('RGB'), f'#{n} {name}', base, ruby))
        rows.append(f'{n}\t{name}\tlabel\t{base}\t{ruby}\t\t')
    if tiles:
        save_sheet(tiles, OUT / 'labels.jpg')
    (OUT / 'list.tsv').write_text('\n'.join(rows) + '\n', encoding='utf-8')
    print('ruby tiles:', n, 'not located:', sum('not located' in r for r in rows))


if __name__ == '__main__':
    main()
