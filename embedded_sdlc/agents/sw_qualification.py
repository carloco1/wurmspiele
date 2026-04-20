"""Stage 12 — SW Qualification Tests (V-Model right, pairs with SW Requirements Stage 4)."""
from .base import call_agent

_ROLE = """\
You are a software verification engineer writing SW Qualification Tests (SWQT).
These tests prove that the software satisfies every Software Requirement (SwFR-xxx).
They run on target hardware or a high-fidelity simulation.

Produce:

1. SWQT STRATEGY
   - Test environment: target HW, JTAG probe, logic analyser, oscilloscope
   - Test automation approach (pytest + pyserial / LAUTERBACH / Segger RTT)
   - Regression policy

2. QUALIFICATION TEST CASES  (QT-xxx)
   One test case per SwFR (or group of closely related requirements):

   QT-001: <Requirement ID> — <Requirement Name>
   Requirement : SwFR-xxx full text
   Environment : target HW + tools needed
   Precondition: system state, configuration, calibration
   Procedure   : numbered steps (stimulate → observe → verify)
   Expected    : measurable acceptance criteria (value ± tolerance, timing)
   Pass/Fail   : explicit GO / NO-GO criteria
   MISRA note  : static analysis must show zero Mandatory violations before running

   Cover ALL SwFR-xxx items. Include:
   - Nominal operation
   - Boundary/limit values
   - Error handling and fault recovery
   - Timing / latency measurements

3. AUTOMATED TEST SCRIPTS (Python + pytest)
   <!-- FILE: test/qualification/test_swfr_xxx.py -->
   ```python
   import pytest
   # target communication stub (replace with actual serial/JTAG interface)
   ```

4. TEST ENVIRONMENT SETUP
   - Hardware configuration diagram (ASCII)
   - Required test equipment list
   - Firmware build configuration for testing

5. PASS/FAIL CRITERIA SUMMARY
   | QT-ID | SwFR-ID | Criterion | Tool |
   |-------|---------|-----------|------|

6. TRACEABILITY MATRIX
   | QT-ID | SwFR-ID | IT-IDs passed | Static Analysis passed |
   |-------|---------|--------------|----------------------|
"""


def run(context: dict) -> str:
    sw_reqs = context.get("sw_requirements", "")
    code    = context.get("implementation", "")
    it      = context.get("integration_tests", "")
    sa      = context.get("static_analysis", "")
    prompt = f"""\
Write SW Qualification Tests to prove every software requirement is met.

SOFTWARE REQUIREMENTS:
{sw_reqs[:3000]}

INTEGRATION TESTS (already defined, for gap analysis):
{it[:1000]}

STATIC ANALYSIS SUMMARY:
{sa[:500]}

SOURCE CODE (for API reference):
{code[:1500]}
"""
    return call_agent(_ROLE, prompt)
