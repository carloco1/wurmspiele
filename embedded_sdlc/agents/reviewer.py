"""Stage 6 — Final Code Review & Sign-off Agent."""
from .base import call_agent

_ROLE = """\
You are a principal embedded systems engineer performing the final design review.

Consolidate all SDLC artefacts and produce a Design Review Report covering:

1. EXECUTIVE SUMMARY
   - Go / No-Go recommendation
   - Key risks

2. REQUIREMENTS COVERAGE
   - Fraction of requirements addressed by the architecture and code
   - Any gaps or ambiguities found

3. ARCHITECTURE QUALITY
   - Appropriateness of design patterns chosen
   - Scalability and maintainability
   - Any architectural risks

4. CODE QUALITY SCORECARD
   | Criterion              | Score (1–5) | Comment |
   |------------------------|-------------|---------|
   | MISRA compliance       |             |         |
   | Naming conventions     |             |         |
   | Error handling         |             |         |
   | ISR safety             |             |         |
   | Memory safety          |             |         |
   | Portability            |             |         |
   | Testability            |             |         |
   | Documentation          |             |         |

5. STATIC ANALYSIS FINDINGS DISPOSITION
   - Which findings are accepted with justification
   - Which must be fixed before release

6. TEST COVERAGE ASSESSMENT
   - Is coverage adequate for the SIL/ASIL level?
   - Missing test scenarios

7. ACTION ITEMS (before release)
   | ID | Priority | Owner | Description | Due |
   |----|----------|-------|-------------|-----|

8. LESSONS LEARNED & RECOMMENDATIONS
   - What should be improved in the next iteration

Provide a definitive Go / No-Go verdict with rationale.\
"""


def run(context: dict) -> str:
    task     = context.get("task", "")
    reqs     = context.get("requirements", "")
    arch     = context.get("architecture", "")
    code     = context.get("codegen", "")
    analysis = context.get("analysis", "")
    tests    = context.get("testgen", "")

    prompt = f"""\
Perform the final design review for the embedded firmware project below.

PROJECT:
{task}

REQUIREMENTS SPECIFICATION:
{reqs[:1500]}

ARCHITECTURE DOCUMENT:
{arch[:1500]}

GENERATED CODE (excerpt):
{code[:2000]}

STATIC ANALYSIS REPORT:
{analysis[:2000]}

TEST SUITE SUMMARY:
{tests[:1500]}

Produce a complete Design Review Report with a Go / No-Go decision.\
"""
    return call_agent(_ROLE, prompt)
