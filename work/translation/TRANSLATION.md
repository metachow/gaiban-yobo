# 外蕃容貌圖画: Chinese and English translation — guidelines

Edition: one volume per 冊, three languages. Each country takes two openings: the facsimile
opening (figure + original, as in the facsimile edition), then the translation opening
(Chinese on the right page, English on the left). Rulings by the user (2026-11-15):
modern written Chinese in simplified characters; English faithful and readable; light notes.

Further rulings (2026-11-15): the sample pages `text/tr/q007L.yaml` (大明) and `text/tr/k004L.yaml`
(都兒格) are approved — follow them for layout of the file, register, names and note density.
English title of the edition: *Illustrated Appearances of Foreign Peoples* (Gaiban yōbō zuga).
Research results on doubtful names are in the glossary notes (e.g. 唐東 → note "probably for 廣南
(Quảng Nam), perhaps by a slip for 廣東"; ミーコウ → Miechów; ハルカ as in 坤輿圖識, unidentified).
The book draws much of its text from 箕作省吾『坤輿圖識』(1845); you need not consult it.

## Source

- `work/translation/reading_<vol>.md`: the text of every page, columns joined, variants
  normalised. `漢字《よみ》` = the reading printed beside the characters (ruby); use it, it is how
  the author read the name or word. `〔右／左〕` = a two-line small note (割注) in the original.
  Katakana between 。…。 are foreign names (the original marks them that way).
- The facsimile and its 校記 (`text/jiaoji.yaml`) are the authority; ask if the reading text looks
  wrong. Translate the text **as written** — errors of fact or of writing are translated, and
  corrected in a note (e.g. 天笠 → 天竺, 多勒多 with the reading マトリタ).
- `work/translation/GLOSSARY.tsv`: every proper name, its reading, how to write it in Chinese
  (`zh_form`, `zh_modern`) and English (`en`, `romanized`), with a confidence (確 / 推 / 疑).
  Use it; report names that are missing or that you would identify differently.

## Output

One file per page: `text/tr/<key>.yaml` (key as in the reading text: q007L, k004L …).

```yaml
head_zh: 都儿格（土耳其）       # country as on the figure label: original form + modern name
head_en: Toruko (Turkey)
zh: |
  正文，一段或数段。注号写 [^1]。割注照原文位置写作〔…〕。
en: |
  Text, one or more paragraphs. Note markers [^1]. Small notes as 〔…〕 where the original has them.
notes_zh:
  - 注 1 的内容。
notes_en:
  - Content of note 1.
```

Chinese and English carry the same notes with the same numbers.

## Names

- **First mention on a page: the original form, then the modern name in brackets; afterwards the
  modern name.** Chinese: kanji names in simplified form (`zh_form`) — 都儿格（土耳其）, later 土耳其;
  katakana names stay katakana — セーヘンベルケン（特兰西瓦尼亚）. English: the romanized reading
  (Hepburn of the kana as written, ー as a macron, ヲ o, ヱ e, ヂ ji) — Toruko (Turkey), later
  Turkey; Sēhenberuken (Transylvania).
- kind `P` in the glossary (continents, seas, China, Korea, eras, ordinary historical terms) are
  translated as ordinary words, no bracket. 支那 stays 支那 in Chinese (historical term; the 凡例
  says so) and is "Shina" in English at first mention, "China" after it.
- Japanese eras: keep the era, give the Western year in a note the first time on a page
  (正保 → 1644–1648). 我皇國 = 我皇国 / "our Imperial Land".
- Unidentified names (`疑`): original form only, and say in a note that it is not identified.

## Fixed formulas

- 北極地ヲ出ル事 N 度ヨリ M 度ニ至ル (on almost every page) = the elevation of the pole, i.e. the
  latitude: 北极出地 N 度至 M 度 / "The pole stands N to M degrees above the horizon." (The 凡例
  explains it once.) 南極ヲ見ル事 … = 南极出地… / "The south pole stands …".
- 此國北ハ…ニ界シ東ハ…ニ隣リ… = 此国北以…为界，东邻…… / "The country borders on … to the north,
  adjoins … to the east …" — keep the order of the directions.
- 人物 (the people's character) / 氣候 / 産物: as in the original, without headings.

## Register

- Chinese: plain modern written Chinese (书面语), not colloquial, not classical; close to the
  sentence order of the original where natural. Full-width Chinese punctuation; numbers in Chinese
  numerals as in the original (三十五度), Arabic numerals only for Western years in notes.
- English: faithful and readable; one English sentence per original sentence where possible; no
  added explanations in the text (they go in notes). Japanese words kept as words (*kara*) in
  italics with `*…*`.
- The author's judgements about peoples (賤シク, 愚昧, 野鄙 …) are translated as written,
  without softening and without comment, except where a note is needed to identify a fact. The
  凡例 states that the book reflects the views of its time.

## Notes (light)

Only: identification of a name or term not clear from the bracket; an obvious error of fact or a
legend (the Amazons, the Patagonian giants); a date conversion; a textual point that matters for
the meaning (cite the 校記). One or two sentences each. No literature survey.

## Not to do

- Do not copy or paraphrase a published translation.
- Do not add headings, paragraph divisions beyond one or two, or modern punctuation inside quoted
  original words.

Ruling (2026-11-15): the volumes are called Ken and Kon in English, after the original's ruby 乾《ケン》/坤《コン》;
first mention on a page glossed (Heaven) / (Earth). Chinese keeps 乾、坤.
Ruling (2026-11-15): in Chinese notes that discuss the characters of the original (原文作…, …之误, 字形), quote the
original in its own (traditional) forms — 唐東 / 廣南 / 廣東 — so that the shapes can be compared; the running
translation stays simplified.
