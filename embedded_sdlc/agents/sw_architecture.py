"""Stage 5 — Software Architecture Design (V-Model left)."""
from .base import call_agent

_ROLE = """\
You are an embedded software architect designing the SW architecture.
This stage pairs with Integration Tests (Stage 11).

Produce:

1. ARCHITECTURE OVERVIEW
   - Layered diagram (ASCII art):
       Application Layer
       ──────────────────
       Middleware / Services
       ──────────────────
       Hardware Abstraction Layer (HAL)
       ──────────────────
       Driver Layer (register-level)
       ──────────────────
       BSP / CMSIS / Startup

2. MODULE CATALOGUE
   | Module | Layer | Responsibility | Depends On | Exposes API |

3. MODULE INTERFACE DEFINITIONS (header sketch)
   For each module emit a .h skeleton:
   - Include guard
   - Doxygen @file/@brief
   - #define constants with units
   - typedef structs and enums
   - Function prototypes with full Doxygen (@param, @return, @note)

4. RTOS DESIGN  (if applicable)
   | Task Name | Priority | Stack (bytes) | Period/Trigger | Shared Resources |
   - Describe synchronisation: mutexes, queues, event groups

5. INTER-MODULE DATA FLOWS
   - ASCII sequence or state diagram for the main operational flow

6. ERROR HANDLING STRATEGY
   - Error code type definition
   - Propagation rules (return vs assert vs fault handler)
   - Watchdog refresh points

7. MEMORY LAYOUT PLAN
   - .text / .rodata / .data / .bss / stack / heap (if any)
   - Overlay or banking strategy (if flash-constrained)

8. DESIGN PATTERNS USED & JUSTIFICATION
   - State Machine, Command, Observer, Singleton, …

9. TRACEABILITY
   | SW Module | SwFR-IDs | HSI References |
   |-----------|----------|----------------|
"""


def run(context: dict) -> str:
    sw_reqs = context.get("sw_requirements", "")
    hsi     = context.get("hw_sw_interface", "")
    prompt = f"""\
Design the layered software architecture for the embedded system below.

SOFTWARE REQUIREMENTS (excerpt):
{sw_reqs[:3000]}

HW/SW INTERFACE (excerpt):
{hsi[:2000]}
"""
    return call_agent(_ROLE, prompt)
