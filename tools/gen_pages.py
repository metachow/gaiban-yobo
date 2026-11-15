"""Generate one TikZ page per half-leaf from the transcription and text/layout.yaml.

usage: gen_pages.py [KEY ...]      (no keys: all pages + pages/list.tex, pages/list_spread.tex)

Transcription (text/<vol>/<key>.txt), one line per column, right to left:
  漢字《ルビ》     reading at the right of the run of kanji just before 《
  ｜一統《トウ》    ｜ marks where the ruby base starts (here: only 統 is wanted -> 一｜統《トウ》)
  〔右|左〕        double-line small note (割注); ruby allowed inside
  　              (full-width space) an empty cell
  ^N             at line start: the column starts N cells lower than the text top
  #              comment line
The original is written out by hand (no grid): characters are spaced along the column;
a column that is nearly full is justified to the full text height, a short one (end of
a paragraph) keeps the natural spacing.
"""
import re
import sys
from pathlib import Path

import yaml
from fontTools.ttLib import TTFont

sys.path.insert(0, str(Path(__file__).parent))
import jiaoji  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
TEXT = ROOT / 'text'
OUT = ROOT / 'pages'
PT = 72.27 / 25.4               # TeX pt per mm

KANA = set(chr(c) for c in range(0x30A0, 0x3100)) | set('ヽヾゝゞ〻')
SMALL_ADV = 0.80                # advance of a katakana relative to a kanji
KANA_SIZE = 0.90                # katakana in the text are written smaller than kanji
MARKS = {'。': 'circle', '、': 'tick'}

_CMAPS = {}
FONT_FILES = {'body': 'KleeOne-SemiBold.ttf', 'gyo': 'KouzanGyousho.ttf',
              'fallback': 'TW-Kai.ttf', 'fallbackB': 'TW-Kai-ExtB.ttf'}


def has(family, ch):
    if family not in _CMAPS:
        _CMAPS[family] = TTFont(ROOT / 'fonts' / FONT_FILES[family]).getBestCmap()
    return ord(ch) in _CMAPS[family]


def pick_family(family, ch):
    """The family, or the first fallback that has the character."""
    if family not in FONT_FILES:
        return family
    for f in (family, 'fallback', 'fallbackB'):
        if has(f, ch):
            return f
    print(f'warning: no font has {ch} (U+{ord(ch):04X})')
    return family


def load_variants():
    table = {}
    p = TEXT / 'variants.tsv'
    if p.exists():
        for line in p.read_text(encoding='utf-8').splitlines():
            if line.strip() and not line.startswith('#'):
                a, b, *_ = line.split('\t')
                table[a] = b
    return table


# ---------------------------------------------------------------- parsing
def is_kanji(ch):
    return not (ch in KANA or ch in '　|〔〕《》｜')


def parse_items(s):
    """-> list of items: ('c', ch, ruby or None, is_ruby_base_start) | ('e',) | ('n', right, left)
    Ruby is stored on the first character of its base, with the base length."""
    items = []
    i = 0
    mark = None          # index in items where an explicit ｜ base starts
    while i < len(s):
        ch = s[i]
        if ch == '｜':
            mark = len(items)
        elif ch == '《':
            j = s.index('》', i)
            ruby = s[i + 1:j]
            end = len(items)
            if mark is not None:
                start = mark
            else:
                start = end
                while start > 0 and items[start - 1][0] == 'c' and is_kanji(items[start - 1][1]) \
                        and items[start - 1][2] is None and not items[start - 1][3]:
                    start -= 1
            if start == end:
                raise ValueError(f'ruby 《{ruby}》 without a base')
            c = items[start]
            items[start] = ('c', c[1], (ruby, end - start), True)
            for k in range(start + 1, end):            # mark the rest of the base as taken
                d = items[k]
                items[k] = ('c', d[1], d[2], True) if d[2] is None else d
            mark = None
            i = j
        elif ch == '〔':
            j = s.index('〕', i)
            parts = s[i + 1:j].split('|')
            halves = [parse_items(p) for p in parts] + [[]]
            items.append(('n', halves[0], halves[1]))
            i = j
        elif ch == '　':
            items.append(('e',))
        elif ch in MARKS:          # a circle / tick at the lower right of the character before
            if not items or items[-1][0] != 'c':
                raise ValueError(f'mark {ch} without a character before it')
            items.append(('m', MARKS[ch]))
        elif ch in '》〕|':
            raise ValueError(f'stray {ch}')
        elif ch in ' \t':
            raise ValueError('ASCII space in text')
        else:
            items.append(('c', ch, None, False))
        i += 1
    return items


