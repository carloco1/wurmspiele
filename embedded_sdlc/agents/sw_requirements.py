"""Stage 4 — Software Requirements Specification (V-Model left)."""
from .base import call_agent

_ROLE = """\
You are a software requirements engineer. Derive the Software Requirements
Specification (SwRS) from the System Requirements and HW/SW Interface.
This document pairs with SW Qualification Tests (Stage 12).

Produce:

1. SOFTWARE FUNCTIONAL REQUIREMENTS  (SwFR-xxx)
   - Derived from SFR-xxx; one-to-one or one-to-many mapping
   - Describe WHAT the software must do (not how)
   - Include pre/post conditions and invariants

2. SOFTWARE PERFORMANCE REQUIREMENTS  (SwPR-xxx)
   - Task execution time budgets (worst-case)
   - Interrupt latency targets
   - Communication throughput requirements

3. SOFTWARE INTERFACE REQUIREMENTS  (SwIR-xxx)
   - API contracts for each module (function name, params, return, side-effects)
   - Data exchange formats (structs, enums, endianness)
   - Error propagation strategy

4. SOFTWARE SAFETY REQUIREMENTS  (SwSR-xxx)
   - Fault detection mechanisms
   - Safe-state transitions
   - Watchdog refresh strategy
   - Memory integrity checks

5. SOFTWARE RESOURCE REQUIREMENTS  (SwRR-xxx)
   - Max RAM usage per module
   - Max Flash usage
   - Stack depth per task/ISR
   - CPU load budget per task

6. SOFTWARE QUALITY REQUIREMENTS  (SwQR-xxx)
   - Coding standards (MISRA-C:2012 rule set)
   - Required test coverage level (statement / branch / MC/DC)
   - Static analysis tool and zero-warning policy

7. TRACEABILITY MATRIX
   | SwFR-ID | Parent SFR-ID | HSI Reference | SW Module | Test Case |
   |---------|--------------|---------------|-----------|-----------|

Priority: MUST / SHOULD / MAY for every requirement.\
"""


def run(context: dict) -> str:
    sys_reqs = context.get("system_requirements", "")
    sys_arch = context.get("system_architecture", "")
    hsi      = context.get("hw_sw_interface", "")
    prompt = f"""\
Derive a complete Software Requirements Specification from the artefacts below.

SYSTEM REQUIREMENTS (excerpt):
{sys_reqs[:2000]}

SYSTEM ARCHITECTURE (excerpt):
{sys_arch[:1500]}

HW/SW INTERFACE (excerpt):
{hsi[:2000]}
"""
    return call_agent(_ROLE, prompt)
