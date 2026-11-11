# Release gate report — Zomato refund risk & operations analytics

Applies the release gates from the universal finalization prompt. Status values:
**PASS** = verified with evidence · **CONDITIONAL** = usable, a documented limitation remains · **BLOCKED** = prevents a trustworthy release · **UNVERIFIED** = could not be checked from the build environment.

Overall: **CONDITIONAL for the code. BLOCKED for a public, recruiter-ready release** until the items in §3 are closed.

## 1. Business and analytics gates

| Gate | Status | Evidence |
|---|---|---|
| Business problem clearly documented | PASS | README §2 and §3 |
| Dataset source verified | CONDITIONAL | Source is named as the public Kaggle Zomato delivery dataset (`data/DATA_DICTIONARY.md`). The repo has no URL, licence or extraction date. Needs confirming by the owner. |
| Data assumptions explicit | PASS | README §11, `reports/assumptions_and_limitations.md` |
| Important KPIs validated | PASS | `reports/kpi_reconciliation.md`: 8 KPIs MATCH, 0 mismatches. Uses SQLite, not PostgreSQL. |
| SQL and Python consistent where comparable | PASS | Same report as above |
| No unsupported conclusions | CONDITIONAL | README claims were checked against reports (§4 of the UI report). Other reports, e.g. `reports/interview_prep.md`, were not re-audited line by line. |

## 2. Technical gates

| Gate | Status | Evidence |
|---|---|---|
| App starts locally | PASS | Streamlit `AppTest` loads the app with no exceptions. Checked from the repo root and from `/tmp`. Not a browser run. |
| Dependencies install | PASS | Clean venv from `requirements.txt` in this session |
| Main workflows function | CONDITIONAL | Load and tab state verified. Filter interactions were not clicked through in a browser. |
| Critical tests pass | PASS | `pytest`: 188 passed (186 + 2 path regression tests) |
| No unresolved critical runtime defects | PASS | Default state: 0 exceptions, 0 errors. See defect D1 below (fixed). |
| Paths work outside developer's machine | PASS | Data paths now resolve from the file location (`tests/test_app_paths.py`). No absolute developer paths in tracked files. |

**Defect D1 (fixed, Medium):** the baseline-normalisation section read its CSV with a relative path. When the app ran from another directory, three Investigation KPIs were silently dropped. Fixed in commit `1c92e3f`; the metric count is back to 28 from both directories.

**Open finding D2 (Low):** that section's `except Exception` shows a generic "unavailable" notice and hides the real cause. Logging the exception would make such failures diagnosable. Not changed here.

## 3. UI gates

| Gate | Status | Evidence |
|---|---|---|
| All main pages load | PASS | 5 tabs, identical to baseline |
| Charts display correctly | UNVERIFIED | No browser in the build environment. Two pie charts were replaced with bars; the rendering has not been seen. |
| Filters work | CONDITIONAL | Not exercised interactively |
| KPI values are dynamic | CONDITIONAL | Values were checked at default filters only |
| Layout consistent, content readable | UNVERIFIED | Needs a visual check |
| No critical visual defects | UNVERIFIED | Needs a visual check |

## 4. Documentation gates

| Gate | Status | Evidence |
|---|---|---|
| README matches implementation | CONDITIONAL | 24 relative links resolve. Figures were checked against reports. Screenshots predate the latest changes (see below). |
| Dataset source and attribution | CONDITIONAL | Same gap as §1 |
| Setup instructions tested | CONDITIONAL | Clean install and `pytest` tested. Launch tested only through `AppTest`. |
| Screenshots current | BLOCKED | `docs/screenshots/` predates the header chip, the three label renames and the two bar-chart changes. The README image shows the old labels. |
| Limitations documented | PASS | README §11 |
| Live demo URL correct | UNVERIFIED | The Streamlit Cloud URL could not be reached from the sandbox |

## 5. Deployment gates

| Gate | Status | Evidence |
|---|---|---|
| Public application reachable | UNVERIFIED | Not reachable from the sandbox |
| Application completes startup | UNVERIFIED on the platform | Startup verified locally only |
| Critical workflows smoke-tested | CONDITIONAL | Load-level only |
| No secrets exposed | PASS | Regex scan of tracked files: no API keys, tokens, private keys or passwords. `.env.example` lists variable names with empty values. `.gitignore` covers `.env`, `.venv/`, `.streamlit/secrets.toml`. |
| Deployment limitations documented | CONDITIONAL | Live app is a demo; README says it may need waking |

## 6. Repository hygiene

| Item | Status | Note |
|---|---|---|
| `.env.example` | PASS | Added in `f43b5b0` |
| `.gitignore` | PASS | Extended in `f43b5b0` |
| `LICENSE` | BLOCKED (owner decision) | None present. The licence choice belongs to the owner, so it was not added. The Kaggle source's terms must also be checked. |
| Large tracked files | Note | `data/processed/zomato_with_refunds.csv` (~7 MB) and `data/raw/Zomato Dataset.csv` (~6 MB) are tracked. Acceptable for a portfolio, but the README should say so. |

## 7. Required actions to reach a recruiter-ready release

1. Retake the screenshots on the owner's machine from the current app, and update the README gallery. **(BLOCKED item)**
2. Confirm the Kaggle dataset URL, licence and extraction date, and record them in the README and data dictionary.
3. Choose and add a `LICENSE` file, if the owner wants one.
4. Click through every filter and visually check every tab in a browser. Record any defects.
5. Verify the public Streamlit URL loads and all five tabs render. Record the date.
6. Review PR #6 and merge it to `main` only after steps 1–5.
