"""The nav bar is the only way to reach four of the five pages, so every button
must render its page without an exception. Markers are subheaders unique to each
page; the labels stay short so the 5-column bar does not truncate on a laptop.
"""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1] / "dashboard" / "app.py"

PAGES = [
    ("nav_0", "1 Overview", "highest priority first"),
    ("nav_1", "2 Refunds", "Where the refund money concentrates"),
    ("nav_2", "3 Risk review", "Explain a flag"),
    ("nav_3", "4 Operations", "Review queue & capacity"),
    ("nav_4", "5 Method", "Data, validation and methodology"),
]


@pytest.fixture(scope="module")
def app():
    at = AppTest.from_file(str(APP)).run(timeout=120)
    assert not at.exception
    return at


def test_all_five_nav_buttons_are_labelled(app):
    labels = [b.label for b in app.button if (b.key or "").startswith("nav_")]
    assert labels == [label for _, label, _ in PAGES]


def test_every_nav_button_opens_its_page(app):
    for key, label, marker in PAGES:
        app.button(key=key).click().run(timeout=120)
        assert not app.exception, f"{label} raised: {app.exception}"
        subheaders = [s.value for s in app.subheader]
        assert any(marker in s for s in subheaders), (
            f"{label} did not render {marker!r}: {subheaders}"
        )
