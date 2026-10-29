# Case: funnel lab (ad campaigns)

Observational comparison of two ad campaigns from a public dataset. See [case-study.md](case-study.md) for the story and [pack/](pack/) for the output.

| | |
|---|---|
| Data | `data/KAG_conversion_data.csv`, 1,143 ad sets, three campaigns. **Not committed**; `prepare.py` fetches it and checks the SHA-256 |
| Source | Kaggle, "Sales Conversion Optimization" |
| Licence | Kaggle lists it as "Other (specified in description)" and the description states no terms (checked on the dataset's Kaggle page). Not redistributed here |
| Groups | Campaign 936 (baseline) against campaign 1178 |
| Spec | [spec.yaml](spec.yaml), tree in [tree.yaml](tree.yaml) |

Fetch the data, then rebuild the pack:

```bash
python cases/funnel-lab/prepare.py
decisionpack run cases/funnel-lab/spec.yaml cases/funnel-lab/data/KAG_conversion_data.csv --out cases/funnel-lab/pack
```

The pack is committed so you can read the output without running anything.
