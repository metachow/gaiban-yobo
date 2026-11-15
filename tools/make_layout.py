"""Write text/layout.yaml: every page of both volumes in reading order, with plate boxes
(work/plates.json), label geometry (work/label_geom.json) and label texts (text/labels.yaml).
Pages are half-leaves; an opening = an ura (side b, right) + the next omote (side a, left).
The fixed part of the layout (geometry) is kept from the existing file."""
import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
W_ED = 182.0

# (key, kind, extra) in reading order. q = 乾 scans, k = 坤 scans; R/L = half of the opening.
def inventory():
    pages = [('q004R', 'blank', '前見返し'), ('q004L', 'text', '序'), ('q005R', 'text', '序'),
             ('q005L', 'text', '序'), ('q006R', 'map', None), ('q006L', 'map', None)]
    for i in range(7, 28):
        pages += [(f'q{i:03d}R', 'figure', None), (f'q{i:03d}L', 'text', None)]
    pages += [('q028R', 'text', '跋'), ('q028L', 'blank', None), ('q029R', 'blank', None),
              ('q029L', 'blank', '後見返し')]
    pages += [('k002R', 'blank', '前見返し'), ('k002L', 'text', '内題')]
    for i in range(3, 26):
        pages += [(f'k{i:03d}R', 'figure', None), (f'k{i:03d}L', 'text', None)]
    pages += [('k026R', 'text', '刊記'), ('k026L', 'text', '刊記'), ('k027R', 'blank', None),
              ('k027L', 'blank', '後見返し')]
    return pages


# per-page additions: preface in the 行書 style, column 1 where the scan has it
EXTRA = {
    'q004L': {'style': 'preface', 'first_col': 157.9},
    'q005R': {'style': 'preface', 'first_col': 167.5},
    'q005L': {'style': 'preface', 'first_col': 166.3},
    'k002L': {'style': 'naidai', 'first_col': 155.0},
    'q006L': {'style': 'maptext', 'first_col': 22.3},
}


COLOPHON = yaml.safe_load((ROOT / 'text' / 'colophon.yaml').read_text(encoding='utf-8'))
COLOPHON_W = {'k026R': 175.3, 'k026L': 168.7}     # scan page widths (measure_page)


def scan_name(key):
    return ('qian' if key[0] == 'q' else 'kun') + '_' + key[1:4]


def ruby_len(text):
    return len(re.sub(r'《[^》]*》|｜', '', text))


def label_entries(name, page_w, geom, texts):
    if name not in geom or name not in texts:
        return []
    region, country, *rest = texts[name]
    over = rest[0] if rest else {}          # per-label overrides (size, ruby, dx of the name column)
    dx = W_ED - page_w
    out = []
    g = geom[name]['region']
    n = ruby_len(region)
    pitch = over.get('region_pitch', (g[2] - g[1]) / n)
    out.append({'text': region, 'x': round(g[0] + dx + over.get('region_dx', 0), 1), 'y': g[1],
                'size': round(min(0.95 * pitch, 5.8), 2), 'pitch': round(pitch, 2)})
    g = geom[name]['name']
    n = ruby_len(country)
    pitch = (g[2] - g[1]) / n
    out.append({'text': country, 'x': round(g[0] + dx + over.get('dx', 0), 1), 'y': g[1],
                'size': over.get('size', round(min(0.92 * pitch, 9.0), 2)), 'pitch': round(pitch, 2),
                'ruby': over.get('ruby', 3.3)})
    return out


def main():
    path = ROOT / 'text' / 'layout.yaml'
    cfg = yaml.safe_load(path.read_text(encoding='utf-8'))
    plates = json.loads((ROOT / 'work' / 'plates.json').read_text())
    geom = json.loads((ROOT / 'work' / 'label_geom.json').read_text())
    texts = yaml.safe_load((ROOT / 'text' / 'labels.yaml').read_text(encoding='utf-8'))
    pages = {}
    for key, kind, note in inventory():
        side = 'b' if key.endswith('R') else 'a'
        vol = 'qian' if key[0] == 'q' else 'kun'
        p = {'kind': kind, 'side': side}
        if note:
            p['note'] = note
        if kind == 'text':
            p['text'] = f'{vol}/{key}.txt'
        if kind == 'figure':
            name = scan_name(key)
            pl = plates[name]
            dx = W_ED - pl['page_w']
            p['plate'] = {'file': f'figures/{name}.png', 'x': round(pl['x'] + dx, 1),
                          'y': round(pl['y'], 1), 'w': round(pl['w'], 1)}
            p['label'] = label_entries(name, pl['page_w'], geom, texts)
        if kind == 'map':
            mb = json.loads((ROOT / 'work' / 'map_boxes.json').read_text())[key[-1]]
            dx = W_ED - mb['page_w'] if side == 'b' else 0.0
            p['plate'] = {'file': f'figures/map_{key[-1]}.png', 'x': round(mb['x'] + dx, 1),
                          'y': round(mb['y'], 1), 'w': round(mb['w'], 1)}
            if side == 'a':
                p['text'] = f'{vol}/{key}.txt'
        if key in COLOPHON:          # free columns and seal images, as placed in the original
            dx = W_ED - COLOPHON_W[key] if side == 'b' else 0.0
            p['kind'] = 'free'
            p.pop('text', None)
            p['label'] = [dict(l, x=round(l['x'] + dx, 1)) for l in COLOPHON[key]['label']]
            p['images'] = [dict(i, x=round(i['x'] + dx, 1)) for i in COLOPHON[key].get('images', [])]
        p.update(EXTRA.get(key, {}))
        pages[key] = p
    cfg['pages'] = pages
    head = path.read_text(encoding='utf-8').split('\npages:')[0]
    body = yaml.safe_dump({'pages': pages}, allow_unicode=True, sort_keys=False, width=200)
    path.write_text(head + '\n' + body, encoding='utf-8')
    print(len(pages), 'pages')


if __name__ == '__main__':
    main()
