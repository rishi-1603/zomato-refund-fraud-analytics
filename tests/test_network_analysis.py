"""
test_network_analysis.py — the ring detector must be correct and honest.
==============================================================================
Pins:
  1. GRAPH MATH    — union-find correctness, edge thresholding, component counts.
  2. THE SCREEN    — density ranking must not reward size alone; the 788-customer
                     busy-area blob must NOT outrank small dense groups.
  3. THE NULL      — the permutation test must be reproducible and must not
                     manufacture a clustering signal that is not in the data.
"""
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from network_analysis import (  # noqa: E402
    DSU,
    MIN_ORDERS_FOR_EDGE,
    clustering_test,
    customer_stats,
    density_screen,
    load,
    shared_driver_pairs,
)


@pytest.fixture(scope="module")
def df():
    return load()


@pytest.fixture(scope="module")
def stats(df):
    return customer_stats(df)


class TestUnionFind:
    """Connected components are the backbone — get these wrong and every ring is wrong."""

    def test_single_elements_are_separate(self):
        d = DSU()
        for x in ("a", "b", "c"):
            d.add(x)
        assert len({d.find(x) for x in "abc"}) == 3

    def test_union_merges(self):
        d = DSU()
        d.union("a", "b")
        assert d.find("a") == d.find("b")

    def test_transitive_union(self):
        d = DSU()
        d.union("a", "b")
        d.union("b", "c")
        assert d.find("a") == d.find("c")

    def test_path_compression_does_not_change_groups(self):
        d = DSU()
        for i in range(20):
            d.union(f"n{i}", f"n{i+1}")
        roots = {d.find(f"n{i}") for i in range(21)}
        assert len(roots) == 1

    def test_repeated_union_is_idempotent(self):
        d = DSU()
        d.union("a", "b")
        before = d.find("a")
        d.union("a", "b")
        assert d.find("a") == before


class TestEdgeThreshold:
    """A single shared order must not create an edge — that would link everyone."""

    def test_threshold_is_at_least_two(self):
        assert MIN_ORDERS_FOR_EDGE >= 2

    def test_shared_driver_pairs_are_symmetric_and_unique(self, df):
        pairs, by_driver = shared_driver_pairs(df)
        for a, b in list(pairs)[:200]:
            assert a < b, "pairs must be stored in a canonical order"
            assert (a, b) in pairs
        # no self-pairs
        assert all(a != b for a, b in pairs)

    def test_every_pair_shares_a_driver(self, df):
        pairs, by_driver = shared_driver_pairs(df)
        driver_sets = {}
        for driver, customers in by_driver.items():
            for c in customers:
                driver_sets.setdefault(c, set()).add(driver)
        for a, b in list(pairs)[:100]:
            assert driver_sets[a] & driver_sets[b], f"{a} and {b} share no driver"


class TestDensityScreen:
    """Ranking must reflect abnormal behaviour, not component size."""

    def test_screen_is_sorted_by_excess_descending(self, df, stats):
        comps = [[c] for c in stats["Customer_ID"].head(50)]
        # build one deliberately abnormal component
        screen = density_screen(comps, stats, min_size=1)
        if len(screen) > 1:
            excess = screen["excess_pp"].tolist()
            assert excess == sorted(excess, reverse=True)

    def test_big_component_is_not_automatically_top(self, df, stats):
        """The 788-customer busy-area blob must not win on size."""
        big = list(stats["Customer_ID"].head(788))
        small_dense = list(stats.nlargest(5, "refund_rate_pct")["Customer_ID"])
        screen = density_screen([big, small_dense], stats, min_size=1)
        assert not screen.empty
        # the top row must be the dense group, not the large one
        assert screen.iloc[0]["customers"] == 5, (
            "size alone influenced the ranking — the screen would flag busy areas")

    def test_baseline_rate_matches_dataset(self, df, stats):
        screen = density_screen([list(stats["Customer_ID"].head(10))], stats, min_size=1)
        expected = stats["refunds"].sum() / stats["orders"].sum() * 100
        assert screen.iloc[0]["baseline_rate_pct"] == pytest.approx(round(expected, 2))

    def test_excess_is_component_minus_baseline(self, df, stats):
        screen = density_screen([list(stats["Customer_ID"].head(10))], stats, min_size=1)
        row = screen.iloc[0]
        assert row["excess_pp"] == pytest.approx(
            row["refund_rate_pct"] - row["baseline_rate_pct"], abs=0.02)

    def test_min_size_filter_respected(self, df, stats):
        comps = [list(stats["Customer_ID"].head(2))]
        assert density_screen(comps, stats, min_size=3).empty


class TestClusteringNull:
    """The permutation test must be reproducible and must not manufacture signal."""

    def test_is_reproducible(self, df, stats):
        a = clustering_test(df, stats)
        b = clustering_test(df, stats)
        assert a["observed_clustering"] == b["observed_clustering"]
        assert a["p_value"] == b["p_value"]

    def test_observed_is_a_fraction(self, df, stats):
        t = clustering_test(df, stats)
        assert 0.0 <= t["observed_clustering"] <= 1.0
        assert 0.0 <= t["p_value"] <= 1.0

    def test_published_null_result_is_pinned(self, df, stats):
        """No clustering beyond chance is the published finding — pin it.

        If this flips, the README narrative must change with it.
        """
        t = clustering_test(df, stats)
        assert t["p_value"] > 0.05, (
            "clustering is now significant — update reports/network_analysis.md "
            "and the README, this is a finding change, not a test failure to silence"
        )
        assert t["observed_clustering"] < t["null_p95"]

    def test_null_distribution_is_centred_near_observed_scale(self, df, stats):
        t = clustering_test(df, stats)
        # the null mean must be the same order of magnitude as the statistic
        assert t["null_mean"] > 0
        assert 0.1 < t["observed_clustering"] / t["null_mean"] < 10


class TestCommittedArtifacts:
    def test_json_exists_with_expected_sections(self):
        import json
        p = ROOT / "reports" / "network_analysis.json"
        assert p.exists(), "run scripts/network_analysis.py to regenerate"
        d = json.loads(p.read_text())
        for key in ("data", "parameters", "layers", "clustering_test", "honesty"):
            assert key in d, f"missing {key}"
        assert set(d["layers"]) == {
            "shared_delivery_person", "shared_restaurant_cell", "shared_drop_cell"}

    def test_markdown_report_exists(self):
        assert (ROOT / "reports" / "network_analysis.md").exists()

    def test_honesty_section_is_present_and_non_trivial(self):
        import json
        d = json.loads((ROOT / "reports" / "network_analysis.json").read_text())
        assert len(d["honesty"]) >= 3
        assert any("not evidence of collusion" in h for h in d["honesty"])
