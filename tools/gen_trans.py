"""Translation pages of the trilingual edition (original + Chinese + English).

For every page with a translation (text/tr/<key>.yaml) two pages follow the original's text page:
the Chinese on a right page (side b), the English on a left page (side a), so each country has
the facsimile opening and then the translation opening.
  pages/tr_<key>_zh.tex, pages/tr_<key>_en.tex   TikZ overlays like the facsimile pages
  pages/list_tri_<vol>.tex, list_tri_spread_<vol>.tex
    python -I -X utf8 tools/gen_trans.py"""
import re
import sys
from pathlib import Path

import yaml
from fontTools.ttLib import TTFont

sys.path.insert(0, str(Path(__file__).parent))
from gen_pages import spread_listing  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
TR = ROOT / 'text' / 'tr'
OUT = ROOT / 'pages'
CONT = {'亜細亜': ('亚洲', 'Asia'), '歐邏巴': ('欧洲', 'Europe'), '亜弗利加': ('非洲', 'Africa'),
        '南亜墨利加': ('南美洲', 'South America'), '北亜墨利加': ('北美洲', 'North America')}
SC = TTFont(ROOT / 'fonts' / 'NotoSerifSC-Regular.ttf').getBestCmap()
SUNG = TTFont(ROOT / 'fonts' / 'TW-Sung.ttf').getBestCmap()

# text block of a translation page (mm)
TOP, BOTTOM, SPINE, FORE = 30.0, 28.0, 24.0, 26.0
W, H = 182.0, 251.0

# page key -> translation set after it instead of its own: the preface after its last page; the
# 跋 and the colophon (right pages) after the left page of their opening, so openings stay whole
AFTER = {'q005L': 'preface', 'q028L': 'q028R', 'k026L': 'k026R'}
# translations longer than a page: paragraph indices where a new opening starts (zh and en have
# the same paragraphs)
SPLIT = {'preface': [2, 4]}  # paragraphs: title+heaven | poles, zones + customs | continents + sources
LONG = {'zh': 800, 'en': 1800}     # characters (text + notes) above which a page is set tighter
BS = '\\'
MARKS = {'en': {'\x01': BS + 'trmark{', '\x02': '}', '\x03': BS + 'emph{', '\x04': '}',
                '〔': BS + 'trsmall{[', '〕': ']}'},
         'zh': {'\x01': BS + 'trmark{', '\x02': '}', '\x03': BS + 'emph{', '\x04': '}',
                '〔': BS + 'trsmall{〔', '〕': '〕}'}}
NEUTRAL = set(' 0123456789.,;:!?()[]\'"-/')


def esc(s):
    for a, b in ((BS, ''), ('&', BS + '&'), ('%', BS + '%'), ('#', BS + '#'), ('_', BS + '_')):
        s = s.replace(a, b)
    return s


def cjk_char(c):
    if ord(c) < 0x2E80 or ord(c) in SC:
        return c
    return '{' + BS + ('apxsung ' if ord(c) in SUNG else 'apxsungB ') + c + '}'


def script(c, lang):
    """'C' (CJK), 'L' (Latin) or None (neutral: space, digits, ASCII punctuation)."""
    if c in NEUTRAL:
        return None
    if c in '“”‘’—–…':
        return 'C' if lang == 'zh' else 'L'
    return 'C' if ord(c) >= 0x2E80 else 'L'


def inline(s, lang):
    """Markup -> TeX: [^n] note marks, *emphasis*, 〔small note〕; font runs: CJK inside English
    (trcjk), Latin and digits inside Chinese (trlat), fallback faces for characters Noto lacks."""
    s = esc(s)
    if lang == 'en':                          # straight double quotes -> curly (TeX makes both ”)
        s = re.sub(r'(^|[\s(\[〔—])"', lambda m: m.group(1) + '“', s)
        s = s.replace('"', '”')
    s = re.sub(r'\[\^(\d+)\]', lambda m: '\x01' + m.group(1) + '\x02', s)
    s = re.sub(r'\*([^*]+)\*', lambda m: '\x03' + m.group(1) + '\x04', s)
    out, run, cur = [], [], None

    def flush():
        nonlocal run, cur
        if run:
            t = ''.join(run)
            if lang == 'en' and cur == 'C':
                out.append('{' + BS + 'trcjk ' + ''.join(cjk_char(c) for c in t) + '}')
            elif lang == 'zh' and cur == 'L':
                out.append('{' + BS + 'trlat ' + t + '}')
            else:
                out.append(''.join(cjk_char(c) for c in t))
        run, cur = [], None

    for c in s:
        if c in MARKS[lang]:
            flush()
            out.append(MARKS[lang][c])
            continue
        k = script(c, lang)
        if lang == 'zh' and c in '0123456789':
            k = 'L'                          # digits in Chinese: the Latin face
        if k is None or cur is None or k == cur:
            run.append(c)
            cur = cur or k
        else:
            flush()
            run, cur = [c], k
    flush()
    return ''.join(out)


