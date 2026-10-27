import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from xl import expected_excess, fit_gpd, hill, optimum  # noqa: E402


class XLTests(unittest.TestCase):
    def test_hill_recovers_pareto_index(self):
        x = stats.pareto.rvs(2.0, size=50000, random_state=1)     # alpha = 2 -> xi = 0.5
        self.assertAlmostEqual(hill(x, 2000), 0.5, delta=0.04)

    def test_expected_excess_matches_monte_carlo(self):
        rng = np.random.default_rng(0)
        x = np.r_[rng.uniform(1, 10, 9000), 10 + stats.genpareto.rvs(0.3, scale=5, size=1000, random_state=rng)]
        gpd = fit_gpd(x[x > 10] - 10)
        for p in (5.0, 10.0, 25.0):
            self.assertAlmostEqual(expected_excess(x, 10.0, gpd, p), np.maximum(x - p, 0).mean(), delta=0.15)

    def test_optimum_picks_minimum_and_flat_range(self):
        t = pd.DataFrame({"priority": [5.0, 10.0, 20.0, np.inf], "total_cost": [12.0, 10.0, 10.4, 30.0]})
        o = optimum(t)
        self.assertEqual(o["priority"], 10.0)
        self.assertEqual(o["within_5pct_range"], [10.0, 20.0])
        self.assertAlmostEqual(o["saving_vs_no_reinsurance"], 2 / 3)


if __name__ == "__main__":
    unittest.main()
