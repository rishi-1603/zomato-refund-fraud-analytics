"""Case management lifecycle for FoodTrust investigations.
================================================================================
A flagged customer is a REVIEW CANDIDATE, never a verdict. This module gives an
analyst a formal, auditable case lifecycle with a state machine, priorities and
an append-only audit trail. It is pure Python (no Streamlit) so every rule is
unit-testable; the UI adapter lives in app.py.

Language policy (binding, see docs/METRIC_DICTIONARY.md §F):
  - 'Cleared' and 'Confirmed Issue' are case outcomes, not fraud verdicts.
  - Every status change, priority change and outcome is recorded with actor,
    timestamp and note. Cleared cases remain in history (never deleted).

Deterministic: no network, no LLM, no randomness beyond uuid case ids.
"""
from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone

# ── Vocabulary ───────────────────────────────────────────────────────────────
NEW = "New"
UNDER_REVIEW = "Under Review"
MORE_INFO_REQUIRED = "More Information Required"
ESCALATED = "Escalated"
CLEARED = "Cleared"
CONFIRMED_ISSUE = "Confirmed Issue"
CLOSED = "Closed"

CASE_STATUSES = (
    NEW, UNDER_REVIEW, MORE_INFO_REQUIRED, ESCALATED,
    CLEARED, CONFIRMED_ISSUE, CLOSED,
)

# State machine: from_status -> set of allowed to_statuses.
# Closed is terminal. Cleared cases may only move to Closed (they stay in
# history and are never re-opened — re-opening would erase the audit value).
ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    NEW: frozenset({UNDER_REVIEW, ESCALATED, CLEARED}),
    UNDER_REVIEW: frozenset({MORE_INFO_REQUIRED, ESCALATED, CLEARED, CONFIRMED_ISSUE, CLOSED}),
    MORE_INFO_REQUIRED: frozenset({UNDER_REVIEW, ESCALATED, CLEARED, CLOSED}),
    ESCALATED: frozenset({UNDER_REVIEW, CLEARED, CONFIRMED_ISSUE, CLOSED}),
    CLEARED: frozenset({CLOSED}),
    CONFIRMED_ISSUE: frozenset({CLOSED}),
    CLOSED: frozenset(),
}

PRIORITIES = ("Low", "Medium", "High")

_RISK_BANDS = ("Low Risk", "Review Recommended", "High Priority Review")

_MAX_NOTES = 500
_MAX_REASONS = 20
_MAX_EVENTS = 200

_TS = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?\+00:00$")


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _text(value, label, limit=_MAX_NOTES, required=True):
    if not isinstance(value, str) or (required and not value.strip()) or len(value) > limit:
        raise ValueError(f"{label} must be non-empty text of at most {limit} characters.")
    return value.strip()


