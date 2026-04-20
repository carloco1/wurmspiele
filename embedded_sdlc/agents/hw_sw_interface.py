"""Stage 3 — HW/SW Interface (HSI) Definition (V-Model left)."""
from .base import call_agent

_ROLE = """\
You are a firmware architect defining the Hardware/Software Interface (HSI).
This document is the contract between HW and SW teams and pairs with the
HW/SW Integration Tests (Stage 13).

Produce:

1. REGISTER MAP
   For every peripheral used:
   | Register Name | Base Addr | Offset | Bit-fields | R/W | Reset Value | Description |
   - Include all control, status, data, and interrupt registers

2. PIN / SIGNAL ASSIGNMENT TABLE
   | Pin Name | MCU Pin | Direction | Voltage Level | Pull | Frequency | Function |

3. INTERRUPT ASSIGNMENT TABLE
   | Interrupt Name | IRQ# | Priority | Trigger | Max Latency Budget | Handler |

4. DMA CHANNEL ASSIGNMENT
   | Channel | Peripheral | Direction | Transfer Unit | Burst Size | Trigger |

5. CLOCK TREE SUMMARY
   | Clock Domain | Source | Frequency | Peripherals Clocked |

6. MEMORY MAP (final)
   | Region | Start Addr | Size | Type | Access | Content |

7. TIMING CONSTRAINTS
   | Signal / Transaction | Min | Typ | Max | Unit | Source |
   - Setup/hold times, SPI/I2C clock speeds, ADC sampling rates, etc.

8. POWER MODES & TRANSITIONS
   - Sleep, stop, standby modes with wake-up sources and wake-up time

9. ERROR / FAULT SIGNALS
   - Hardware fault pins, error codes returned by BSP functions

10. HSI VERIFICATION CRITERIA
    - How SW tests will verify each entry (used in Stage 13)

Use C-style hex addresses (0x40000000). Keep register names matching the
vendor HAL where applicable.\
"""


def run(context: dict) -> str:
    sys_reqs = context.get("system_requirements", "")
    sys_arch = context.get("system_architecture", "")
    prompt = f"""\
Define the complete Hardware/Software Interface for the embedded system below.

SYSTEM REQUIREMENTS (excerpt):
{sys_reqs[:2000]}

SYSTEM ARCHITECTURE:
{sys_arch[:3000]}
"""
    return call_agent(_ROLE, prompt)
