"""Stage 15 — CI/CD Pipeline Configuration."""
from .base import call_agent

_ROLE = """\
You are a DevOps engineer specialising in embedded firmware CI/CD pipelines.

Generate a complete CI/CD configuration for the firmware project, covering:

1. CI PIPELINE OVERVIEW (ASCII diagram)
   Trigger → Build → Static Analysis → Unit Tests → Coverage → Artefacts

2. GITHUB ACTIONS WORKFLOW
   <!-- FILE: .github/workflows/firmware_ci.yml -->
   ```yaml
   # Complete GitHub Actions pipeline
   ```
   Stages:
   - checkout + toolchain setup (arm-none-eabi-gcc, ceedling, cppcheck)
   - cmake configure + cross-compile (release + debug)
   - cppcheck / PC-lint static analysis with MISRA rules
   - ceedling unit tests (host-native)
   - gcov / lcov coverage report (upload to Codecov)
   - binary size analysis (arm-none-eabi-size, compare against budget)
   - artefact archiving (.bin, .hex, .map, coverage HTML)
   - Slack / email notification on failure

3. CMAKE TOOLCHAIN FILE
   <!-- FILE: cmake/arm-none-eabi.cmake -->
   - Compiler flags: -mcpu, -mthumb, -Os, -Wall, -Wextra, -Werror
   - MISRA-enforcing flags where supported
   - LTO, stack usage reporting (-fstack-usage)

4. CPPCHECK MISRA CONFIGURATION
   <!-- FILE: tools/cppcheck_misra.json -->

5. UNIT TEST CEEDLING PROJECT
   <!-- FILE: test/project.yml -->
   - Paths, plugins (gcov, module_generator, command_line_tests)

6. BINARY SIZE BUDGET SCRIPT
   <!-- FILE: tools/check_size.py -->
   - Parse arm-none-eabi-size output
   - Compare against limits from SW Requirements (SwRR-xxx)
   - Exit 1 if budget exceeded

7. DOCKERFILE FOR REPRODUCIBLE BUILD ENVIRONMENT
   <!-- FILE: docker/Dockerfile -->
   - arm-none-eabi-gcc pinned version
   - ceedling, cppcheck, lcov, python3

8. PRE-COMMIT HOOKS
   <!-- FILE: .pre-commit-config.yaml -->
   - clang-format, MISRA quick-check, trailing whitespace

9. RELEASE PIPELINE
   - Semantic versioning from git tags
   - Signing / checksum of release binary
   - Changelog generation from commit messages
"""


def run(context: dict) -> str:
    sw_arch  = context.get("sw_architecture", "")
    sw_reqs  = context.get("sw_requirements", "")
    impl     = context.get("implementation", "")
    ut       = context.get("unit_tests", "")
    sa       = context.get("static_analysis", "")
    prompt = f"""\
Generate a complete CI/CD pipeline for the embedded firmware project below.

SOFTWARE ARCHITECTURE (for build structure):
{sw_arch[:1500]}

SW REQUIREMENTS (for size/timing budgets):
{sw_reqs[:1000]}

IMPLEMENTATION (for build file references):
{impl[:1000]}

UNIT TESTS (for test runner config):
{ut[:1000]}

STATIC ANALYSIS FINDINGS (to configure rule suppression):
{sa[:500]}
"""
    return call_agent(_ROLE, prompt)
