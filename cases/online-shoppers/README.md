# Case: Online Shoppers Purchasing Intention

Observational comparison of new and returning visitors. See [case-study.md](case-study.md) and [pack/](pack/).

| | |
|---|---|
| Data | `data/online_shoppers_intention.csv`, 12,359 rows, 12,330 with a purchase label |
| Source | UCI Machine Learning Repository, [Online Shoppers Purchasing Intention Dataset](https://archive.ics.uci.edu/dataset/468/online+shoppers+purchasing+intention+dataset) |
| Licence | Creative Commons Attribution 4.0 International (CC BY 4.0), as stated on the dataset page. Attribution: Sakar, C. and Kastro, Y. (2018), UCI Machine Learning Repository |
| Groups | Returning visitors (baseline) against new visitors |
| Spec | [spec.yaml](spec.yaml), tree in [tree.yaml](tree.yaml) |

Rebuild the pack:

```bash
decisionpack run cases/online-shoppers/spec.yaml cases/online-shoppers/data/online_shoppers_intention.csv --out cases/online-shoppers/pack
```