def parse_page(path):
    cols = []
    for n, raw in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
        line = raw.rstrip()
        if not line or line.startswith('#'):
            continue
        start = 0
        m = re.match(r'\^(\d+(?:\.\d+)?)', line)
        if m:
            start, line = float(m.group(1)), line[m.end():]
        try:
            cols.append((start, parse_items(line)))
        except ValueError as e:
            raise ValueError(f'{path.name} line {n}: {e}') from None
    return cols


# ---------------------------------------------------------------- drawing
def node(x, y, ch, family, size, variants, rotate=0):
    ch = variants.get(ch, ch)
    family = pick_family(family, ch)
    pt = size * PT
    rot = f',rotate={rotate}' if rotate else ''
    return (f'\\node[inner sep=0pt,anchor=center{rot}] at ({x:.2f}mm,{y:.2f}mm) '
            f'{{\\fontsize{{{pt:.2f}pt}}{{{pt:.2f}pt}}\\ed{family} {ch}}};\n')


MARK_ADV = 0.36      # a 。/、 takes a little room of its own below its character, as in the original


def mark(mx, my, kind, g):
    """Mark centred at (mx, my), drawn at the scale of glyph size g."""
    if kind == 'circle':
        return f'\\draw[line width={0.055*g:.2f}mm] ({mx:.2f}mm,{my:.2f}mm) circle ({0.105*g:.2f}mm);\n'
    return (f'\\draw[line width={0.08*g:.2f}mm,line cap=round] ({mx-0.06*g:.2f}mm,{my+0.08*g:.2f}mm)'
            f' -- ({mx+0.05*g:.2f}mm,{my-0.07*g:.2f}mm);\n')


def adv(it, note_scale):
    if it[0] == 'm':
        return MARK_ADV
    if it[0] == 'e':
        return 1.0
    if it[0] == 'n':
        return max(sum(adv(c, 1) for c in it[1]), sum(adv(c, 1) for c in it[2])) * note_scale
    return SMALL_ADV if it[1] in KANA else 1.0


def ruby_nodes(x, y_top, span, ruby, size, variants):
    """Reading centred beside a base running from y_top down over `span` mm."""
    pitch = max(size * 1.0, min(span / len(ruby), size * 1.25))
    total = pitch * len(ruby)
    y = y_top - (span - total) / 2 - pitch / 2
    out = ''
    for ch in ruby:
        out += node(x, y, ch, 'ruby', size, variants, rotate=-90 if ch == 'ー' else 0)
        y -= pitch
    return out


