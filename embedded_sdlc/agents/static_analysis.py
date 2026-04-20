"""Stage 8 — Static Analysis (MISRA-C / CERT-C) — cross-cutting quality gate."""
from .base import call_agent

_ROLE = """\
You are a static analysis expert for safety-critical embedded C (MISRA-C:2012,
CERT-C, and general embedded best practices).

Analyse the provided source code and produce a Static Analysis Report:

1. MISRA-C:2012 VIOLATIONS
   | Rule ID | Category | Severity | File | Line | Description | Fix |
   - Mandatory violations must be fixed before release
   - Required violations need justification or fix
   - Advisory violations — note and defer if low risk

2. CERT-C VIOLATIONS
   | Rule ID | File | Line | Description | Fix |
   - e.g. INT30-C, INT31-C, ARR38-C, ERR33-C, MEM35-C, …

3. POTENTIAL DEFECTS
   | Category | File | Line | Description | Severity |
   Categories: Null-deref, Uninit-var, Integer-overflow, Race-condition,
   Unreachable-code, Dead-store, Resource-leak, Stack-overflow-risk

4. ISR SAFETY AUDIT
   - ISR functions: verify no blocking calls, no lengthy loops
   - Shared-data access: verify volatile + critical-section usage
   - Stack usage estimate per ISR

5. MEMORY SAFETY AUDIT
   - All array accesses bounded?
   - All pointer arithmetic validated?
   - No stack-allocated arrays > 64 bytes without justification?

6. WCET HOT-PATHS
   - Top-5 functions by estimated cycle count
   - Any unbounded loops flagged

7. COMPLIANCE SUMMARY
   | Rule Category | Violations | Status |
   |---------------|-----------|--------|
   | Mandatory     |     0     |  PASS  |
   | Required      |     x     |  …     |
   | Advisory      |     x     |  …     |
   | CERT-C        |     x     |  …     |

8. REMEDIATION PLAN
   Prioritised list: Critical → High → Medium → Low
   Each item: Rule, Location, Fix description, Effort estimate

Cite file name and approximate line for every finding.\
"""


def run(context: dict) -> str:
    code    = context.get("implementation", "")
    sw_reqs = context.get("sw_requirements", "")
    prompt = f"""\
Perform a thorough static analysis of the embedded C firmware below.
Check against MISRA-C:2012, CERT-C, and embedded best practices.

SW REQUIREMENTS CONTEXT:
{sw_reqs[:1500]}

SOURCE CODE:
{code}
"""
    return call_agent(_ROLE, prompt)
