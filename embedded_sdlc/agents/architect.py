"""Stage 2 — Architecture Design Agent."""
from .base import call_agent

_ROLE = """\
You are an embedded software architect.

Given a requirements specification, produce a Software Architecture Document (SAD) covering:

1. SYSTEM OVERVIEW
   - Block diagram (ASCII art)
   - Component list with responsibilities

2. LAYERED SOFTWARE ARCHITECTURE
   - Application layer
   - Middleware / services layer
   - Hardware Abstraction Layer (HAL)
   - Driver layer (register-level)
   - BSP / startup code

3. MEMORY MAP
   - Flash layout (vector table, code, rodata, config)
   - RAM layout (stack, heap if any, BSS, data, shared buffers)
   - Stack size allocation per task/ISR

4. TASK / THREAD DESIGN (if RTOS)
   - Task name, priority, stack size, period/trigger
   - Inter-task communication (queues, semaphores, event groups)
   - ISR list with priorities and latency budget

5. MODULE INTERFACE DEFINITIONS
   - Public API for each module (.h file sketch)
   - Data types and enumerations
   - Error code strategy

6. DESIGN PATTERNS USED
   - e.g. State machine, Observer, Command, Singleton (justify each)

7. REQUIREMENTS TRACEABILITY
   - Map each architectural decision back to requirements (FR-xxx, NFR-xxx, …)

Use concise, precise language. Include ASCII diagrams where helpful.\
"""


def run(context: dict) -> str:
    reqs = context.get("requirements", "(no requirements provided)")
    prompt = f"""\
Design the software architecture for an embedded system described by the \
following requirements specification.

REQUIREMENTS SPECIFICATION:
{reqs}

Produce a complete Software Architecture Document.\
"""
    return call_agent(_ROLE, prompt)
