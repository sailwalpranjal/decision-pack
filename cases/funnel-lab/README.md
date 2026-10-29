# Case: funnel lab (ad campaigns)

Observational comparison of two ad campaigns from a public dataset. See [case-study.md](case-study.md) for the story and [pack/](pack/) for the output.

| | |
|---|---|
| Data | `data/KAG_conversion_data.csv`, 1,143 ad sets, three campaigns |
| Source | Kaggle, "Sales Conversion Optimization" |
| Licence | Recorded in my funnel lab as public domain / CC0-equivalent; **not independently re-verified**. Check Kaggle before reusing the file |
| Groups | Campaign 936 (baseline) against campaign 1178 |
| Spec | [spec.yaml](spec.yaml), tree in [tree.yaml](tree.yaml) |

Rebuild the pack:

```bash
decisionpack run cases/funnel-lab/spec.yaml cases/funnel-lab/data/KAG_conversion_data.csv --out cases/funnel-lab/pack
```

The pack is committed so you can read the output without running anything.
