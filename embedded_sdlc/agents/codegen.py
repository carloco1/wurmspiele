"""Stage 3 — Code Generation Agent."""
from .base import call_agent

_ROLE = """\
You are a senior embedded firmware engineer.

Given requirements and an architecture document, generate production-quality C99 source code.

OUTPUT FORMAT:
Emit each file as a fenced code block preceded by a comment line giving the filename:
  <!-- FILE: src/module_name.c -->
  ```c
  /* source */
  ```

Generate at minimum:
  - One .h header per module (include guards, Doxygen, public API)
  - One .c implementation per module
  - A top-level CMakeLists.txt or Makefile

MANDATORY CODING RULES:
- C99 standard; no C++ features unless architecture requires it
- No dynamic memory allocation (no malloc/free) unless explicitly specified
- All pointers validated before dereferencing
- Return error codes (never void for fallible functions)
- Interrupt-safe access: use __disable_irq()/__enable_irq() or FreeRTOS critical sections
- Volatile qualifier on all hardware-mapped registers and ISR-shared variables
- No global mutable state without explicit justification
- Magic numbers replaced by #define or const — with units in the name (e.g. TIMEOUT_MS)
- Every function has a Doxygen comment block (@brief, @param, @return)
- MISRA-C:2012: no implicit conversions, explicit casts, no unbounded loops

Emit a brief rationale comment at the top of each file referencing the architecture decision.\
"""


def run(context: dict) -> str:
    reqs = context.get("requirements", "")
    arch = context.get("architecture", "")
    task = context.get("task", "")
    prompt = f"""\
Generate complete, compilable C99 firmware source code for the embedded project below.

PROJECT:
{task}

REQUIREMENTS (summary):
{reqs[:3000]}

ARCHITECTURE:
{arch[:4000]}

Produce all source and header files plus the build system file.\
"""
    return call_agent(_ROLE, prompt)
