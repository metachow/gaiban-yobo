"""校記 entries, shared by gen_appendix.py (the list) and gen_pages.py (the anchors in the text).

Each entry of a page is numbered 1, 2, … in the order of text/jiaoji.yaml (or of the `# 校:` /
`# ?` comments of a transcription file not in jiaoji.yaml).  Link names:
  jj-<key>-<n>     the entry in the 校記 list
  jjsrc-<key>-<n>  the place in the text it is about
The place is read from the entry itself: 第N列 (or 第N・M列), the first 「…」 quotation, and the
words 割注 (prefer the small note), 三箇所 etc. (every occurrence), 図の標題 (the country label
on the facing figure page)."""
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
_JJ = ROOT / 'text' / 'jiaoji.yaml'
JJ = (yaml.safe_load(_JJ.read_text(encoding='utf-8')) or {}) if _JJ.exists() else {}
KANJI_NUM = {'二': 2, '三': 3, '四': 4, '五': 5}


def items(key, src=None):
    """The entries of one page as display strings ('校　…'), in order."""
    if key in JJ:
        return [n.replace('：', '　', 1) if n[:2] in ('校：', '？：', '注：') else n for n in JJ[key]]
    if not src or not src.exists():
        return []
    out = []
    for l in src.read_text(encoding='utf-8').splitlines():
        m = re.match(r'#\s*(\?|校:)\s*(.*)', l)
        if m:
            out.append(('校' if m.group(1) == '校:' else '？') + '　' + m.group(2).strip())
    return out


def place(key, n, text):
    """Where entry n of page `key` points: dict(page, cols, quote, note, every, label)."""
    m = re.search(r'第([\d・]+)列', text)
    label = '図の標題' in text and not m      # 「…（本文・図の標題も同じ）」 stays in the text
    cols = [int(c) for c in m.group(1).split('・')] if m else []
    q = re.search(r'「([^」]*)」', text[m.end():] if m else text[text.find('図の標題') + 1:])
    return dict(page=key[:-1] + 'R' if label else key, cols=cols,
                quote=q.group(1) if q else '', note='割注' in text[:m.end() + 8] if m else False,
                every=bool(re.search(r'[二三四五]箇所|いずれも', text)), label=label,
                src=f'jjsrc-{key}-{n}', dst=f'jj-{key}-{n}', num=n)


def by_page(cfg):
    """page key -> list of places to anchor on that page (a 図の標題 entry goes to the plate)."""
    out = {}
    for key, info in cfg['pages'].items():
        src = ROOT / 'text' / info['text'] if info.get('text') else None
        for n, t in enumerate(items(key, src), 1):
            p = place(key, n, t)
            out.setdefault(p['page'], []).append(p)
    return out
