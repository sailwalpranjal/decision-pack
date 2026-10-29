"""Download the funnel lab ad dataset and check it against a known checksum.

    python cases/funnel-lab/prepare.py

The file is the Kaggle dataset "Sales Conversion Optimization" (1,143 ad sets, three campaigns).
Kaggle lists its licence as "Other (specified in description)" and the description states no
terms, so this repository does not redistribute it. The script fetches a public mirror and
refuses to keep anything whose SHA-256 differs from the file I analysed.
"""

from __future__ import annotations

import hashlib
import urllib.request
from pathlib import Path

URL = "https://raw.githubusercontent.com/ychennay/ychennay.github.io/master/KAG_conversion_data.csv"
SHA256 = "2ee88488b5229562e8814b08e95e09e675aa939f69fc16f124eefe2bfdfa7cf8"
SIZE = 60522
OUT = Path(__file__).resolve().parent / "data" / "KAG_conversion_data.csv"


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    print(f"downloading {URL}")
    with urllib.request.urlopen(URL, timeout=60) as resp:  # noqa: S310
        data = resp.read()
    digest = hashlib.sha256(data).hexdigest()
    if digest != SHA256:
        raise SystemExit(f"checksum mismatch: got {digest}, expected {SHA256}; nothing written")
    OUT.write_bytes(data)
    print(f"wrote {OUT} ({len(data):,} bytes, sha256 {digest})")
    if len(data) != SIZE:
        print(f"note: expected {SIZE:,} bytes")


if __name__ == "__main__":
    main()
