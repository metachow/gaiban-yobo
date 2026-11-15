"""Stitch IIIF strips (scans/strips/<vol>_<nnn>_<s>.png) into full openings and
make 1/4-size reading copies.  Usage: python -I tools/stitch.py ROOT"""
import os, sys
from PIL import Image

root = sys.argv[1]
urls = [l.split() for l in open(os.path.join(root, "scans/urls.txt"))]
groups = {}
for name, url, w, h in urls:
    key = name.rsplit("_", 1)[0]
    groups.setdefault(key, (int(w), int(h), []))[2].append((name, url))
os.makedirs(os.path.join(root, "scans/tsukuba"), exist_ok=True)
os.makedirs(os.path.join(root, "work/pages"), exist_ok=True)
for key, (w, h, parts) in groups.items():
    out = os.path.join(root, "scans/tsukuba", key + ".png")
    if not os.path.exists(out):
        img = Image.new("RGB", (w, h))
        for name, url in parts:
            x = int(url.split("/")[-4].split(",")[0])
            img.paste(Image.open(os.path.join(root, "scans/strips", name + ".png")).convert("RGB"), (x, 0))
        img.save(out, compress_level=1)
    else:
        img = Image.open(out)
    small = img.resize((w // 4, h // 4), Image.LANCZOS)
    small.save(os.path.join(root, "work/pages", key + ".jpg"), quality=88)
    print(key)