def render_text(key, info, lay, cols, variants, recs=None):
    """recs (optional list) receives, per column, the glyph boxes used for the 校記 anchors."""
    W, H = lay['paper']
    top = H - lay['top']
    height = lay['height']
    pitch_x = lay['col_pitch']
    unit = lay['unit']                       # natural advance of a kanji, mm
    g = lay['glyph']                         # body glyph size, mm
    rs = lay['ruby']                         # ruby glyph size, mm
    note_scale = lay.get('note_scale', 0.55)
    if info['side'] == 'a':                  # omote: left page, fore-edge left, spine right
        x1 = W - lay['spine_margin']
    else:                                    # ura: right page, fore-edge right
        x1 = W - lay['fore_margin']
    if 'first_col' in info:                  # column 1 centre, mm from the left edge
        x1 = info['first_col']
    fam = lay.get('font', 'body')
    out = []
    for c, (start, items) in enumerate(cols):
        x = x1 - c * pitch_x
        col_rec = []
        if recs is not None:
            recs.append(col_rec)
        nat = sum(adv(it, note_scale) for it in items) + start
        cap = height / unit
        if nat > cap * 1.04:
            print(f'warning: {key} column {c+1} runs over ({nat:.1f} > {cap:.1f} units)')
        scale = unit * (cap / nat if nat >= lay.get('justify', 0.85) * cap else 1.0)
        y = top - start * scale
        last = None
        for k, it in enumerate(items):
            a = adv(it, note_scale) * scale
            if it[0] == 'm':             # right of the character's foot, in the gap below it
                out.append(mark(last[0] + 0.16 * last[2], y - a / 2, it[1], last[2]))
                y -= a
                continue
            if it[0] == 'c':
                ch, ruby = it[1], it[2]
                rot = -90 if ch in 'ー' else 0
                gs = g * (KANA_SIZE if ch in KANA and ch not in 'ー' and fam == 'body' else 1.0)
                out.append(node(x, y - a / 2, ch, fam, gs,
                                variants, rot))
                last = (x, y - a / 2, g)
                col_rec.append(dict(ch=ch, xc=x, x0=x - g / 2, x1=x + g / 2 + rs * 1.1, y0=y - a, y1=y,
                                    ruby=ruby, note=False, stream=('m',)))
                if ruby:
                    text, n = ruby
                    # the base spans this and the next n-1 characters (marks do not count)
                    span, taken, j = a, 1, k + 1
                    while taken < n and j < len(items):
                        if items[j][0] != 'm':
                            span += adv(items[j], note_scale) * scale
                            taken += 1
                        j += 1
                    out.append(ruby_nodes(x + g / 2 + rs * 0.55, y, span, text, rs, variants))
            elif it[0] == 'n':
                # a reading on the left half-line sits between the two halves (as in the
                # original): open them up so it does not run into the right half
                wide = any(c[0] == 'c' and c[2] for c in it[2])
                for half, cells in ((0, it[1]), (1, it[2])):
                    hx = x + (0.26 if half == 0 else -0.26) * g * 1.25
                    if wide:
                        hx += 1.0 if half == 0 else -1.1
                    yy = y
                    for k, cell in enumerate(cells):
                        if cell[0] == 'm':
                            ma = MARK_ADV * note_scale * scale
                            out.append(mark(hx + 0.16 * g * note_scale, yy - ma / 2, cell[1], g * note_scale))
                            yy -= ma
                            continue
                        if cell[0] != 'c':
                            yy -= note_scale * scale
                            continue
                        ca = adv(cell, 1) * note_scale * scale
                        out.append(node(hx, yy - ca / 2, cell[1], 'body', g * note_scale, variants))
                        col_rec.append(dict(ch=cell[1], xc=hx, x0=hx - g * note_scale / 2,
                                            x1=hx + g * note_scale / 2 + (rs * 0.9 if cell[2] else 0),
                                            y0=yy - ca, y1=yy, ruby=cell[2], note=True, stream=(id(it), half)))
                        if cell[2]:
                            text, n = cell[2]
                            span = sum(adv(d, 1) * note_scale * scale for d in cells[k:k + n])
                            out.append(ruby_nodes(hx + g * note_scale / 2 + rs * (0.35 if half else 0.45), yy, span,
                                                  text, rs * 0.8, variants))
                        yy -= ca
            y -= a
    return out


def render_label(lab, H, variants, col_rec=None):
    """A free column of text (country label on a figure page): x = column centre,
    y = top of the first character, from the top-left of the page, in mm."""
    out = []
    items = parse_items(lab['text'])
    size, pitch = lab['size'], lab['pitch']
    x, y = lab['x'], H - lab['y']
    fam = lab.get('font', 'body')
    for k, it in enumerate(items):
        if it[0] == 'm':
            continue
        if it[0] != 'c':
            y -= pitch
            continue
        out.append(node(x, y - pitch / 2, it[1], fam, size, variants))
        if col_rec is not None:
            col_rec.append(dict(ch=it[1], xc=x, x0=x - size / 2, x1=x + size / 2 + (size * 0.5 if it[2] else 0),
                                y0=y - pitch, y1=y, ruby=it[2], note=False, stream=('m',)))
        if it[2]:
            text, n = it[2]
            rs = lab.get('ruby', size * 0.42)
            out.append(ruby_nodes(x + size / 2 + rs * 0.6, y, pitch * n, text, rs, variants))
        y -= pitch
    return out


