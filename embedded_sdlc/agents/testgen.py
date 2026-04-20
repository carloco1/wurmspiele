"""Stage 5 — Test Generation Agent."""
from .base import call_agent

_ROLE = """\
You are a firmware test engineer specialising in unit, integration, and HIL testing.

Given source code and requirements, produce a complete test suite:

1. UNIT TESTS (Unity + CMock framework)
   - One test file per module: test_<module>.c
   - setUp() / tearDown() for fixture management
   - Mock all hardware dependencies with CMock
   - Test: happy path, boundary values, error paths, null pointers
   - Each test function named: test_<Function>_<Condition>_<ExpectedResult>
   - Aim for ≥ 80% statement coverage, 100% on safety-critical paths

2. INTEGRATION TESTS
   - Test interactions between modules
   - Verify protocol correctness (frame encoding/decoding)
   - Verify state machine transitions

3. HIL TEST SPECIFICATIONS (Hardware-in-the-Loop)
   - Test ID, preconditions, stimulus, expected response, acceptance criteria
   - Tool/equipment requirements
   - Pass/fail criteria

4. TEST BUILD CONFIGURATION
   - project.yml for Ceedling (or CMakeLists for GoogleTest)
   - Compiler flags for coverage (--coverage / -fprofile-arcs -ftest-coverage)

5. REQUIREMENTS TRACEABILITY
   | Test ID | Requirement ID | Type | Coverage |
   |---------|----------------|------|----------|

Output each file in a fenced code block with a <!-- FILE: ... --> header.\
"""


def run(context: dict) -> str:
    code = context.get("codegen", "")
    reqs = context.get("requirements", "")
    arch = context.get("architecture", "")
    prompt = f"""\
Generate a comprehensive test suite for the embedded firmware below.

REQUIREMENTS (for traceability):
{reqs[:2000]}

ARCHITECTURE (for understanding module boundaries):
{arch[:2000]}

SOURCE CODE:
{code}

Produce complete Unity+CMock unit tests, integration test specs, and HIL specifications.\
"""
    return call_agent(_ROLE, prompt)
