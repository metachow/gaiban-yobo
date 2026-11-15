"""Download KuroNet results (public curation JSON) listed in work/kuronet_tasks.txt
(<key>:<task id>) and write work/kuronet/<key>.json and <key>.txt (columns, right to left:
"<x> <characters top to bottom>"). Characters closer than 55 px in x form one column; thin
ruby columns come out as separate short columns."""
import json
import ssl
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'work' / 'kuronet'
OUT.mkdir(parents=True, exist_ok=True)
ctx = ssl.create_default_context()


def columns(cur):
    a = []
    for e in cur['selections'][0]['members']:
        x, y, w, h = map(int, e['@id'].split('xywh=')[1].split(','))
        a.append((x + w / 2, y + h / 2, w, e['metadata'][0]['value'][0]['resource']['marker']['text']))
    a.sort(key=lambda t: -t[0])
    cols = []
    for c in a:
        if cols and abs(cols[-1]['x'] - c[0]) < 55:
            cols[-1]['items'].append(c)
            n = len(cols[-1]['items'])
            cols[-1]['x'] = (cols[-1]['x'] * (n - 1) + c[0]) / n
        else:
            cols.append({'x': c[0], 'items': [c]})
    return [f"{round(c['x'])} " + ''.join(t[3] for t in sorted(c['items'], key=lambda t: t[1])) for c in cols]


for line in (ROOT / 'work' / 'kuronet_tasks.txt').read_text().split():
    key, tid = line.split(':')
    url = f'https://mp.ex.nii.ac.jp/api/kuronet/curation/{tid}'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    cur = json.loads(urllib.request.urlopen(req, timeout=60, context=ctx).read())
    (OUT / f'{key}.json').write_text(json.dumps(cur, ensure_ascii=False), encoding='utf-8')
    (OUT / f'{key}.txt').write_text('\n'.join(columns(cur)) + '\n', encoding='utf-8')
    print(key, len(cur['selections'][0]['members']))
