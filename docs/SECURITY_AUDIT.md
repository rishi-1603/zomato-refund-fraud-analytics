# Security audit scope

2026-10-30. This is a bounded portfolio audit, not a penetration-test certificate.

- Requirements-based dependency scan and selected historical/current secret signatures were checked in the preceding audit. They do not guarantee absence of every secret or vulnerability.
- No credential is needed for the deterministic dashboard and benchmark paths. External AI-provider checks are blocked when provider credentials are unavailable.
- Credential exposure cannot be repaired by deleting a repository file: rotate/revoke the exposed credential at its issuer.
- Source/configuration and regression checks were rerun after the reviewed PR integration. Main-branch CI remains the release gate.

## Project-specific repairs

- Customer identifiers and refunds are synthetic. Public delivery attributes do not establish wrongdoing.
- Evidence tools expose no fraud verdict field; authored refusal tests do not guarantee safety of arbitrary optional narration.
- No account restriction/refund denial action is implemented or recommended solely from the score.
