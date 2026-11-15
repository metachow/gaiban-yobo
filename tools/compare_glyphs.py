"""Comparison sheets for uncertain readings: the cut from our scan beside real examples of
each candidate character from the CODH 日本古典籍くずし字データセット (CC BY-SA 4.0,
books unpacked under work/codh/<id>/<id>/characters/U+XXXX/*.jpg).

    python -I tools/compare_glyphs.py      -> work/glyph/cmp_<id>.jpg for each entry below

Each row: one candidate, N examples spread over all unpacked books (deterministic sample)."""
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
CODH = ROOT / 'work' / 'codh'
GLYPH = ROOT / 'work' / 'glyph'
N = 10
CELL = 96
FONT = ImageFont.truetype(str(ROOT / 'fonts' / 'BIZ-UDMinchoM.ttc'), 30)

# spot id, cut file, what to decide, candidate characters
SPOTS2 = [   # round 2: single glyphs
    ('G1', 'G1.png', '第2頁1列 第1字', ['志', 'し', '去', '古', '尤']),
    ('G2', 'G2.png', '第2頁1列 第2字', ['て', 'こ', 'し', '之']),
    ('H1', 'H1.png', '第2頁1列「□帯」', ['正', '二', '三', '云', '此']),
    ('I1', 'I1.png', '第2頁2列 劣の下 1', ['れ', 'き', 'ゝ', 'る', 'た']),
    ('I2', 'I2.png', '第2頁2列 劣の下 2', ['り', 'し', 'ら', 'と']),
    ('I3', 'I3.png', '第2頁2列 劣の下 3', ['め', 'の', 'ゆ', 'と', 'る']),
    ('I4', 'I4.png', '第2頁2列 劣の下 4', ['し', 'と', 'り', 'ら']),
    ('K1', 'K1.png', '第3頁3列 殊の下 1', ['に', 'よ', 'ま']),
    ('K2', 'K2.png', '第3頁3列 殊の下 2', ['て', 'れ', 'ハ', 'に', 'ら']),
    ('K3', 'K3.png', '第3頁3列「爰」', ['爰', '更', '叓', '是']),
]
SPOTS3 = [
    ('M1', 'M1.png', '第2頁5列 依之の下', ['萬', '我', '其', '美', '夫']),
    ('N1', 'N1.png', '第2頁6列 無の下 1', ['之', 'き', 'に', 'そ', 'し']),
    ('N2', 'N2.png', '第2頁6列 無の下 2', ['ハ', 'は', 'に', 'ゝ']),
    ('N3', 'N3.png', '第2頁6列 第3字', ['非', '就', '況', '沈']),
    ('N4', 'N4.png', '第2頁6列 第4字', ['ず', 'す', '中', '乞', 'る']),
    ('N1b', 'N1.png', '第2頁6列 第1字', ['き', 'ゆ', 'む', 'ま', 'に']),
]
SPOTS4 = [
    ('P1', 'P1.png', '第2頁7列 齎の下', ['せ', 'き', 'し', 'さ']),
    ('Q2', 'Q2.png', '第2頁8列 意な の下 1', ['り', 'る', 'れ', 'め']),
    ('Q3', 'Q3.png', '第2頁8列 意な の下 2', ['べ', 'け', 'き', 'し']),
    ('R2', 'R2.png', '第2頁9列 叓と の下', ['ハ', 'に', 'よ', 'ゝ']),
    ('R5', 'R5.png', '第2頁9列 な の下', ['り', 'ま', 'き', 'け']),
    ('R7', 'R7.png', '第2頁9列 全の上', ['も', 'て', 'に', 'し']),
]
SPOTS = [
    ('A', 'A_天之主宰する.png', '第1頁2列「天之主宰する」', ['之', '地', '主', 'す', 'る']),
    ('B', 'B_是之.png', '第1頁4列「是之」', ['之', '也', 'な', 'り']),
    ('C', 'C_彼岸之又.png', '第1頁7列「彼岸之」', ['之', '也', 'な']),
    ('D', 'D_度なれども.png', '第1頁5列 度の下の仮名', ['な', 'れ', 'ど', 'も', 'あ']),
    ('E', 'E_指たるが.png', '第1頁6列 指の下の仮名', ['た', 'る', 'が', 'す']),
    ('F', 'F_之此る.png', '第1頁7列「冬至夏至之此る」', ['之', 'と', '此', 'な', 'る']),
    ('G', 'G_尤.png', '第2頁1列 首字', ['尤', '去', '大', '最']),
    ('H', 'H_正.png', '第2頁1列「正帯」', ['正', '二', '三']),
    ('I', 'I_劣れり.png', '第2頁2列「劣れり」', ['劣', 'れ', 'り', 'き', 'し']),
    ('J', 'J_者之.png', '第2頁2列「者之」', ['之', '也', 'な']),
    ('K', 'K_殊に爰に.png', '第3頁3列「殊に爰に」', ['爰', '更', 'に', 'よ', 'れ']),
    ('L', 'L_彼らの是.png', '第3頁1列「彼らの是」', ['是', '畧', 'ら', 'の']),
]


def examples(ch):
    code = f'U+{ord(ch):04X}'
    files = []
    for book in sorted(CODH.glob('*/*/characters')):
        files += sorted((book / code).glob('*.jpg'))
    random.Random(ch).shuffle(files)
    return files[:N], len(files)


def thumb(path, size):
    im = Image.open(path).convert('RGB')
    im.thumbnail((size, size))
    t = Image.new('RGB', (size, size), 'white')
    t.paste(im, ((size - im.width) // 2, (size - im.height) // 2))
    return t


def sheet(spot, cut, title, cands):
    src = Image.open(GLYPH / cut).convert('RGB')
    h = CELL * len(cands)
    s = h / src.height
    src = src.resize((max(1, int(src.width * s)), h))
    W = src.width + 20 + 46 + N * CELL
    out = Image.new('RGB', (W, h + 40), 'white')
    d = ImageDraw.Draw(out)
    d.text((6, 4), f'{spot}  {title}', fill=(160, 0, 0), font=ImageFont.truetype(str(ROOT / 'fonts' / 'BIZ-UDMinchoM.ttc'), 20))
    out.paste(src, (0, 40))
    x0 = src.width + 20
    for r, ch in enumerate(cands):
        files, total = examples(ch)
        y = 40 + r * CELL
        d.text((x0, y + 30), ch, fill=(0, 0, 0), font=FONT)
        d.text((x0, y + 70), str(total), fill=(120, 120, 120))
        for k, f in enumerate(files):
            out.paste(thumb(f, CELL - 4), (x0 + 46 + k * CELL, y + 2))
    out.save(GLYPH / f'cmp_{spot}.jpg', quality=90)


def main():
    books = sorted(CODH.glob('*/*/characters'))
    print('books:', ', '.join(b.parent.name for b in books))
    import sys
    todo = SPOTS4 if 'round4' in sys.argv else SPOTS3 if 'round3' in sys.argv else SPOTS2 if 'round2' in sys.argv else SPOTS
    for spot in todo:
        sheet(*spot)
    print('wrote', len(todo), 'sheets to work/glyph/cmp_*.jpg')


if __name__ == '__main__':
    main()
