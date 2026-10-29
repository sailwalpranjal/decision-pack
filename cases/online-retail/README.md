# Case: Online Retail II (average order value, year on year)

Observational comparison of two full years of invoices from a UK online retailer. See [case-study.md](case-study.md) and [pack/](pack/).

| | |
|---|---|
| Data | Online Retail II: 1,067,371 invoice lines, December 2009 to December 2011. **Not committed** (45 MB Excel file); `prepare.py` downloads it |
| Source | UCI Machine Learning Repository, [Online Retail II](https://archive.ics.uci.edu/dataset/502/online+retail+ii) |
| Licence | Creative Commons Attribution 4.0 International (CC BY 4.0), as stated on the dataset page. Attribution: Chen, D. (2012). Online Retail II [Dataset]. UCI Machine Learning Repository. https://doi.org/10.24432/C5CG6D |
| Checksum | SHA-256 of the downloaded zip, as I received it: `572e36277c2390fbfde10664750731e0a86f55e33470d91919085f0408e67bfb` |
| Groups | Y1 (Dec 2009 to Nov 2010, baseline) against Y2 (Dec 2010 to Nov 2011) |
| Spec | [spec.yaml](spec.yaml), tree in [tree.yaml](tree.yaml) |

Reproduce:

```bash
python cases/online-retail/prepare.py                  # downloads, prepares data/sales_lines.csv
decisionpack run cases/online-retail/spec.yaml cases/online-retail/data/sales_lines.csv --out cases/online-retail/pack
```

Reading the Excel workbook takes a few minutes the first time. The prepared table has 1,016,558 sales lines, which makes this the case that runs on about a million rows (the analysis took about 7.5 seconds on my machine).
