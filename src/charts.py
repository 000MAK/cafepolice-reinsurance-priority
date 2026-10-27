"""Article figure: tail fit (left) and the priority cost curve (right), Turkish labels."""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy import stats

BLUE, ORANGE, GREEN, INK, MUTED = "#2A5DB0", "#D9661F", "#1F8A70", "#1d1d1f", "#6b6b70"


def figure(res: dict, art: dict, path: Path) -> None:
    plt.rcParams.update({"font.family": "Calibri", "font.size": 9, "axes.edgecolor": MUTED, "axes.labelcolor": INK,
                         "xtick.color": MUTED, "ytick.color": MUTED, "axes.spines.top": False, "axes.spines.right": False})
    fig, (a, b) = plt.subplots(1, 2, figsize=(10, 3.9), dpi=200)

    # left: empirical exceedance probability vs spliced GPD tail
    x, u, g = np.sort(art["x"]), res["assumptions"]["u"], art["gpd"]
    emp = 1 - np.arange(len(x)) / len(x)
    tail = x > u
    a.scatter(x[tail], emp[tail], s=10, color=BLUE, alpha=0.75, linewidths=0, label="Gözlenen hasarlar")
    grid = np.geomspace(u, x.max() * 1.3, 200)
    a.plot(grid, res["p_exceed_u"] * stats.genpareto.sf(grid - u, g["xi"], scale=g["sigma"]), color=ORANGE, lw=2,
           label=f"Genelleştirilmiş Pareto (ξ = {g['xi']:.2f})".replace(".", ","))
    a.set(xscale="log", yscale="log", xlabel="Hasar tutarı (milyon DKK, log)", ylabel="Bir hasarın bu tutarı aşma olasılığı (log)")
    a.set_xticks([10, 20, 50, 100, 200], ["10", "20", "50", "100", "200"])
    a.set_yticks([0.05, 0.01, 0.001], ["%5", "%1", "%0,1"])
    a.minorticks_off()
    a.set_title("Kuyruk: 10 milyonu aşan 109 hasar", color=INK, fontsize=10, loc="left")
    a.legend(frameon=False, fontsize=8, loc="lower left")
    a.grid(alpha=0.25, lw=0.5)

    # right: reinsurance margin + cost of capital vs priority
    t = art["table"][np.isfinite(art["table"]["priority"])]
    b.plot(t["priority"], t["reins_margin"], color=ORANGE, lw=2)
    b.plot(t["priority"], t["capital_cost"], color=GREEN, lw=2)
    b.plot(t["priority"], t["total_cost"], color=BLUE, lw=2.6)
    lo, hi = res["optimum"]["within_5pct_range"]
    b.axvspan(lo, hi, color="#d8d8dc", alpha=0.5, lw=0)
    b.axhline(res["optimum"]["total_cost_no_reinsurance"], color=MUTED, lw=1, ls="--")
    b.text(11, res["optimum"]["total_cost_no_reinsurance"] + 2.5, "Reasüranssız toplam maliyet", color=MUTED, fontsize=8)
    p = res["optimum"]["priority"]
    b.scatter([p], [res["optimum"]["total_cost"]], s=40, color=BLUE, edgecolors="white", linewidths=1.5, zorder=5)
    end = t.iloc[-1]
    for col, lab, colr, dy in (("reins_margin", "Reasürans marjı", ORANGE, 0), ("capital_cost", "Sermaye maliyeti", GREEN, 0),
                               ("total_cost", "Toplam", BLUE, 3)):
        b.text(end["priority"] * 1.06, end[col] + dy, lab, color=INK, fontsize=8, va="center")
    b.text(np.sqrt(lo * hi), 100, "en düşük maliyetin\n%5 yakınındaki aralık", color=MUTED, fontsize=7.5, ha="center")
    b.minorticks_off()
    b.set(xscale="log", xlim=(2, 280), ylim=(0, 112), xlabel="Muafiyet (priority, milyon DKK, log)", ylabel="Yıllık maliyet (milyon DKK)")
    b.set_xticks([2, 5, 10, 20, 50, 100], ["2", "5", "10", "20", "50", "100"])
    b.set_title("Muafiyet seçimi: marj + sermaye maliyeti", color=INK, fontsize=10, loc="left")
    b.grid(alpha=0.25, lw=0.5)

    fig.tight_layout(w_pad=2.5)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, facecolor="white")
    plt.close(fig)
