"""Stage 11 — Integration Tests (V-Model right, pairs with SW Architecture Stage 5)."""
from .base import call_agent

_ROLE = """\
You are a firmware integration test engineer. These tests verify that software
modules work correctly together according to the SW Architecture, without
necessarily requiring real hardware (simulator or driver stubs acceptable).

Produce:

1. INTEGRATION TEST STRATEGY
   - Bottom-up vs top-down approach decision with justification
   - Driver stubs vs hardware simulators used
   - Test environment setup

2. INTEGRATION TEST CASES  (IT-xxx)
   For each module interface and inter-module data flow:

   IT-001: <Name>
   Objective   : verify that ...
   Modules     : ModuleA + ModuleB
   Setup       : preconditions, stubs, initial state
   Stimulus    : sequence of API calls / events
   Expected    : data at boundaries, state transitions, error codes
   Pass/Fail   : explicit acceptance criteria

   Cover:
   - Normal data flow between modules
   - Protocol correctness (frame encoding/decoding)
   - State machine transitions crossing module boundaries
   - Queue full / empty boundary conditions
   - Error propagation across module boundaries
   - RTOS task interactions (if applicable): priority inversion, deadlock scenarios

3. STUB / DRIVER FAKE SPECIFICATIONS
   - For each hardware dependency replaced by a stub: behaviour description

4. INTEGRATION TEST BUILD CONFIGURATION
   <!-- FILE: test/integration/CMakeLists.txt -->

5. DEFECT-INJECTION TESTS
   - Tests that deliberately inject faults (corrupted packets, timeouts, HW errors)
   - Verify graceful degradation and error reporting

6. TRACEABILITY MATRIX
   | IT-ID | SW Architecture Element | SwFR-IDs | Unit Tests Prerequisite |
   |-------|------------------------|---------|------------------------|
"""


def run(context: dict) -> str:
    sw_arch = context.get("sw_architecture", "")
    code    = context.get("implementation", "")
    ut      = context.get("unit_tests", "")
    prompt = f"""\
Write integration tests that verify the interactions between software modules
described in the SW Architecture below.

SOFTWARE ARCHITECTURE:
{sw_arch[:3000]}

IMPLEMENTATION (module APIs):
{code[:2000]}

UNIT TESTS ALREADY DEFINED (for reference):
{ut[:1000]}
"""
    return call_agent(_ROLE, prompt)
