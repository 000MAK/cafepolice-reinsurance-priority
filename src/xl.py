"""Per-risk excess-of-loss priority on the Danish fire losses (danishuni, CASdatasets).

Data: 2,167 fire losses over 1 mDKK reported to Copenhagen Re, 1980-1990, inflation-adjusted
to 1985 values (Embrechts, Klueppelberg & Mikosch 1997; McNeil 1996).

Pipeline
1. Tail: Hill estimator and Peaks-Over-Threshold Generalised Pareto fit; threshold sensitivity.
2. Layer cost: expected annual ceded loss of an unlimited XL cover with priority P,
   from the spliced model (empirical body below u, GPD above u) and from burning cost.
3. Capital: Monte Carlo annual retained loss, SCR proxy = VaR 99.5% - mean.
4. Priority choice: minimise reinsurance margin + cost of capital,
   C(P) = theta * E[ceded] + CoC * SCR(retained); theta and CoC are stated assumptions.
5. Checks: bootstrap of the GPD fit; fit on 1980-1987, compare with 1988-1990 burning cost.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

SEED = 42
U = 10.0                                   # POT threshold, mDKK (McNeil 1996)
PRIORITIES = np.r_[np.arange(2, 10, 1.0), np.arange(10, 41, 2.5), 50, 60, 80, 100]
THETA, COC = 0.30, 0.10                    # reinsurer margin on expected ceded loss; cost of capital


def load(path: Path) -> pd.DataFrame:
    import pyreadr
    df = pyreadr.read_r(str(path))["danishuni"]
    df["Date"] = pd.to_datetime(df["Date"])
    df["Year"] = df["Date"].dt.year
    return df


def hill(x: np.ndarray, k: int) -> float:
    """Hill estimate of xi = 1/alpha from the k largest observations."""
    xs = np.sort(x)[::-1]
    return float(np.mean(np.log(xs[:k]) - np.log(xs[k])))


def fit_gpd(excess: np.ndarray) -> dict:
    shape, _, scale = stats.genpareto.fit(excess, floc=0)
    return {"xi": float(shape), "sigma": float(scale), "n": int(len(excess))}


def fit_lognormal(excess: np.ndarray) -> dict:
    """Lognormal kuyruk benchmark'ı (alternatif kuyruk varsayımı, AIC ile)."""
    s, loc, scale = stats.lognorm.fit(excess, floc=0)
    ll = float(np.sum(stats.lognorm.logpdf(excess, s, loc=loc, scale=scale)))
    return {"s": float(s), "scale": float(scale), "aic": float(2 * 2 - 2 * ll), "n": int(len(excess))}


def expected_excess(x: np.ndarray, u: float, gpd: dict, p: float) -> float:
    """E[(X - p)+] per claim: empirical below u, GPD above u."""
    xi, sigma = gpd["xi"], gpd["sigma"]
    p_u = float((x > u).mean())
    if p >= u:
        d = p - u
        surv = (1 + xi * d / sigma) ** (-1 / xi)
        return p_u * surv * (sigma + xi * d) / (1 - xi)
    body = x[x <= u]
    return float((1 - p_u) * np.mean(np.maximum(body - p, 0)) + p_u * (u - p + sigma / (1 - xi)))


def simulate_years(x: np.ndarray, u: float, gpd: dict, lam: float, years: int, rng) -> tuple[np.ndarray, np.ndarray]:
    """Claim severities for `years` Poisson(lam) years; returns (claims, year index of each claim)."""
    n = rng.poisson(lam, years)
    total = int(n.sum())
    body = x[x <= u]
    tail = rng.random(total) < (x > u).mean()
    sev = rng.choice(body, total)
    sev[tail] = u + stats.genpareto.rvs(gpd["xi"], scale=gpd["sigma"], size=int(tail.sum()), random_state=rng)
    return sev, np.repeat(np.arange(years), n)


def priority_table(sev: np.ndarray, year_idx: np.ndarray, years: int, x: np.ndarray, gpd: dict, lam: float,
                   n_years_obs: int, theta: float = THETA, coc: float = COC) -> pd.DataFrame:
    gross = np.bincount(year_idx, sev, years)
    rows = []
    for p in list(PRIORITIES) + [np.inf]:
        ret = np.bincount(year_idx, np.minimum(sev, p), years)
        ceded_mc = float((gross - ret).mean())
        ceded = lam * expected_excess(x, U, gpd, p) if np.isfinite(p) else 0.0
        scr = float(np.quantile(ret, 0.995) - ret.mean())
        rows.append({"priority": float(p), "ceded_model": ceded, "ceded_mc": ceded_mc,
                     "burning_cost": float(np.maximum(x - p, 0).sum() / n_years_obs) if np.isfinite(p) else 0.0,
                     "retained_mean": float(ret.mean()), "scr_retained": scr,
                     "reins_margin": theta * ceded, "capital_cost": coc * scr, "total_cost": theta * ceded + coc * scr})
    return pd.DataFrame(rows)


