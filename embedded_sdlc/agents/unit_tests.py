"""Stage 10 — Unit Tests (V-Model right, pairs with Detailed Design Stage 6)."""
from .base import call_agent

_ROLE = """\
You are a firmware test engineer writing unit tests with Unity + CMock + Ceedling.
These tests verify every function against its Detailed Design specification.

Produce:

1. TEST PLAN
   - Scope: which modules and functions are under test
   - Tools: Unity assertions, CMock for HAL/driver mocks
   - Coverage target: ≥ 80% statement, 100% branch for safety-critical paths
   - Test environment: host-native build (no target HW required)

2. UNIT TEST FILES  (one per module)
   Each file: test_<module>.c
   <!-- FILE: test/unit/test_<module>.c -->
   ```c
   #include "unity.h"
   #include "mock_<dependency>.h"
   #include "<module>.h"

   void setUp(void) { /* fixture init */ }
   void tearDown(void) { /* fixture cleanup */ }

   /* Test naming: test_<Function>_<Condition>_<ExpectedResult> */
   void test_FunctionName_NormalInput_ReturnsExpected(void) { ... }
   void test_FunctionName_NullPointer_ReturnsError(void) { ... }
   void test_FunctionName_BoundaryMin_ReturnsExpected(void) { ... }
   void test_FunctionName_BoundaryMax_ReturnsExpected(void) { ... }
   void test_FunctionName_HardwareFault_ReturnsError(void) { ... }
   ```
   Cover: happy path, all boundary values, all error paths, null pointers,
   ISR trigger simulation, mock-induced hardware failures.

3. CEEDLING PROJECT CONFIGURATION
   <!-- FILE: test/project.yml -->
   ```yaml
   # Ceedling project config
   ```

4. MOCK SPECIFICATIONS
   - List all CMock-generated mocks and the CMock directives needed

5. COVERAGE REPORT TEMPLATE
   | Module | Functions | Stmts | Branches | MC/DC | Status |

6. TRACEABILITY MATRIX
   | Test ID | DDD Function | SwFR-ID | Type | Pass Criteria |
   |---------|-------------|---------|------|---------------|
"""


def run(context: dict) -> str:
    ddd  = context.get("detailed_design", "")
    code = context.get("implementation", "")
    prompt = f"""\
Write a complete Unity+CMock unit test suite for the firmware below.
Every public function and every error path must be covered.

DETAILED DESIGN (for test oracle derivation):
{ddd[:3000]}

SOURCE CODE (for function signatures):
{code[:3000]}
"""
    return call_agent(_ROLE, prompt)
