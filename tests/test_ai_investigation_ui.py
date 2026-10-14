"""
test_ai_investigation_ui.py — regression tests for the Investigation tab's
AI assistant and baseline sections, run in a simulated Streamlit runtime.

Bugs (found 2026-10-14, reported by the project owner):

1. Clicking "Run AI Investigation" showed "AI investigation module not
   available." The lazy import `from app.dashboard.utils.ai_investigator
   import ...` could never work in the Streamlit runtime: the script's own
   directory is on sys.path there, and `dashboard/app.py` shadows any
   `app` package. Fixed by moving the module next to app.py
   (dashboard/ai_investigator.py) and importing it as a sibling.

2. The baseline section showed "Baseline normalization unavailable" —
   `fig.update_layout(**PLOTLY_LAYOUT, ..., height=320)` collided with the
   `height=380` already inside PLOTLY_LAYOUT (TypeError), so the whole
   section (metrics + P95 chart) was swallowed by a bare except.

These tests reproduce the production runtime: they purge the repo root from
sys.path and clear cached modules, then drive the real UI with AppTest.
"""
import os
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

_MODULES_TO_PURGE = ("ai_investigator", "dashboard.ai_investigator",
                     "baseline_normalization", "dashboard.baseline_normalization")


def _run_in_streamlit_runtime(fn):
    """Run fn() with the repo root NOT importable (like Streamlit Cloud)."""
    cwd = os.getcwd()
    os.chdir(ROOT)  # DATA_PATH is repo-root-relative
    saved_path = list(sys.path)
    saved_mods = {k: v for k, v in list(sys.modules.items())
                  if k in _MODULES_TO_PURGE or k.startswith("app.")}
    for k in saved_mods:
        del sys.modules[k]
    sys.path[:] = [p for p in sys.path if not p or Path(p).resolve() != ROOT]
    try:
        fn()
    finally:
        sys.path[:] = saved_path
        sys.modules.update(saved_mods)
        os.chdir(cwd)


def test_ai_investigation_button_works_in_streamlit_runtime():
    from streamlit.testing.v1 import AppTest

    def scenario():
        at = AppTest.from_file(str(ROOT / "dashboard" / "app.py"),
                               default_timeout=240)
        at.run()
        assert not at.exception, f"dashboard raised: {at.exception}"

        # The AI assistant lives in the Investigation tab; AppTest sees all
        # tab content, so drive it directly by key.
        sb = at.selectbox(key="inv_customer")
        assert "CUST09534" in sb.options, "known suspect missing from picker"
        sb.set_value("CUST09534").run()
        assert not at.exception, at.exception

        at.button(key="inv_run").click().run()
        assert not at.exception, f"AI investigation raised: {at.exception}"

        info_texts = [i.value for i in at.info]
        assert not any("AI investigation module not available" in t
                       for t in info_texts), info_texts
        assert not at.error, [e.value for e in at.error]

        # Evidence rendered with dataset-verified values for CUST09534
        # (cross-checked against data/processed + reports/fraud_suspects.csv)
        md = "\n".join(m.value for m in at.markdown)
        assert "**Risk Score:** 56.66" in md, "evidence block did not render"
        assert "**Tier:** Medium" in md, "tier mismatch"
        assert "**Refund Rate:** 100.0%" in md, "refund rate mismatch"
        assert "**Refunds:** 8" in md, "refund count mismatch"
        assert "**Total Exposure:** ₹4,379" in md, "exposure mismatch"
        assert "**Volume Band:** 6-10 orders" in md, "volume band mismatch"
        assert "**Band P95:** 33.33%" in md, "band P95 mismatch"

    _run_in_streamlit_runtime(scenario)


def test_baseline_section_renders_in_streamlit_runtime():
    from streamlit.testing.v1 import AppTest

    # Expected values computed independently from the data
    from scripts.baseline_normalization import build_baselines
    df = pd.read_csv(ROOT / "data" / "processed" / "zomato_with_refunds.csv")
    cust, _bands = build_baselines(df)
    suspects = pd.read_csv(ROOT / "reports" / "fraud_suspects.csv")
    cust["is_flagged"] = cust["Customer_ID"].isin(set(suspects["Customer_ID"]))
    flagged = cust[cust["is_flagged"]]
    n_above = int(flagged["above_baseline"].sum())
    n_below = int((~flagged["above_baseline"]).sum())
    n_above_all = int(cust["above_baseline"].sum())
    assert n_above + n_below == 279, "flagged count drifted"

    def scenario():
        at = AppTest.from_file(str(ROOT / "dashboard" / "app.py"),
                               default_timeout=240)
        at.run()
        assert not at.exception, f"dashboard raised: {at.exception}"

        info_texts = [i.value for i in at.info]
        assert not any("Baseline normalization unavailable" in t
                       for t in info_texts), info_texts

        labels = [m.label for m in at.metric]
        above_m = at.metric[labels.index("Flagged above band baseline")]
        below_m = at.metric[labels.index("Flagged but within band norms")]
        all_m = at.metric[labels.index("Above baseline (all customers)")]
        assert above_m.value == f"{n_above:,}", f"{above_m.value} != {n_above}"
        assert below_m.value == f"{n_below:,}", f"{below_m.value} != {n_below}"
        assert all_m.value == f"{n_above_all:,}", f"{all_m.value} != {n_above_all}"

    _run_in_streamlit_runtime(scenario)
