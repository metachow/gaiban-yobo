"""Apply the ruby proofreading (work/review/ruby_*.tsv) to the transcription.

Each row: key, col, tile, ours, proposed, certainty, comment.  Rows marked 確実 or 推定 are
applied: `ours` must occur exactly once in that column (the col-th text line of
text/<vol>/<key>.txt) and is replaced by `proposed`; label rows (key qian_NNN / kun_NNN) edit
text/labels.yaml.  Rows marked 不明, rows already applied and rows that do not match are listed.
    python -I -X utf8 tools/apply_ruby_review.py [--dry]"""
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
dry = '--dry' in sys.argv
skipped, done, failed = [], [], []
files = {}

for tsv in sorted((ROOT / 'work' / 'review').glob('ruby_*.tsv')):
    with tsv.open(encoding='utf-8', newline='') as f:
        for r in csv.DictReader(f, delimiter='\t'):
            key, col, ours, prop, cert = r['key'], r['col'], r['ours'], r['proposed'], r['certainty']
            tag = f"{tsv.stem} {key} c{col} {r['tile']}: {ours} -> {prop}"
            if cert not in ('確実', '推定') or not prop or prop == ours:
                skipped.append(f'{tag} [{cert}]')
                continue
            if '_' in key:                                  # plate label
                p = ROOT / 'text' / 'labels.yaml'
                text = files.setdefault(p, p.read_text(encoding='utf-8'))
                lines = text.split('\n')
                idx = [i for i, l in enumerate(lines) if l.startswith(key + ':')]
                if not idx:
                    failed.append(f'{tag} (label not found)')
                    continue
                i = idx[0]
            else:
                p = ROOT / 'text' / ('qian' if key[0] == 'q' else 'kun') / f'{key}.txt'
                text = files.setdefault(p, p.read_text(encoding='utf-8'))
                lines = text.split('\n')
                body = [i for i, l in enumerate(lines) if l and not l.startswith('#')]
                try:
                    i = body[int(col) - 1]
                except (ValueError, IndexError):
                    failed.append(f'{tag} (no column {col})')
                    continue
            n = lines[i].count(ours)
            if n == 1:
                lines[i] = lines[i].replace(ours, prop)
                files[p] = '\n'.join(lines)
                done.append(tag)
            elif prop in lines[i]:
                skipped.append(f'{tag} [already applied]')
            else:
                failed.append(f'{tag} (found {n} times)')

if not dry:
    for p, t in files.items():
        p.write_text(t, encoding='utf-8')
print(f'applied {len(done)}, skipped {len(skipped)}, failed {len(failed)}' + (' (dry run)' if dry else ''))
for x in failed:
    print('FAIL', x)
for x in skipped:
    print('skip', x)
