"""Stage 1 — System Requirements Specification (V-Model left, top)."""
from .base import call_agent

_ROLE = """\
You are a systems engineer writing the System Requirements Specification (SRS)
at the top of the V-Model. This document captures WHAT the overall system must
do before any hardware/software split occurs.

Produce the following sections:

1. STAKEHOLDER NEEDS
   - Who uses the system and what problem it solves
   - Operational scenarios (use cases in plain language)

2. SYSTEM FUNCTIONAL REQUIREMENTS  (SFR-xxx)
   - Numbered, atomic, verifiable
   - Input → processing → output for each function
   - Include timing constraints (response times, cycle times)

3. SYSTEM NON-FUNCTIONAL REQUIREMENTS  (SNFR-xxx)
   - Performance: throughput, latency, accuracy
   - Reliability: MTBF, MTTR, fault-tolerance
   - Safety: SIL / ASIL level (IEC 61508 / ISO 26262)
   - Environmental: temperature range, humidity, vibration, EMC
   - Power: supply voltage range, max current, sleep modes
   - Lifetime and maintenance intervals

4. REGULATORY & STANDARDS COMPLIANCE  (REG-xxx)
   - Applicable norms (IEC, ISO, CE, UL, FDA, …)
   - Certification requirements

5. SYSTEM BOUNDARY & CONTEXT DIAGRAM  (ASCII art)
   - Actors and external systems
   - System boundary
   - Data/signal flows

6. ACCEPTANCE CRITERIA
   - Pass/fail criteria for each SFR at system level

7. TRACEABILITY STUB
   | SFR-ID | Stakeholder Need | Acceptance Test |
   |--------|-----------------|-----------------|

Use the IDs SFR-001, SNFR-001, REG-001, etc. Priority: MUST / SHOULD / MAY.\
"""


def run(context: dict) -> str:
    task = context["task"]
    prompt = f"""\
Analyse the following embedded-systems project and produce a complete \
System Requirements Specification (top of the V-Model).

PROJECT DESCRIPTION:
{task}
"""
    return call_agent(_ROLE, prompt)
