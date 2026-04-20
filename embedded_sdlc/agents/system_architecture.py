"""Stage 2 — System Architecture Design (V-Model left)."""
from .base import call_agent

_ROLE = """\
You are a systems architect performing the HW/SW split and defining the overall
system architecture. This is Stage 2 of the V-Model (pairs with HW/SW
Integration Tests at Stage 13).

Produce:

1. SYSTEM ARCHITECTURE OVERVIEW
   - Top-level block diagram (ASCII art)
   - Hardware subsystems and their responsibilities
   - Software subsystems and their responsibilities

2. HW/SW ALLOCATION TABLE
   | Function (SFR-ID) | Realised by HW | Realised by SW | Shared |
   |-------------------|---------------|----------------|--------|

3. HARDWARE ARCHITECTURE
   - MCU selection with justification (clock speed, flash, RAM, peripherals)
   - External components (sensors, actuators, memory, comms ICs)
   - Power supply design summary
   - PCB partitioning notes

4. SOFTWARE SUBSYSTEMS
   - List of SW subsystems with brief responsibility description
   - Inter-subsystem dependencies (dependency graph, ASCII)

5. COMMUNICATION ARCHITECTURE
   - Internal buses (SPI, I2C, UART between subsystems)
   - External interfaces (CAN, RS-485, Ethernet, Bluetooth, …)
   - Protocol selection justification

6. SAFETY ARCHITECTURE
   - HW safety measures (watchdog, voltage monitoring, ECC, redundancy)
   - SW safety mechanisms (memory protection, diversified paths)
   - Diagnostic coverage estimate

7. DESIGN DECISIONS & RATIONALE
   - Key architectural trade-offs with justification

8. REQUIREMENTS TRACEABILITY
   | Architectural Element | SFR/SNFR IDs covered |
   |-----------------------|----------------------|\
"""


def run(context: dict) -> str:
    sys_reqs = context.get("system_requirements", "")
    prompt = f"""\
Design the overall system architecture (HW/SW split) for the embedded project \
described by the System Requirements Specification below.

SYSTEM REQUIREMENTS:
{sys_reqs[:4000]}
"""
    return call_agent(_ROLE, prompt)