def render(key, info, cfg, variants):
    lay = dict(cfg['layout'], **cfg.get('styles', {}).get(info.get('style'), {}))
    W, H = lay['paper']
    out = [f'% generated by tools/gen_pages.py ({key}) -- do not edit\n',
           '\\begin{tikzpicture}[remember picture,overlay,shift={(current page.south west)},'
           'xshift=\\edxshift]\n']
    p = info.get('plate')
    if p and 'x' in p and (ROOT / p['file']).exists():
        out.append(f'\\node[inner sep=0pt,anchor=north west] at ({p["x"]:.2f}mm,{H - p["y"]:.2f}mm) '
                   f'{{\\includegraphics[width={p["w"]:.2f}mm]{{{embed(p["file"])}}}}};\n')
    out.append(f'\\node at ({W / 2:.1f}mm,{H - 2:.1f}mm) {{\\hypertarget{{p-{key}}}{{}}}};\n')
    label_recs, text_recs = [], []
    for lab in info.get('label', []):
        label_recs.append([])
        out += render_label(lab, H, variants, label_recs[-1])
    for im in info.get('images', []):        # small cut-outs (seals): x, y = top-left, mm
        out.append(f'\\node[inner sep=0pt,anchor=north west] at ({im["x"]:.2f}mm,{H - im["y"]:.2f}mm) '
                   f'{{\\includegraphics[width={im["w"]:.2f}mm]{{{embed(im["file"])}}}}};\n')
    if info.get('text'):
        src = TEXT / info['text']
        if src.exists():
            out += render_text(key, info, lay, parse_page(src), variants, text_recs)
        else:
            MISSING.append(key)
    out += anchors(key, lay, text_recs, label_recs, variants)
    out.append('\\end{tikzpicture}\n')
    return ''.join(out)


MISSING = []
UNPLACED = []
JJ_PLACES = None


def _norm(s, variants):
    return ''.join(variants.get(c, c) for c in s if c not in '。、｜《》〔〕|　')


def _find(col, quote, variants, every, prefer_note):
    """Runs of glyph records in one column matching the quotation: the base text first, then the
    readings (a reading -> the base it belongs to)."""
    q = _norm(quote, variants)
    if not q:
        return []
    chars = ''.join((_norm(r['ch'], variants) or '?')[0] for r in col)
    hits, i = [], chars.find(q)
    while i >= 0:
        hits.append(col[i:i + len(q)])
        i = chars.find(q, i + 1)
    if not hits:
        for k, r in enumerate(col):
            if r['ruby'] and q in _norm(r['ruby'][0], variants):
                hits.append([d for d in col[k:] if d['stream'] == r['stream']][:r['ruby'][1]])
    if prefer_note and any(all(r['note'] for r in h) for h in hits):
        hits = [h for h in hits if all(r['note'] for r in h)]
    return hits if every else hits[:1]


def _link(box, dst):
    """An invisible link area over a run of glyphs, to the named destination dst."""
    x0, x1 = min(r['x0'] for r in box), max(r['x1'] for r in box)
    y0, y1 = min(r['y0'] for r in box), max(r['y1'] for r in box)
    h = (y1 - y0) / 2 * PT
    return (f'\\node[inner sep=0pt,anchor=base west] at ({x0:.2f}mm,{(y0 + y1) / 2:.2f}mm) '
            f'{{\\special{{pdf:ann width {(x1 - x0) * PT:.2f}pt height {h:.2f}pt depth {h:.2f}pt '
            f'<< /Type /Annot /Subtype /Link /Border [0 0 0] /A << /S /GoTo /D ({dst}) >> >>}}}};\n')


