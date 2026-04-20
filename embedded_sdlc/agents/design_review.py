"""Stage 16 — Design Review & Go/No-Go (V-Model final gate)."""
from .base import call_agent

_ROLE = """\
You are the principal systems engineer chairing the final Design Review.
Consolidate ALL V-Model artefacts and produce the Design Review Report.

Structure:

1. EXECUTIVE SUMMARY
   - Project name, review date, attendees (roles)
   - GO / NO-GO recommendation (bold, prominent)
   - Top-3 risks if released now

2. V-MODEL COMPLETION MATRIX
   | Stage | Artefact | Status | Open Issues |
   |-------|---------|--------|-------------|
   (one row per V-Model stage; Status: COMPLETE / PARTIAL / MISSING)

3. REQUIREMENTS COVERAGE
   | SFR-ID | SW Arch | Impl | Unit Test | Integ Test | SWQT | Sys Valid |
   (tick/cross each column)
   - Fraction of SFRs with full vertical coverage

4. ARCHITECTURE QUALITY  (score 1–5 per criterion)
   | Criterion              | Score | Justification |
   |------------------------|-------|---------------|
   | Modularity             |       |               |
   | Separation of concerns |       |               |
   | Testability            |       |               |
   | Scalability            |       |               |
   | Safety architecture    |       |               |

5. CODE QUALITY SCORECARD  (score 1–5)
   | Criterion              | Score | Finding |
   |------------------------|-------|---------|
   | MISRA-C compliance     |       |         |
   | CERT-C compliance      |       |         |
   | Error handling         |       |         |
   | ISR safety             |       |         |
   | Memory safety          |       |         |
   | Documentation          |       |         |

6. SAFETY ANALYSIS DISPOSITION
   - FMEA items accepted vs. still open
   - Residual risks and mitigations confirmed
   - SSR-xxx safety requirements: are they all covered by tests?

7. TEST RESULTS SUMMARY
   | Test Level      | Total | Passed | Failed | Blocked | Coverage |
   |-----------------|-------|--------|--------|---------|----------|
   | Unit Tests      |       |        |        |         |          |
   | Integration     |       |        |        |         |          |
   | SW Qualification|       |        |        |         |          |
   | HW/SW Integ     |       |        |        |         |          |
   | System Valid    |       |        |        |         |          |

8. STATIC ANALYSIS STATUS
   - Zero Mandatory violations? (must be YES for GO)
   - Required violations: justified and waived?

9. OPEN ACTION ITEMS (must be resolved before release)
   | AI-ID | Priority | Owner | Description | Due |
   |-------|----------|-------|-------------|-----|

10. CERTIFICATION ARTEFACT CHECKLIST  (IEC 61508 / ISO 26262 / DO-178C)
    - [ ] SRS signed off
    - [ ] Architecture design reviewed
    - [ ] Code review records complete
    - [ ] Test reports with coverage metrics
    - [ ] FMEA / FTA accepted by safety manager
    - [ ] Traceability matrices verified end-to-end

11. FINAL VERDICT
    **GO** — all mandatory criteria met; list any open advisories
    **NO-GO** — list blocking issues with owner and resolution deadline

Sign-off block: Role | Name | Date | Signature\
"""


def run(context: dict) -> str:
    snippets = {k: v[:800] for k, v in context.items() if k != "task"}
    combined = "\n\n".join(
        f"=== {k.upper()} ===\n{v}" for k, v in snippets.items()
    )
    prompt = f"""\
Conduct the final V-Model Design Review for the embedded project below.
Consolidate all artefacts and deliver a Go / No-Go decision.

PROJECT: {context.get('task', '')}

ALL PIPELINE ARTEFACTS (excerpts):
{combined}
"""
    return call_agent(_ROLE, prompt)
