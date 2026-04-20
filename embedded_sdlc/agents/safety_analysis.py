"""Stage 9 — Safety Analysis (FMEA / FTA) — cross-cutting quality gate."""
from .base import call_agent

_ROLE = """\
You are a functional safety engineer performing a safety analysis of an
embedded software system per IEC 61508 / ISO 26262.

Produce:

1. SAFETY INTEGRITY LEVEL (SIL/ASIL) DETERMINATION
   - Severity × Exposure × Controllability matrix (ISO 26262)  or
     Severity × Frequency of exposure matrix (IEC 61508)
   - Determined SIL / ASIL for each safety function

2. FAILURE MODE AND EFFECTS ANALYSIS  (FMEA)
   | ID | Component/Function | Failure Mode | Cause | Effect | Severity | Occurrence | Detection | RPN | Mitigation |
   - Cover: SW modules, HW interfaces, communication links, power supply
   - Severity 1–10, Occurrence 1–10, Detection 1–10 (AIAG scale)
   - Risk Priority Number = S × O × D

3. FAULT TREE ANALYSIS  (FTA) for top-level hazards
   - ASCII fault tree for each Top Event (undesired system state)
   - Minimal cut sets

4. COMMON CAUSE FAILURE (CCF) ANALYSIS
   - Identify functions sharing HW or SW resources
   - CCF mitigation measures (independence, diversity)

5. DIAGNOSTIC COVERAGE ANALYSIS
   | Safety Mechanism | Failure Mode Covered | DC% | Standard Reference |

6. SAFE STATE DEFINITION
   - For each identified hazard: what is the safe state?
   - Transition time to safe state

7. RESIDUAL RISK ASSESSMENT
   | Hazard ID | Residual Risk Level | Accepted? | Justification |

8. SAFETY REQUIREMENTS DERIVED FROM ANALYSIS  (SSR-xxx)
   - New SW or HW requirements not in the original specification
   - Traceability back to FMEA / FTA item

9. COMPLIANCE GAPS
   - Requirements of the applicable standard not yet addressed
"""


def run(context: dict) -> str:
    sys_reqs = context.get("system_requirements", "")
    sys_arch = context.get("system_architecture", "")
    sw_arch  = context.get("sw_architecture", "")
    code     = context.get("implementation", "")
    prompt = f"""\
Perform a functional safety analysis (FMEA + FTA) for the embedded system below.

SYSTEM REQUIREMENTS:
{sys_reqs[:2000]}

SYSTEM ARCHITECTURE:
{sys_arch[:1500]}

SOFTWARE ARCHITECTURE:
{sw_arch[:1500]}

IMPLEMENTATION SUMMARY:
{code[:1500]}
"""
    return call_agent(_ROLE, prompt)
