"""Download all page images of the two Tsukuba items at full resolution.

IIIF server limits maxArea to 10 Mpx, so each 5616x3744 opening is fetched in
vertical strips and stitched.  Usage: python -I fetch_iiif.py OUTDIR
"""
import json, os, ssl, sys, time, urllib.request, io
from PIL import Image

ITEMS = {"qian": 4771317, "kun": 4771348}
UA = {"User-Agent": "Mozilla/5.0"}
ctx = ssl.create_default_context()


def get(url):
    for k in range(4):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=120, context=ctx) as r:
                return r.read()
        except Exception as e:  # noqa
            print("  retry", k, e)
            time.sleep(3)
    raise RuntimeError(url)


def main(out):
    os.makedirs(out, exist_ok=True)
    for vol, iid in ITEMS.items():
        item = json.loads(get(f"https://dc.tulips.tsukuba.ac.jp/api/items/{iid}"))
        for n, m in enumerate(item["o:media"], 1):
            fn = os.path.join(out, f"{vol}_{n:03d}.png")
            if os.path.exists(fn):
                continue
            media = json.loads(get(m["@id"]))
            svc = media["data"]["id"]
            w, h = media["data"]["width"], media["data"]["height"]
            maxa = media["data"].get("maxArea", 10_000_000)
            strips = 1
            while (w / strips) * h > maxa:
                strips += 1
            sw = -(-w // strips)
            img = Image.new("RGB", (w, h))
            for s in range(strips):
                x = s * sw
                ww = min(sw, w - x)
                data = get(f"{svc}/{x},0,{ww},{h}/max/0/default.png")
                img.paste(Image.open(io.BytesIO(data)).convert("RGB"), (x, 0))
            img.save(fn)
            print(vol, n, w, h, strips)


if __name__ == "__main__":
    main(sys.argv[1])
