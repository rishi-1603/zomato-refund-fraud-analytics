"""Render every chart in the Streamlit app to PNG, using the app's own figure specs and data.

This is a chart-only gallery. It does not capture full app pages.
Run from the repository root:  python scripts/render_chart_gallery.py
Requires kaleido==0.2.1 (bundles its own headless Chromium).
"""
import json
import os
import re
from pathlib import Path

import plotly.graph_objects as go
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "dashboard" / "app.py"
OUT = ROOT / "docs" / "chart_renders"
DARK = "#141D31"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    at = AppTest.from_file(str(APP), default_timeout=300).run()
    if at.exception:
        raise SystemExit(f"App raised: {[e.value for e in at.exception]}")
    manifest = []
    for i, el in enumerate(at.get("plotly_chart")):
        spec = json.loads(el.proto.spec)
        fig = go.Figure(data=spec.get("data", []), layout=spec.get("layout", {}))
        fig.update_layout(
            paper_bgcolor=DARK, plot_bgcolor=DARK, font=dict(color="#E8ECF4", size=13),
            title=dict(font=dict(color="#F1F5F9", size=16)),
            legend=dict(font=dict(color="#CBD5E1")), margin=dict(l=70, r=40, t=70, b=60),
        )
        axis = dict(gridcolor="#26375C", linecolor="#334155", zerolinecolor="#334155",
                    tickfont=dict(color="#CBD5E1"), title_font=dict(color="#CBD5E1"))
        fig.update_xaxes(**axis)
        fig.update_yaxes(**axis)
        title = (spec.get("layout", {}).get("title", {}) or {}).get("text") or f"chart_{i}"
        slug = re.sub(r"[^a-z0-9]+", "_", str(title).lower()).strip("_")[:60] or f"chart_{i}"
        fn = f"{i:02d}_{slug}.png"
        fig.write_image(str(OUT / fn), width=900, height=520, scale=1)
        manifest.append({"file": fn, "title": title})
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"Rendered {len(manifest)} charts to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
