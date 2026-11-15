"""Compile one page alone and put it beside the scan:  python -I tools/check_page.py q018L
-> work/check/q018L.jpg (scan left | edition right, same scale). Safe to run in parallel
(each page builds in build/check/<key>/). Prints generator warnings and TeX errors."""
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from measure_page import split_opening  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def main(key):
    r = subprocess.run([sys.executable, '-I', '-X', 'utf8', str(ROOT / 'tools' / 'gen_pages.py'), key],
                       cwd=ROOT, capture_output=True, text=True, encoding='utf-8')
    print((r.stdout + r.stderr).strip())
    if r.returncode:
        return
    d = ROOT / 'build' / 'check' / key
    d.mkdir(parents=True, exist_ok=True)
    (d / 'one.tex').write_text('\\documentclass{article}\n\\input{preamble}\n\\begin{document}\n'
                               f'\\edpage{{{key}}}\n\\end{{document}}\n', encoding='utf-8')
    for _ in range(2):
        t = subprocess.run(['xelatex', '-interaction=nonstopmode', f'-output-directory={d}', str(d / 'one.tex')],
                           cwd=ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace')
    errs = [l for l in t.stdout.splitlines() if l.startswith('!')]
    if errs:
        print('TeX errors:', *errs[:5], sep='\n  ')
    subprocess.run(['pdftoppm', '-r', '100', '-png', '-singlefile', str(d / 'one.pdf'), str(d / 'one')], check=True)
    ed = Image.open(d / 'one.png').convert('RGB')
    scan = ('qian' if key[0] == 'q' else 'kun') + '_' + key[1:4]
    im = Image.open(ROOT / 'scans' / 'tsukuba' / f'{scan}.png').convert('RGB')
    L, R = split_opening(np.asarray(im))
    pg = im.crop(L if key.endswith('L') else R)
    s = ed.height / pg.height
    pg = pg.resize((int(pg.width * s), ed.height), Image.LANCZOS)
    out = Image.new('RGB', (pg.width + ed.width + 20, ed.height), 'white')
    out.paste(pg, (0, 0))
    out.paste(ed, (pg.width + 20, 0))
    (ROOT / 'work' / 'check').mkdir(parents=True, exist_ok=True)
    out.save(ROOT / 'work' / 'check' / f'{key}.jpg', quality=88)
    print('wrote work/check/' + key + '.jpg')


if __name__ == '__main__':
    main(sys.argv[1])