def _num(value, label, minimum=None, maximum=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be a number.")
    v = float(value)
    if v != v or v in (float("inf"), float("-inf")):  # NaN / inf
        raise ValueError(f"{label} must be finite.")
    if minimum is not None and v < minimum:
        raise ValueError(f"{label} must be >= {minimum}.")
    if maximum is not None and v > maximum:
        raise ValueError(f"{label} must be <= {maximum}.")
    return v


# ── Case creation ────────────────────────────────────────────────────────────
def open_case(*, customer_id, risk_score, risk_band, exposure, alert_reasons,
              opened_by="analyst", note=""):
    """Create a new investigation case from a flagged customer record.

    risk_band must be one of the three prioritisation bands. Bands are review
    priorities, not guilt declarations.
    """
    customer_id = _text(customer_id, "Customer ID", 60)
    score = _num(risk_score, "Risk score", 0, 100)
    if risk_band not in _RISK_BANDS:
        raise ValueError(f"Risk band must be one of {_RISK_BANDS}.")
    exposure = _num(exposure, "Exposure", 0)
    if not isinstance(alert_reasons, (list, tuple)) or not alert_reasons:
        raise ValueError("alert_reasons must be a non-empty list.")
    if len(alert_reasons) > _MAX_REASONS:
        raise ValueError(f"Too many alert reasons (max {_MAX_REASONS}).")
    reasons = [_text(r, "Alert reason", 200) for r in alert_reasons]
    case = {
        "case_id": uuid.uuid4().hex,
        "customer_id": customer_id,
        "risk_score": score,
        "risk_band": risk_band,
        "exposure": exposure,
        "alert_reasons": reasons,
        "status": NEW,
        "priority": "Medium" if risk_band == "Review Recommended" else (
            "High" if risk_band == "High Priority Review" else "Low"),
        "outcome": None,
        "note": _text(note, "Note", required=False),
        "opened_at_utc": _now_utc(),
        "updated_at_utc": _now_utc(),
        "events": [],
    }
    case["events"].append({
        "at_utc": case["opened_at_utc"], "actor": _text(opened_by, "Actor", 60),
        "field": "status", "from": None, "to": NEW, "note": "Case opened from flag",
    })
    return case


# ── Mutations (each returns a new dict; audit trail is append-only) ─────────
def _append_event(case, actor, field, from_value, to_value, note):
    case["events"].append({
        "at_utc": _now_utc(), "actor": actor, "field": field,
        "from": from_value, "to": to_value, "note": note,
    })
    if len(case["events"]) > _MAX_EVENTS:
        raise ValueError(f"Too many audit events (max {_MAX_EVENTS}); close the case and export it.")
    case["updated_at_utc"] = case["events"][-1]["at_utc"]


def change_status(case, to_status, *, actor="analyst", note=""):
    """Move the case through the state machine. Illegal transitions raise."""
    if to_status not in CASE_STATUSES:
        raise ValueError(f"Unknown status {to_status!r}.")
    current = case["status"]
    if to_status == current:
        raise ValueError("Case is already in that status.")
    if to_status not in ALLOWED_TRANSITIONS[current]:
        raise ValueError(
            f"Transition {current} -> {to_status} is not allowed. "
            f"Allowed: {sorted(ALLOWED_TRANSITIONS[current]) or 'none (terminal)'}")
    actor = _text(actor, "Actor", 60)
    note = _text(note, "Note", required=False)
    case["status"] = to_status
    if to_status == CLOSED and case["outcome"] is None:
        raise ValueError("A case cannot be closed without recording an outcome.")
    _append_event(case, actor, "status", current, to_status, note)
    return case


def set_priority(case, priority, *, actor="analyst", note=""):
    if priority not in PRIORITIES:
        raise ValueError(f"Priority must be one of {PRIORITIES}.")
    actor = _text(actor, "Actor", 60)
    note = _text(note, "Note", required=False)
    if priority == case["priority"]:
        raise ValueError("Priority is unchanged.")
    old = case["priority"]
    case["priority"] = priority
    _append_event(case, actor, "priority", old, priority, note)
    return case


def add_note(case, note, *, actor="analyst"):
    note = _text(note, "Note")
    actor = _text(actor, "Actor", 60)
    _append_event(case, actor, "note", None, note[:80], note)
    return case


def record_outcome(case, outcome, *, actor="analyst", note=""):
    """Record the investigation outcome. Advisory workflow: outcomes describe
    what the analyst found, they never trigger automatic customer actions."""
    if outcome not in {CLEARED, CONFIRMED_ISSUE}:
        raise ValueError("Outcome must be Cleared or Confirmed Issue.")
    if case["status"] in {CLOSED, }:
        raise ValueError("Cannot record an outcome on a closed case.")
    if case["outcome"] is not None:
        raise ValueError("Outcome already recorded.")
    actor = _text(actor, "Actor", 60)
    note = _text(note, "Note", required=False)
    case["outcome"] = outcome
    _append_event(case, actor, "outcome", None, outcome, note)
    return case


def close_case(case, *, actor="analyst", note=""):
    if case["status"] == CLOSED:
        raise ValueError("Case is already closed.")
    if case["outcome"] is None:
        raise ValueError("Record an outcome (Cleared or Confirmed Issue) before closing.")
    return change_status(case, CLOSED, actor=actor, note=note)


# ── Serialisation / validation ───────────────────────────────────────────────
def validate(case):
    """Validate a case dict (shape, values, state machine, audit consistency)."""
    if not isinstance(case, dict):
        raise ValueError("Case must be a dict.")
    if not isinstance(case.get("case_id"), str) or len(case["case_id"]) != 32:
        raise ValueError("Invalid case id.")
    uuid.UUID(hex=case["case_id"])
    _text(case.get("customer_id", ""), "Customer ID", 60)
    _num(case.get("risk_score"), "Risk score", 0, 100)
    if case.get("risk_band") not in _RISK_BANDS:
        raise ValueError("Invalid risk band.")
    _num(case.get("exposure"), "Exposure", 0)
    if case.get("status") not in CASE_STATUSES:
        raise ValueError("Invalid status.")
    if case.get("priority") not in PRIORITIES:
        raise ValueError("Invalid priority.")
    if case.get("outcome") not in {None, CLEARED, CONFIRMED_ISSUE}:
        raise ValueError("Invalid outcome.")
    events = case.get("events")
    if not isinstance(events, list) or not events:
        raise ValueError("Case must have an audit trail.")
    if len(events) > _MAX_EVENTS:
        raise ValueError("Too many audit events.")
    for ev in events:
        if not isinstance(ev, dict):
            raise ValueError("Invalid audit event.")
        _text(ev.get("at_utc", ""), "Event time", 50)
        if not _TS.match(ev["at_utc"]):
            raise ValueError("Event timestamp must be UTC ISO-8601.")
        _text(ev.get("actor", ""), "Actor", 60)
        _text(ev.get("field", ""), "Field", 40)
        if ev.get("note") is not None and not isinstance(ev["note"], str):
            raise ValueError("Event note must be text.")
    status_seq = [e["to"] for e in events if e["field"] == "status"]
    if not status_seq or status_seq[0] != NEW:
        raise ValueError("Audit trail must begin with case opening (New).")
    if status_seq[-1] != case["status"]:
        raise ValueError("Audit trail does not match current status.")
    for a, b in zip(status_seq, status_seq[1:]):
        if b not in ALLOWED_TRANSITIONS[a]:
            raise ValueError(f"Audit trail contains illegal transition {a} -> {b}.")
    if case["status"] == CLOSED and case["outcome"] is None:
        raise ValueError("Closed case must have an outcome.")
    return case


def to_dict(case) -> dict:
    return validate(_copy(case))


def _copy(case):
    import copy as _copymod
    try:
        out = _copymod.deepcopy(case)
    except Exception as exc:  # pragma: no cover - defensive
        raise ValueError("Case is not deep-copyable.") from exc
    return out


def export_cases(cases) -> bytes:
    """Serialise a list of cases for download. Cleared/closed cases retained."""
    import json
    if not isinstance(cases, (list, tuple)):
        raise ValueError("Cases must be a list.")
    payload = [validate(_copy(c)) for c in cases]
    return json.dumps(payload, ensure_ascii=False, allow_nan=False, indent=2).encode("utf-8")


def import_cases(payload):
    import json
    if not isinstance(payload, bytes) or len(payload) > 512_000:
        raise ValueError("Import must be JSON no larger than 512 KB.")
    try:
        data = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Invalid JSON.") from exc
    if not isinstance(data, list):
        raise ValueError("Import must be a JSON array of cases.")
    return [validate(c) for c in data]
