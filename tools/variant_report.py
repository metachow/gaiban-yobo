"""Count every character of the transcription (main text, ruby excluded) and list the
variant forms: characters on the hand list below, or outside JIS X 0208 (cp932), with
counts and the pages they occur on. Writes work/variant_report.tsv.

The edition keeps the forms as written (the user's ruling: variants are listed in the
book's appendix, not normalised), so this report feeds the appendix table."""
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# variant -> standard form: text/variants.tsv (what the edition applies), plus forms
# reported only (not changed)
HAND = {
    '叓': '事', '攺': '改', '亜': '亞', '国': '國', '来': '來', '号': '號',
    '㗊': '器', '躰': '體', '万': '萬', '学': '學', '覚': '覺', '冨': '富', '嶋': '島',
    '舩': '船', '凢': '凡', '鉄': '鐵', '属': '屬', '寿': '壽', '戦': '戰', '强': '強',
    '矦': '侯', '挐': '拏', '說': '説', '徃': '往', '笠': '竺',
}


for _l in (ROOT / 'text' / 'variants.tsv').read_text(encoding='utf-8').splitlines():
    if _l and not _l.startswith('#'):
        _a, _b = _l.split('	')[:2]
        HAND[_a] = _b
APPLIED = {l.split('	')[0] for l in (ROOT / 'text' / 'variants.tsv').read_text(encoding='utf-8').splitlines()
           if l and not l.startswith('#')}


def text_chars(path):
    s = path.read_text(encoding='utf-8')
    lines = [l for l in s.splitlines() if l and not l.startswith('#')]
    body = '\n'.join(lines)
    body = re.sub(r'《[^》]*》', '', body)          # ruby
    return [c for c in body if c not in '｜〔〕|。、　\n^0123456789.']


def is_jis(c):
    try:
        c.encode('cp932')
        return True
    except UnicodeEncodeError:
        return False


def main():
    count, where = Counter(), defaultdict(set)
    files = sorted((ROOT / 'text').glob('*/*.txt'))
    for f in files:
        for c in text_chars(f):
            count[c] += 1
            where[c].add(f.stem)
    rows = []
    for c, n in count.most_common():
        if c in APPLIED:
            rows.append((c, HAND[c], n, 'applied'))
        elif c in HAND and HAND[c] != c:
            rows.append((c, HAND[c], n, 'list'))
        elif not is_jis(c):
            rows.append((c, '?', n, 'non-JIS'))
    out = ROOT / 'work' / 'variant_report.tsv'
    with open(out, 'w', encoding='utf-8') as fh:
        fh.write('variant\tstandard\tcount\twhy\tpages\n')
        for c, std, n, why in rows:
            fh.write(f'{c}\t{std}\t{n}\t{why}\t{" ".join(sorted(where[c]))}\n')
    # pairs where both forms occur (国/國, 来/來 ...)
    both = [(c, HAND[c], count[c], count[HAND[c]]) for c in HAND if count[c] and count[HAND[c]] and HAND[c] != c]
    print(f'{len(files)} files, {sum(count.values())} characters, {len(count)} distinct')
    print(f'{len(rows)} variant rows -> {out.relative_to(ROOT)}')
    print('both forms used:', '  '.join(f'{a}{n}/{b}{m}' for a, b, n, m in both))


if __name__ == '__main__':
    main()
