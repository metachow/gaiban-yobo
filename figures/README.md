# figures/ (not in the repository)

Everything here is derived from the University of Tsukuba Library scans and is regenerated, not
committed (the images are under the library's conditions, NoC-CR; see the main README).

1. Scans: `python -I tools/fetch_iiif.py scans/tsukuba` (items 4771317 乾, 4771348 坤; full-resolution
   openings, fetched in strips because of the IIIF size limit).
2. Plates and the world map: `python -I tools/make_plates.py` — paper tone (246,240,226), fixed black
   point + gamma + fibre fade + mild unsharp mask; printed labels removed by the per-page boxes in
   `text/label_fix.yaml` (`tools/label_boxes.py`). JPEG copies for the PDF go to `figures/jpg/`
   (the PDF embeds those when present; refresh them after changing a PNG).
3. Covers: `python -I tools/make_covers.py` — seeded paper textures `cover_paper.jpg`, `slip_paper.jpg`
   and the 題簽 title ink `slip_ink_<vol>.png` cut from the cover scans.
4. Colophon seals (坤 scan 026, right page; boxes in mm from the page's top-left):
   `python -I tools/cut_seal.py kun_026 R 63.3 213.8 82.3 234.8 figures/seal_kun026_a.png` (square)
   `python -I tools/cut_seal.py kun_026 R 83.0 213.3 104.4 234.9 figures/seal_kun026_b.png` (round)
