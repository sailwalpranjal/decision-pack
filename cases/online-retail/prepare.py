"""Download and prepare the UCI Online Retail II dataset for the online-retail case.

    python cases/online-retail/prepare.py [--zip path/to/online+retail+ii.zip]

The raw file is a 45 MB Excel workbook with two sheets (about 1.07 million invoice lines), so it
is not committed. This script downloads it from UCI if you do not pass a copy, prints its SHA-256,
keeps only sales lines, adds the columns the spec needs, and writes
``cases/online-retail/data/sales_lines.csv`` (git-ignored). Reading the workbook takes a few
minutes; the parsed table is cached next to the zip as a pickle so a rerun is quick.

What it does to the data:

* A sales line has a positive quantity and price and is on an invoice that is not a cancellation
  (invoice numbers starting with "C" are cancellations).
* ``period`` is "Y1" for December 2009 to November 2010 and "Y2" for December 2010 to November
  2011, two full years. The data ends on 9 December 2011, so December 2011 is dropped as partial.
* ``new_invoice`` is 1 on the first line of each invoice, so ``sum(new_invoice)`` counts invoices.
* ``price_band`` and ``month_of_year`` are plain labels used as segment dimensions.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import urllib.request
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

URL = "https://archive.ics.uci.edu/static/public/502/online+retail+ii.zip"
HERE = Path(__file__).resolve().parent
DATA = HERE / "data"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch(zip_path: Path) -> None:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"downloading {URL} ...")
    with urllib.request.urlopen(URL) as resp, zip_path.open("wb") as out:
        while chunk := resp.read(1 << 20):
            out.write(chunk)


def load(zip_path: Path) -> pd.DataFrame:
    cache = zip_path.with_suffix(".pkl")
    if cache.exists():
        return pd.read_pickle(cache)
    with zipfile.ZipFile(zip_path) as z:
        name = next(n for n in z.namelist() if n.lower().endswith(".xlsx"))
        raw = z.read(name)
    sheets = pd.read_excel(io.BytesIO(raw), sheet_name=None, engine="openpyxl")
    frame = pd.concat(sheets.values(), ignore_index=True).rename(
        columns={"Customer ID": "CustomerID"}
    )
    frame.to_pickle(cache)
    return frame


def prepare(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    frame["Invoice"] = frame["Invoice"].astype(str)
    sales = frame[
        (frame["Quantity"] > 0) & (frame["Price"] > 0) & ~frame["Invoice"].str.startswith("C")
    ].copy()
    when = pd.to_datetime(sales["InvoiceDate"])
    month = when.dt.strftime("%Y-%m")
    sales["month_of_year"] = when.dt.strftime("%m")
    y1 = (month >= "2009-12") & (month <= "2010-11")
    y2 = (month >= "2010-12") & (month <= "2011-11")
    sales["period"] = np.select([y1, y2], ["Y1", "Y2"], default="")
    sales = sales[sales["period"] != ""].copy()
    sales["revenue"] = sales["Quantity"] * sales["Price"]
    sales["lines"] = 1
    sales["new_invoice"] = (~sales.duplicated("Invoice")).astype(int)
    sales["price_band"] = pd.cut(
        sales["Price"], [0, 1, 3, 10, np.inf], labels=["under 1", "1 to 3", "3 to 10", "10 or more"]
    ).astype(str)
    return sales[
        [
            "Invoice",
            "StockCode",
            "Quantity",
            "Price",
            "Country",
            "period",
            "month_of_year",
            "price_band",
            "revenue",
            "lines",
            "new_invoice",
        ]
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zip", type=Path, default=DATA / "online_retail_ii.zip")
    args = parser.parse_args()
    if not args.zip.exists():
        fetch(args.zip)
    print(f"sha256 {sha256(args.zip)}  {args.zip.name}")
    sales = prepare(load(args.zip))
    out = DATA / "sales_lines.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    sales.to_csv(out, index=False)
    print(
        f"wrote {out} with {len(sales):,} sales lines, {int(sales['new_invoice'].sum()):,} invoices"
    )


if __name__ == "__main__":
    main()
