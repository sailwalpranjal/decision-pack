from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
FUNNEL_CSV = ROOT / "cases" / "funnel-lab" / "data" / "KAG_conversion_data.csv"
SHOPPERS_CSV = ROOT / "cases" / "online-shoppers" / "data" / "online_shoppers_intention.csv"


FUNNEL_MISSING = not FUNNEL_CSV.exists()
NEEDS_FUNNEL = {"test_api.py", "test_report.py", "test_spec_and_run.py"}


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """The Kaggle ad file is not committed (no stated licence). Skip what needs it if absent."""
    if not FUNNEL_MISSING:
        return
    skip = pytest.mark.skip(reason="run cases/funnel-lab/prepare.py to fetch the ad dataset")
    for item in items:
        if item.path.name in NEEDS_FUNNEL:
            item.add_marker(skip)


@pytest.fixture(scope="session")
def funnel_df() -> pd.DataFrame:
    if FUNNEL_MISSING:
        pytest.skip("run cases/funnel-lab/prepare.py to fetch the ad dataset")
    df = pd.read_csv(FUNNEL_CSV)
    return df.rename(
        columns={
            "xyz_campaign_id": "campaign",
            "Impressions": "impressions",
            "Clicks": "clicks",
            "Spent": "spent",
            "Total_Conversion": "enquiries",
            "Approved_Conversion": "approved",
        }
    ).astype({"campaign": str, "interest": str})


@pytest.fixture(scope="session")
def shoppers_df() -> pd.DataFrame:
    return pd.read_csv(SHOPPERS_CSV)
