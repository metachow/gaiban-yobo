"""Compare our transcription with KuroNet OCR, column by column.

Input: work/kuronet/<key>.txt  -- KuroNet columns, one per line (right to left), as exported
       from the dashboard (characters sorted top to bottom per column).
Output: work/kuronet_diff.md     -- per page, the columns that differ, with the differing
                                     stretches marked, after normalising forms both sides write
                                     differently (KuroNet gives modern forms: 国/國, 万/萬 ...).
Ruby and 割注 structure are flattened on our side (ruby dropped, notes inlined); KuroNet reads
the ruby too, usually as a separate thin column, which is dropped by the column matcher."""
import difflib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# both sides -> one form, so only real disagreements remain
NORM = {}
for pair in ['國国', '萬万', '叓事', '㕝事', '攺改', '亞亜', '號号', '來来', '學学', '覺覚', '戰戦', '徃往', '强強',
             '矦侯', '舩船', '圖図', '畫画', '與与', '獨独', '豐豊', '廣広', '數数', '屬属', '總総', '從従', '氣気',
             '譯訳', '佛仏', '兒児', '爲為', '當当', '實実', '舊旧', '變変', '盡尽', '繼継', '續続', '禮礼', '樂楽',
             '團団', '轉転', '假仮', '濕湿', '辨弁', '歸帰', '應応', '縣県', '區区', '邊辺', '晝昼', '處処', '賣売',
             '讀読', '聲声', '壽寿', '對対', '醫医', '爭争', '黑黒', '齊斉', '彌弥', '稱称', '嶋島', '冨富', '躰体',
             '鐵鉄', '壯壮', '淺浅', '澤沢', '濱浜', '關関', '劍剣', '惡悪', '惠恵', '戀恋', '收収', '寢寝', '將将',
             '纔才', '蠻蛮', '鬪闘', '險険', '顯顕', '殘残', '靈霊', '雜雑', '雙双', '瀧滝', '燈灯', '蟲虫', '證証',
             '傳伝', '擧挙', '絲糸', '條条', '價価', '儉倹', '凾函', '剩剰', '勞労', '勳勲', '卽即', '參参', '嚴厳',
             '圍囲', '壞壊', '奧奥', '孃嬢', '寳宝', '寶宝', '巖岩', '巢巣', '帶帯', '廢廃', '彈弾', '徑径', '恆恒',
             '戲戯', '拂払', '擔担', '據拠', '攝摂', '敎教', '晉晋', '棧桟', '榮栄', '樣様', '檢検', '歡歓', '歷歴',
             '殼殻', '澁渋', '溫温', '滿満', '濟済', '灣湾', '爐炉', '犧犠', '狀状', '猪豬', '獸獣', '產産', '畫画',
             '盜盗', '眞真', '硏研', '禪禅', '穀穀', '稻稲', '窗窓', '粹粋', '經経', '綠緑', '縱縦', '纖繊', '聽聴',
             '肅粛', '臟臓', '與与', '艷艶', '莊荘', '萠萌', '藏蔵', '藝芸', '虛虚', '螢蛍', '衞衛', '褱懐', '覽覧',
             '觀観', '譽誉', '豫予', '賴頼', '贊賛', '軍軍', '輕軽', '辭辞', '遙遥', '遲遅', '醉酔', '釋釈', '錢銭',
             '鑛鉱', '閱閲', '隱隠', '隨随', '靜静', '響響', '頭頭', '顏顔', '驗験', '髮髪', '鷄鶏', '麥麦', '黃黄',
             '默黙', '齒歯', '龍竜', '龜亀', '豊豊', '笠竺']:
    NORM[pair[0]] = pair[1]
# KuroNet's usual katakana/kanji look-alikes: compare them as one class
for group in ['二ニに', '卜トと', '八ハは', '夕タた', '几ルる', '十ナな', '力カか', '口ロろ', '工エえ', '三ミみ',
              '千チち', '子ネね', '也セせ', '乙', 'ヽゝ', 'ヾゞ', '々〻']:
    for c in group[1:]:
        NORM[c] = group[0]
for code in range(0x30A1, 0x30F7):          # remaining katakana -> hiragana
    k = chr(code)
    if k not in NORM:
        NORM[k] = chr(code - 0x60)


def norm(s):
    return ''.join(NORM.get(c, c) for c in s)


def our_columns(path):
    cols = []
    for line in path.read_text(encoding='utf-8').splitlines():
        if not line or line.startswith('#'):
            continue
        line = re.sub(r'^\^\d+(\.\d+)?', '', line)
        line = re.sub(r'《[^》]*》', '', line)          # ruby
        line = re.sub(r'[｜〔〕|。、　]', '', line)
        cols.append(line)
    return cols


def kn_columns(path):
    return [l.split(' ', 1)[1] if ' ' in l else '' for l in path.read_text(encoding='utf-8').splitlines() if l.strip()]


def best_match(ours, kns):
    """For each of our columns, the KuroNet column (or two adjacent ones joined) that matches
    best; KuroNet splits ruby into extra thin columns, so short unmatched ones are ignored."""
    out = []
    for o in ours:
        no = norm(o)
        best = (0, '')
        for i in range(len(kns)):
            for j in (i, i + 1):
                if j >= len(kns):
                    continue
                cand = ''.join(kns[i:j + 1])
                r = difflib.SequenceMatcher(None, no, norm(cand)).ratio()
                if r > best[0]:
                    best = (r, cand)
        out.append(best)
    return out


def mark(o, k):
    sm = difflib.SequenceMatcher(None, norm(o), norm(k))
    a, b = [], []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal':
            a.append(o[i1:i2])
            b.append(k[j1:j2])
        else:
            a.append(f'【{o[i1:i2]}】')
            b.append(f'【{k[j1:j2]}】')
    return ''.join(a), ''.join(b), sum(1 for t in sm.get_opcodes() if t[0] != 'equal')


def main():
    lines = ['# KuroNet 照合\n', '各列：上＝本書の録文（振り仮名を除く），下＝KuroNet。【】が食い違い。'
             '字体差（國/国 など）とカタカナ・ひらがなの差は無視。\n']
    total = 0
    for kp in sorted((ROOT / 'work' / 'kuronet').glob('*.txt')):
        key = kp.stem
        vol = 'qian' if key[0] == 'q' else 'kun'
        tp = ROOT / 'text' / vol / f'{key}.txt'
        if not tp.exists():
            continue
        ours, kns = our_columns(tp), kn_columns(kp)
        page = []
        for c, (o, (r, k)) in enumerate(zip(ours, best_match(ours, kns)), 1):
            a, b, n = mark(o, k)
            if n:
                page.append(f'- 第{c}列 ({r:.2f})\n  - 本書　{a}\n  - KN　　{b}')
                total += n
        if page:
            lines.append(f'\n## {key}\n' + '\n'.join(page))
    (ROOT / 'work' / 'kuronet_diff.md').write_text('\n'.join(lines), encoding='utf-8')
    print('differences:', total, '-> work/kuronet_diff.md')


if __name__ == '__main__':
    main()