def page(key, lang, tr, label, side, part=None):
    """One translation page. part = (first, last) paragraph indices for a translation spread
    over several openings (SPLIT); its notes go with the paragraphs that cite them."""
    cont = label[0] if label else None
    c_zh, c_en = CONT.get(cont, ('', ''))
    head = tr[f'head_{lang}']
    paras = [p.strip() for p in tr[lang].strip().split('\n\n')]
    notes = list(enumerate(tr.get(f'notes_{lang}') or [], 1))
    if part:
        a, b = part
        if a:
            head += '（续）' if lang == 'zh' else ' (continued)'
        paras = paras[a:b]
        cited = {int(n) for p in paras for n in re.findall(r'\[\^(\d+)\]', p)}
        notes = [(n, t) for n, t in notes if n in cited]
    body = '\n\n'.join(inline(p, lang) for p in paras)
    size = sum(map(len, paras)) + sum(len(t) for _, t in notes)
    if size > LONG[lang]:                   # a long page: one step smaller type (preamble \trtight)
        body = BS + 'trtight\n' + body
    anchor = f'tr-{key}-{lang}' + (f'-{part[0]}' if part and part[0] else '')
    x0 = SPINE if side == 'b' else FORE
    wd, ht = W - SPINE - FORE, H - TOP - BOTTOM
    out = [f'% generated by tools/gen_trans.py ({key} {lang}) -- do not edit\n',
           BS + 'begin{tikzpicture}[remember picture,overlay,shift={(current page.south west)},xshift='
           + BS + 'edxshift]\n',
           f'{BS}node at ({W / 2:.1f}mm,{H - 2:.1f}mm) {{{BS}hypertarget{{{anchor}}}{{}}}};\n',
           f'{BS}node[anchor=north west,inner sep=0pt] at ({x0:.1f}mm,{H - TOP:.1f}mm) {{%\n',
           f'{BS}begin{{trpage}}{{{lang}}}{{{wd:.1f}mm}}{{{ht:.1f}mm}}\n',
           f'{BS}trhead{{{"tr-intro-" + lang if key == "intro" else "p-" + key}}}{{{inline(c_zh if lang == "zh" else c_en, lang)}}}{{{inline(head, lang)}}}\n',
           body + '\n']
    if notes:
        out.append(BS + 'trnotes\n')
        out += [f'{BS}trnote{{{n}}}{{{inline(t, lang)}}}\n' for n, t in notes]
    out.append(BS + 'end{trpage}};\n' + BS + 'end{tikzpicture}\n')
    return ''.join(out)


def main():
    cfg = yaml.safe_load((ROOT / 'text' / 'layout.yaml').read_text(encoding='utf-8'))
    labels = yaml.safe_load((ROOT / 'text' / 'labels.yaml').read_text(encoding='utf-8'))
    only = set(sys.argv[1:])               # keys: build lists with only these translations (samples)
    done = 0
    intro = TR / 'intro.yaml'              # editorial note, an opening after the title page (main.tex)
    if intro.exists():
        tr = yaml.safe_load(intro.read_text(encoding='utf-8'))
        for lang, side in (('zh', 'b'), ('en', 'a')):
            (OUT / f'tr_intro_{lang}.tex').write_text(page('intro', lang, tr, None, side), encoding='utf-8')
    for vol, pre in (('qian', 'q'), ('kun', 'k')):
        keys, sides = [], {}
        for key, info in cfg['pages'].items():
            if not key.startswith(pre):
                continue
            keys.append(key)
            sides[key] = info
            src = AFTER.get(key, key)
            f = TR / f'{src}.yaml'
            if (src == key and key in AFTER.values()) or not f.exists() or (only and src not in only):
                continue
            tr = yaml.safe_load(f.read_text(encoding='utf-8'))
            lab = labels.get(f'{vol}_{key[1:4]}') if src == key else None
            link = 'q004L' if src == 'preface' else src
            n = len(tr['zh'].strip().split('\n\n'))
            cuts = [0] + SPLIT.get(src, []) + [n]
            parts = list(zip(cuts, cuts[1:])) if src in SPLIT else [None]
            for i, part in enumerate(parts):
                for lang, side in (('zh', 'b'), ('en', 'a')):
                    name = f'tr_{src}_{lang}' + (f'_{i + 1}' if i else '')
                    (OUT / f'{name}.tex').write_text(page(link, lang, tr, lab, side, part), encoding='utf-8')
                    keys.append(name)
                    sides[name] = {'side': side}
            done += 1
        (OUT / f'list_tri_{vol}.tex').write_text(''.join(f'{BS}edpage{{{k}}}\n' for k in keys), encoding='utf-8')
        (OUT / f'list_tri_spread_{vol}.tex').write_text(spread_listing(keys, {'pages': sides}), encoding='utf-8')
    print(f'{done} translated pages')


if __name__ == '__main__':
    main()
