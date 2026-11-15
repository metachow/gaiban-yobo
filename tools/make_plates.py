"""Clean every figure page (right half of the openings) and record plate boxes and
label columns in work/plates.json.  python -I tools/make_plates.py [KEY ...]"""
import json
import sys
from multiprocessing import Pool
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import clean_plate  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
TONE = (246, 240, 226)
KEYS = [f'qian_{i:03d}' for i in range(7, 28)] + [f'kun_{i:03d}' for i in range(3, 26)]


def job(key):
    clean_plate.TONE = TONE
    try:
        return key, clean_plate.clean(key, 'R', str(ROOT / 'figures' / f'{key}.png'))
    except Exception as e:  # noqa
        print('FAILED', key, e, flush=True)
        return key, None


if __name__ == '__main__':
    keys = sys.argv[1:] or KEYS
    out = ROOT / 'work' / 'plates.json'
    data = json.loads(out.read_text()) if out.exists() else {}
    with Pool(3) as p:
        for key, info in p.imap_unordered(job, keys):
            if info:
                data[key] = info
                out.write_text(json.dumps(data, indent=1, sort_keys=True))
    print('done', len(data))
