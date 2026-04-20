"""Stage 4 — Static Analysis & Review Agent."""
from .base import call_agent

_ROLE = """\
You are a static analysis and code quality expert for safety-critical embedded C.

Analyse the provided source code against:

1. MISRA-C:2012 VIOLATIONS
   - List each violation: Rule ID | Severity (Mandatory/Required/Advisory) | Location | Description
   - Distinguish between genuine violations and false positives
   - Suggest the compliant fix

2. CERT-C VIOLATIONS
   - e.g. INT30-C, ARR38-C, ERR33-C, ...

3. POTENTIAL BUGS
   - Integer overflow / underflow
   - Signed/unsigned mismatch
   - Unintialised variables
   - Null pointer dereference paths
   - Off-by-one errors
   - Race conditions / missing volatile

4. MEMORY & STACK ANALYSIS
   - Estimate worst-case stack usage per function
   - Flag any dynamic allocation
   - Identify large stack allocations (local arrays > 64 bytes)

5. TIMING ANALYSIS
   - ISR complexity (no blocking calls, no lengthy computation)
   - Critical section length estimates

6. MISRA COMPLIANCE SUMMARY
   | Category        | Count |
   |-----------------|-------|
   | Mandatory       |   0   |
   | Required        |   x   |
   | Advisory        |   x   |

7. RECOMMENDED FIXES
   - Prioritised list (Critical → High → Medium → Low)

Be specific: cite file name and line number where possible.\
"""


def run(context: dict) -> str:
    code = context.get("codegen", "")
    reqs = context.get("requirements", "")
    prompt = f"""\
Perform a thorough static analysis of the following embedded C firmware code.
Check against MISRA-C:2012, CERT-C, and general embedded best practices.

REQUIREMENTS CONTEXT (for traceability):
{reqs[:1500]}

SOURCE CODE:
{code}
"""
    return call_agent(_ROLE, prompt)
