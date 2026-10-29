"""Time a full analysis on a synthetic table of N rows (default one million).

    python scripts/perf_check.py            # 1,000,000 rows
    python scripts/perf_check.py --rows 250000

The data are random, drawn with a fixed seed, shaped like the funnel case: two groups, a
four-factor funnel and three segment dimensions. The point is the time and memory of the pipeline,
not the numbers it finds. Results depend on the machine; the README records one measured run.
"""

from __future__ import annotations

import argparse
import platform
import time

import numpy as np
import pandas as pd

import decisionpack
from decisionpack.run import run_analysis
from decisionpack.spec import parse_spec


def peak_mb() -> float | None:
    """Peak resident memory of this process in MB, or None if the platform gives no way to ask."""
    try:
        import resource  # Unix only

        raw = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return raw / 1e6 if platform.system() == "Darwin" else raw / 1024
    except ImportError:
        pass
    try:
        import ctypes
        from ctypes import wintypes

        class Counters(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD),
                ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]

        counters = Counters()
        counters.cb = ctypes.sizeof(Counters)
        kernel32, psapi = ctypes.windll.kernel32, ctypes.windll.psapi  # type: ignore[attr-defined]
        kernel32.GetCurrentProcess.restype = wintypes.HANDLE
        psapi.GetProcessMemoryInfo.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(Counters),
            wintypes.DWORD,
        ]
        ok = psapi.GetProcessMemoryInfo(
            kernel32.GetCurrentProcess(), ctypes.byref(counters), counters.cb
        )
        return counters.PeakWorkingSetSize / 1e6 if ok else None
    except (AttributeError, OSError):
        return None


def make_frame(n: int, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    group = rng.choice(["A", "B"], size=n)
    is_b = group == "B"
    impressions = rng.integers(200, 5000, size=n)
    ctr = np.where(is_b, 0.018, 0.024)
    clicks = rng.binomial(impressions, ctr)
    to_enquiry = np.where(is_b, 0.08, 0.25)
    enquiries = rng.binomial(clicks, to_enquiry)
    approved = rng.binomial(enquiries, 0.33)
    cpm = np.where(is_b, 0.27, 0.36)
    spent = impressions * cpm / 1000 * rng.uniform(0.8, 1.2, size=n)
    return pd.DataFrame(
        {
            "grp": group,
            "age": rng.choice(["18-24", "25-34", "35-44", "45-54", "55+"], size=n),
            "gender": rng.choice(["F", "M"], size=n),
            "interest": rng.integers(1, 41, size=n).astype(str),
            "impressions": impressions,
            "clicks": clicks,
            "enquiries": enquiries,
            "approved": approved,
            "spent": spent,
        }
    )


SPEC = {
    "title": "Performance check",
    "metric": {
        "name": "cost_per_approved",
        "label": "Cost per approved conversion",
        "numerator": "spent",
        "denominator": "approved",
        "unit": "$",
    },
    "groups": {"column": "grp", "baseline": "A", "comparison": "B"},
    "bridge": {
        "factors": [
            {"name": "cost_per_impression", "numerator": "spent", "denominator": "impressions"},
            {"name": "impressions_per_click", "numerator": "impressions", "denominator": "clicks"},
            {"name": "clicks_per_enquiry", "numerator": "clicks", "denominator": "enquiries"},
            {"name": "enquiries_per_approved", "numerator": "enquiries", "denominator": "approved"},
        ]
    },
    "segments": {
        "dimensions": ["age", "gender", "interest"],
        "numerator": "approved",
        "denominator": "clicks",
        "min_denominator": 1000,
        "simpson_stratifiers": ["age", "gender"],
    },
    "n_boot": 1000,
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=int, default=1_000_000)
    args = parser.parse_args()

    t0 = time.perf_counter()
    df = make_frame(args.rows)
    t_gen = time.perf_counter() - t0

    spec = parse_spec(SPEC)
    t0 = time.perf_counter()
    result = run_analysis(spec, df)
    t_run = time.perf_counter() - t0

    print(
        f"decisionpack {decisionpack.__version__}, Python {platform.python_version()}, "
        f"{platform.system()} {platform.machine()}, numpy {np.__version__}, "
        f"pandas {pd.__version__}"
    )
    print(
        f"rows: {args.rows:,}  (frame in memory: {df.memory_usage(deep=True).sum() / 1e6:.0f} MB)"
    )
    print(f"build table:   {t_gen:.1f} s")
    print(f"run_analysis:   {t_run:.1f} s")
    print(
        f"gap {result.gap:.2f}, 95% interval {result.gap_ci[0]:.2f} to {result.gap_ci[1]:.2f}, "
        f"{result.scan.family_size if result.scan else 0} segments compared"
    )
    peak = peak_mb()
    if peak is not None:
        print(f"peak memory:    {peak:.0f} MB")


if __name__ == "__main__":
    main()
