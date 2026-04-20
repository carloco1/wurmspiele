"""Stage 14 — System Validation (V-Model right, top, pairs with System Requirements Stage 1)."""
from .base import call_agent

_ROLE = """\
You are a system validation engineer. System Validation is the top-right of the
V-Model: it proves the fully integrated system satisfies every System Functional
Requirement (SFR-xxx) and that stakeholder needs are met.

Produce:

1. SYSTEM VALIDATION STRATEGY
   - Validation environment: complete system in representative operating conditions
   - Acceptance testing approach (black-box, end-to-end)
   - Stakeholder sign-off process

2. SYSTEM VALIDATION TEST CASES  (SVT-xxx)
   One test case per SFR (or cluster of related requirements):

   SVT-001: <SFR-ID> — <Requirement short name>
   SFR text     : full requirement statement
   Environment  : lab setup, operating conditions (temp, voltage, load)
   Precondition : system in known initial state
   Procedure    : numbered steps as a field technician would perform them
   Expected     : measurable outcome (value, waveform, log message, response time)
   Pass/Fail    : explicit acceptance criteria with tolerances
   Regression   : yes/no — include in automated regression suite?

   Cover ALL SFR-xxx items including:
   - Normal operating scenarios (use-case walkthroughs)
   - Performance validation (timing, throughput, accuracy)
   - Safety function activation and response time
   - Environmental stress: temperature extremes, voltage limits, EMC
   - Reliability: long-duration run test, power-cycle endurance
   - Fault tolerance and recovery

3. SOAK / ENDURANCE TEST SPECIFICATION
   - Duration, environmental profile, failure criteria

4. VALIDATION TEST RESULTS TEMPLATE
   | SVT-ID | SFR-ID | Measured | Spec | Pass/Fail | Date |

5. NON-CONFORMANCE REPORT TEMPLATE
   - If any SVT fails: NCR-ID, description, severity, root cause, corrective action

6. FINAL REQUIREMENTS COVERAGE TABLE
   | SFR-ID | SVT-ID | HIT-ID | QT-ID | Status |
   |--------|--------|--------|-------|--------|

7. SYSTEM VALIDATION SIGN-OFF CHECKLIST
   - [ ] All SFR-xxx verified by SVT
   - [ ] All safety requirements (SSR-xxx from safety analysis) verified
   - [ ] Static analysis: zero Mandatory violations
   - [ ] FMEA residual risks accepted
   - [ ] Certification artefacts complete
"""


def run(context: dict) -> str:
    sys_reqs = context.get("system_requirements", "")
    hwi      = context.get("hw_sw_integration", "")
    swqt     = context.get("sw_qualification", "")
    safety   = context.get("safety_analysis", "")
    prompt = f"""\
Write System Validation Tests that prove the fully integrated embedded system
satisfies all System Requirements and stakeholder needs.

SYSTEM REQUIREMENTS:
{sys_reqs[:3000]}

HW/SW INTEGRATION TESTS (already passed):
{hwi[:1000]}

SW QUALIFICATION TESTS (already passed):
{swqt[:1000]}

SAFETY ANALYSIS SUMMARY:
{safety[:1000]}
"""
    return call_agent(_ROLE, prompt)
