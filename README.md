# Café Poliçe: where to set an excess-of-loss priority (Danish fire losses)

[![License: MIT](https://img.shields.io/badge/code-MIT-blue.svg)](LICENSE)

Code, results and the Turkish article *"Reasürans Dilimini Nereye Koymalı?"* (Café Poliçe) on choosing the priority of a per-risk excess-of-loss (XL) cover with Extreme Value Theory.

Results card on Hugging Face: [makactuary/danish-fire-xl-priority](https://huggingface.co/makactuary/danish-fire-xl-priority)

## Data

`danishuni` from CASdatasets (C. Dutang and A. Charpentier, GPL ≥ 2): 2,167 fire losses over 1 mDKK reported to Copenhagen Re, 1980–1990, inflation-adjusted to 1985 values. Downloaded at run time into `data/` (git-ignored, not redistributed).

## Method

1. **Tail**: Peaks-Over-Threshold Generalised Pareto fit above u = 10 mDKK (109 losses), Hill estimator and threshold sensitivity.
2. **Layer cost**: expected annual ceded loss of an unlimited XL cover with priority P, from a spliced model (empirical body below u, GPD above), checked against burning cost.
3. **Capital**: 50,000 simulated years (Poisson frequency); SCR proxy = VaR 99.5% − mean of the retained annual loss.
4. **Priority**: minimise reinsurer margin (θ = 30% of expected ceded loss) + cost of capital (10% of SCR). Both are stated assumptions, varied in a sensitivity grid.
5. **Checks**: bootstrap of the GPD fit; fit on 1980–1987 and compare with the 1988–1990 outcome under the model's own predictive distribution.

## Results

| | |
|---|---|
| GPD shape ξ (u = 10) | 0.50, bootstrap 95% CI 0.13–0.79; Hill 0.63; 0.45–0.68 across u = 5–20 |
| Lowest-cost priority | 60 mDKK; any priority from 37.5 to 100 mDKK is within 5% of the minimum |
| Cost vs no reinsurance | 34.2 vs 65.1 mDKK a year (−48%) |
| Sensitivity (θ 20–50%, CoC 6–10%) | best priority 40–100 mDKK |
| Expected ceded loss at 60 mDKK | bootstrap 95% range 2.1–164 mDKK a year |
| Hold-out, priority 10 | expected 107, observed 213 mDKK a year; 3.9% of simulations as bad (frequency rose from 188 to 221 claims a year) |
| Hold-out, priority 30 | expected 40, observed 93; inside the predictive range (8.2%) |

The priority is a flat valley, not a point. The bigger risk is in the lower layers: an untrended model understates them.

## Run

```bash
pip install -r requirements.txt
curl -L -o data/danishuni.rda https://raw.githubusercontent.com/dutangc/CASdatasets/master/data/danishuni.rda
python -c "import sys; sys.path.insert(0,'src'); from pathlib import Path; from xl import run; from charts import figure; r,a=run(Path('data/danishuni.rda'), Path('outputs')); figure(r,a,Path('outputs/charts/01_kuyruk_ve_muafiyet.png'))"
python article/build_article.py
python -m pytest tests -q
```

## Limitations

Unlimited layer, no reinstatements or aggregate terms; Poisson frequency without trend; reinsurance price and cost of capital are assumptions. A method illustration, not a reinsurance recommendation.

## Licence

Code: MIT. Data: GPL ≥ 2 (CASdatasets), not redistributed here.
