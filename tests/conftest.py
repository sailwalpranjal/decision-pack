from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
FUNNEL_CSV = ROOT / "cases" / "funnel-lab" / "data" / "KAG_conversion_data.csv"
SHOPPERS_CSV = ROOT / "cases" / "online-shoppers" / "data" / "online_shoppers_intention.csv"


@pytest.fixture(scope="session")
def funnel_df() -> pd.DataFrame:
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
