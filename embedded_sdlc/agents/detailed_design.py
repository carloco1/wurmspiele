"""Stage 6 — Detailed Design (V-Model left, bottom)."""
from .base import call_agent

_ROLE = """\
You are a firmware engineer writing the Detailed Design Document (DDD).
This is the lowest level design before coding and pairs with Unit Tests (Stage 10).

For EVERY module identified in the Software Architecture, produce:

1. MODULE DETAILED DESIGN
   a) PURPOSE & SCOPE
   b) STATE MACHINE (if applicable)
      - ASCII state diagram
      - State table: State × Event → Next State + Action
   c) ALGORITHMS & DATA STRUCTURES
      - Pseudocode or flowchart (ASCII) for every non-trivial function
      - Complexity analysis (time + space) for algorithms with real-time impact
   d) INTERNAL DATA LAYOUT
      - All static/global variables with type, initial value, and access rules
      - Ring buffers, queues, lookup tables — size and index calculations
   e) FUNCTION-LEVEL DESIGN
      For each public AND private function:
      | Name | Inputs | Outputs | Side-effects | Pre-conditions | Post-conditions |
   f) TIMING & RESOURCE USAGE
      - Estimated worst-case execution time (WCET) per function
      - Stack frame size estimate

2. CROSS-MODULE INTERACTIONS
   - Sequence diagrams (ASCII) for the 3 most critical use-cases

3. CONFIGURATION & COMPILE-TIME PARAMETERS
   - All #define tuning knobs with valid range and default

4. UNIT TEST HOOKS
   - Which internal functions need test-seam access (extern in test builds)
   - Fault injection points

5. TRACEABILITY
   | Function | SwFR-ID | DDD-ID |
   |----------|---------|--------|
"""


def run(context: dict) -> str:
    sw_reqs = context.get("sw_requirements", "")
    sw_arch = context.get("sw_architecture", "")
    prompt = f"""\
Write the Detailed Design Document for every module in the software architecture below.

SOFTWARE REQUIREMENTS (excerpt):
{sw_reqs[:2000]}

SOFTWARE ARCHITECTURE:
{sw_arch[:4000]}
"""
    return call_agent(_ROLE, prompt)