def anchors(key, lay, text_recs, label_recs, variants):
    """校記 anchors on this page: an invisible link over the characters an entry is about, the
    destination of the link back from the list there, and the entry's number at the foot of
    its column (under the label for a figure title), linking to the entry as well."""
    global JJ_PLACES
    if JJ_PLACES is None:
        JJ_PLACES = jiaoji.by_page(yaml.safe_load((TEXT / 'layout.yaml').read_text(encoding='utf-8')))
    W, H = lay['paper']
    foot = H - lay['top'] - lay['height'] - 4.0
    out, marks = [], {}                     # (x, y) of a number -> entries
    for p in JJ_PLACES.get(key, []):
        cols = text_recs if text_recs and not p['label'] else label_recs
        want = p['cols']
        if p['label'] or not want:          # a figure title: the label that has the quotation
            want = [i + 1 for i, c in enumerate(cols) if _find(c, p['quote'], variants, False, False)][:1]
        boxes, spans = [], {}
        if len(want) > 1 and not p['every'] and all(1 <= n <= len(cols) for n in want):
            joined = [dict(r, col=n) for n in want for r in cols[n - 1]]    # a word across columns
            hit = _find(joined, p['quote'], variants, False, p['note'])
            if hit:
                spans = {n: [[r for r in hit[0] if r['col'] == n]] for n in want}
        for n in want:
            if not 1 <= n <= len(cols) or not cols[n - 1]:
                UNPLACED.append(f'{key} #{p["num"]}: no column {n}')
                continue
            col = cols[n - 1]
            found = spans[n] if spans.get(n, [[]])[0] else _find(col, p['quote'], variants, p['every'], p['note'])
            if not found:
                UNPLACED.append(f'{key} #{p["num"]} col {n}: 「{p["quote"]}」 not found, whole column linked')
                found = [col]
            boxes += found
            main = [r for r in col if not r['note']] or col
            fx = main[0]['xc']
            fy = foot if cols is text_recs else col[-1]['y0'] - 3.0
            marks.setdefault((round(fx, 1), round(fy, 1)), []).append(p)
        if not boxes:
            UNPLACED.append(f'{key} #{p["num"]}: 「{p["quote"]}」 not placed, linked to the page top')
            out.append(f'\\node at ({W / 2:.1f}mm,{H - 2:.1f}mm) {{\\hypertarget{{{p["src"]}}}{{}}}};\n')
            continue
        top = max(boxes[0], key=lambda r: r['y1'])
        out.append(f'\\node at ({(top["x0"] + top["x1"]) / 2:.2f}mm,{top["y1"]:.2f}mm) '
                   f'{{\\hypertarget{{{p["src"]}}}{{}}}};\n')
        out += [_link(b, p['dst']) for b in boxes]
    for (fx, fy), ps in marks.items():
        for i, p in enumerate(ps):
            out.append(f'\\node[inner sep=0.4mm] at ({fx:.2f}mm,{fy - i * 3.2:.2f}mm) {{\\fontsize{{7pt}}{{7pt}}'
                       f'\\apxrm\\hyperlink{{{p["dst"]}}}{{\\textcolor{{linkcol}}{{{p["num"]}}}}}}};\n')
    return out


def embed(path):
    """figures/x.png -> figures/jpg/x.jpg when it exists (q92 copy: the PDF stays small)."""
    p = Path(path)
    j = p.parent / 'jpg' / (p.stem + '.jpg')
    return j.as_posix() if (ROOT / j).exists() else path


def spread_listing(keys, cfg):
    """Openings as in the scans: right half = ura (side b), left half = the next omote."""
    out, i = [], 0
    pages = cfg['pages']
    while i < len(keys):
        k = keys[i]
        if pages[k]['side'] == 'b' and i + 1 < len(keys) and pages[keys[i + 1]]['side'] == 'a':
            out.append(f'\\edspread{{{k}}}{{{keys[i + 1]}}}\n')
            i += 2
        elif pages[k]['side'] == 'b':
            out.append(f'\\edspread{{{k}}}{{}}\n')
            i += 1
        else:
            out.append(f'\\edspread{{}}{{{k}}}\n')
            i += 1
    return ''.join(out)


def main():
    cfg = yaml.safe_load((TEXT / 'layout.yaml').read_text(encoding='utf-8'))
    variants = load_variants()
    wanted = set(sys.argv[1:])
    OUT.mkdir(exist_ok=True)
    keys = list(cfg['pages'])
    for key in keys:
        if wanted and key not in wanted:
            continue
        (OUT / f'{key}.tex').write_text(render(key, cfg['pages'][key], cfg, variants), encoding='utf-8')
    if not wanted:      # one page list and one opening list per volume (乾 = q*, 坤 = k*)
        for vol, pre in (('qian', 'q'), ('kun', 'k')):
            vk = [k for k in keys if k.startswith(pre)]
            (OUT / f'list_{vol}.tex').write_text(''.join(f'\\edpage{{{k}}}\n' for k in vk), encoding='utf-8')
            (OUT / f'list_spread_{vol}.tex').write_text(spread_listing(vk, cfg), encoding='utf-8')
        for old in ('list.tex', 'list_spread.tex'):
            (OUT / old).unlink(missing_ok=True)
    print(f'{len(wanted) or len(keys)} pages' + (f'; not yet transcribed: {len(MISSING)}' if MISSING else ''))
    for u in UNPLACED:
        print('jiaoji:', u)


if __name__ == '__main__':
    main()