def optimum(table: pd.DataFrame) -> dict:
    row = table.loc[table["total_cost"].idxmin()]
    none = table[~np.isfinite(table["priority"])].iloc[0]
    near = table[np.isfinite(table["priority"]) & (table["total_cost"] <= 1.05 * row["total_cost"])]["priority"]
    return {"priority": float(row["priority"]), "within_5pct_range": [float(near.min()), float(near.max())],
            "total_cost": float(row["total_cost"]),
            "total_cost_no_reinsurance": float(none["total_cost"]),
            "saving_vs_no_reinsurance": float(1 - row["total_cost"] / none["total_cost"])}


def run(data_path: Path, out_dir: Path, years: int = 50_000) -> tuple[dict, dict]:
    rng = np.random.default_rng(SEED)
    df = load(data_path)
    x = df["Loss"].to_numpy()
    n_years = int(df["Year"].nunique())
    lam = len(x) / n_years
    res: dict = {"claims": int(len(x)), "years": n_years, "first": str(df["Date"].min().date()), "last": str(df["Date"].max().date()),
                 "claims_per_year": float(lam), "annual_counts": df.groupby("Year").size().astype(int).to_dict(),
                 "median": float(np.median(x)), "mean": float(x.mean()), "max": float(x.max()),
                 "top10_share": float(np.sort(x)[-10:].sum() / x.sum()), "assumptions": {"theta": THETA, "coc": COC, "u": U}}

    # 1. tail
    gpd = fit_gpd(x[x > U] - U)
    res["gpd"] = gpd
    ln = fit_lognormal(x[x > U] - U)
    gpd_ll = float(np.sum(stats.genpareto.logpdf(x[x > U] - U, gpd["xi"], scale=gpd["sigma"])))
    res["tail_benchmark"] = {"gpd_aic": round(2 * 2 - 2 * gpd_ll, 2),
                              "lognormal_aic": round(ln["aic"], 2),
                              "lognormal_s": round(ln["s"], 4),
                              "winner": "GPD" if (2 * 2 - 2 * gpd_ll) < ln["aic"] else "Lognormal"}
    res["p_exceed_u"] = float((x > U).mean())
    res["hill_xi_k_eq_n_u"] = hill(x, gpd["n"])
    res["threshold_sensitivity"] = {str(u): {"n": int((x > u).sum()), **{k: v for k, v in fit_gpd(x[x > u] - u).items() if k != "n"}}
                                    for u in (5.0, 7.5, 10.0, 15.0, 20.0)}
    ks = np.arange(20, 501, 5)
    hill_curve = np.array([hill(x, k) for k in ks])

    # 2-4. layer cost, capital, optimum
    sev, yidx = simulate_years(x, U, gpd, lam, years, rng)
    table = priority_table(sev, yidx, years, x, gpd, lam, n_years)
    res["optimum"] = optimum(table)
    res["sensitivity"] = {}
    for theta in (0.2, 0.3, 0.5):
        for coc in (0.06, 0.10):
            res["sensitivity"][f"theta={theta},coc={coc}"] = optimum(priority_table(sev, yidx, years, x, gpd, lam, n_years, theta, coc))["priority"]

    # 5a. bootstrap of the GPD fit -> uncertainty of xi and of the ceded cost at the optimum
    exc = x[x > U] - U
    p_star = res["optimum"]["priority"]
    boot = []
    for _ in range(1000):
        g = fit_gpd(rng.choice(exc, len(exc)))
        boot.append((g["xi"], lam * expected_excess(x, U, g, p_star) if g["xi"] < 1 else np.inf))
    boot = np.array(boot)
    res["bootstrap"] = {"xi_ci95": np.quantile(boot[:, 0], [0.025, 0.975]).tolist(),
                        "ceded_at_optimum_ci95": np.quantile(boot[:, 1], [0.025, 0.975]).tolist()}

    # 5b. time hold-out: fit 1980-1987, compare expected ceded with 1988-1990 burning cost
    tr, te = df[df["Year"] <= 1987], df[df["Year"] >= 1988]
    xt = tr["Loss"].to_numpy()
    g_tr = fit_gpd(xt[xt > U] - U)
    lam_tr = len(xt) / tr["Year"].nunique()
    n_te, sims = te["Year"].nunique(), 20_000
    sev_tr, yidx_tr = simulate_years(xt, U, g_tr, lam_tr, n_te * sims, rng)
    res["holdout"] = {"train_gpd": g_tr, "train_claims_per_year": float(lam_tr), "test_claims_per_year": float(len(te) / n_te), "by_priority": {}}
    for p in (5.0, 10.0, 20.0, 30.0):
        observed = float(np.maximum(te["Loss"].to_numpy() - p, 0).sum() / n_te)
        sim_avg = np.bincount(yidx_tr, np.maximum(sev_tr - p, 0), n_te * sims).reshape(sims, n_te).mean(axis=1)
        res["holdout"]["by_priority"][str(p)] = {"expected": float(lam_tr * expected_excess(xt, U, g_tr, p)), "observed": observed,
                                                 "predictive_90pct": np.quantile(sim_avg, [0.05, 0.95]).tolist(),
                                                 "share_of_sims_at_or_above_observed": float((sim_avg >= observed).mean())}

    out_dir.mkdir(parents=True, exist_ok=True)
    table.replace(np.inf, None).to_csv(out_dir / "priority_table.csv", index=False)
    (out_dir / "metrics.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    return res, {"x": x, "gpd": gpd, "table": table, "ks": ks, "hill": hill_curve}
