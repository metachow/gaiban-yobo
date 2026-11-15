"""Build both volumes in both layouts:  python -I tools/build.py [qian|kun] [single|spread] [tri]
Regenerates pages and appendix first. Output: gaiban-yobo_<vol>_<layout>.pdf in the root;
with `tri` the trilingual edition gaiban-yobo_<vol>_zh-en_<layout>.pdf (translation pages from
text/tr/, tools/gen_trans.py)."""
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
vols = [a for a in sys.argv[1:] if a in ('qian', 'kun')] or ['qian', 'kun']
lays = [a for a in sys.argv[1:] if a in ('single', 'spread')] or ['single', 'spread']
tri = 'tri' in sys.argv[1:]

for tool in ('variant_report.py', 'gen_appendix.py', 'gen_pages.py') + (('gen_trans.py',) if tri else ()):
    subprocess.run([sys.executable, '-I', '-X', 'utf8', str(ROOT / 'tools' / tool)], cwd=ROOT, check=True,
                   stdout=subprocess.DEVNULL)
(ROOT / 'build').mkdir(exist_ok=True)
for v in vols:
    for l in lays:
        job = f'gaiban-yobo_{v}_zh-en_{l}' if tri else f'gaiban-yobo_{v}_{l}'
        cmd = ['xelatex', '-interaction=nonstopmode', '-output-directory=build', f'-jobname={job}',
               f'\\def\\edvol{{{v}}}\\def\\edlayout{{{l}}}' + ('\\def\\ededition{tri}' if tri else '')
               + '\\input{main}']
        for _ in range(2):          # remember picture needs two passes
            r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace')
        log = (ROOT / 'build' / f'{job}.log').read_text(encoding='utf-8', errors='replace')
        errs = [x for x in log.splitlines() if x.startswith('!')]
        miss = [x for x in log.splitlines() if 'Missing character' in x]
        shutil.copy(ROOT / 'build' / f'{job}.pdf', ROOT / f'{job}.pdf')
        pages = subprocess.run(['pdfinfo', str(ROOT / f'{job}.pdf')], capture_output=True).stdout.decode('utf-8', 'replace')
        n = next((x.split()[-1] for x in pages.splitlines() if x.startswith('Pages')), '?')
        print(f'{job}.pdf: {n} pages, {len(errs)} errors, {len(miss)} missing glyphs', *errs[:3], sep='\n  ' if errs else ' ')
