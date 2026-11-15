"""Erase the printed note left of the world map's ring on figures/map_L.png (it is set as
text instead): fit the ring's outer edge x(y) robustly and paint everything left of it."""
import numpy as np
from PIL import Image

TONE = np.array([246, 240, 226], np.uint8)
a = np.asarray(Image.open('figures/map_L.png').convert('RGB')).copy()
H, W, _ = a.shape
ai = a.astype(int)
yel = (ai[..., 0] > 200) & (ai[..., 1] > 190) & (ai[..., 2] < 170)
ys, xs = [], []
for y in range(H):
    x = np.where(yel[y, 250:])[0]
    if len(x):
        ys.append(y)
        xs.append(x.min() + 250)
ys, xs = np.array(ys), np.array(xs)
m = np.ones(len(ys), bool)
for _ in range(4):
    p = np.polyfit(ys[m], xs[m], 4)
    m = np.abs(xs - np.polyval(p, ys)) < 12
y0, y1 = ys[m].min(), ys[m].max()
for y in range(H):
    l = int(np.polyval(p, min(max(y, y0), y1))) - 6
    a[y, :min(max(l, 0), W // 2)] = TONE
Image.fromarray(a).save('figures/map_L.png')
print('ring rows', m.sum(), 'of', len(m))
