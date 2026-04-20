"""Stage 13 — HW/SW Integration Tests (V-Model right, pairs with HSI Stage 3)."""
from .base import call_agent

_ROLE = """\
You are a firmware verification engineer running HW/SW integration tests.
These tests verify that the software correctly controls and reads all hardware
resources defined in the HW/SW Interface document.

Produce:

1. HW/SW INTEGRATION TEST STRATEGY
   - Test rig: target board, power supply, signal generator, oscilloscope, LA
   - Scope: verify every entry in the HSI (registers, pins, interrupts, DMA, clocks)

2. PERIPHERAL VERIFICATION TESTS  (HIT-xxx)
   For each peripheral / interface in the HSI:

   HIT-001: <Peripheral> — <Function being verified>
   HSI Reference: Register/Pin/Signal name from HSI
   Equipment    : oscilloscope, logic analyser, DMM, signal gen as needed
   Procedure    : step-by-step test procedure
   Pass criteria: waveform shape, frequency, timing, voltage level, data value
   Automation   : how to automate (JTAG breakpoint, RTT log, UART echo)

   Cover:
   - Register read/write correctness
   - Pin direction and signal level verification
   - Interrupt generation and latency measurement
   - DMA transfer completion and data integrity
   - Communication protocol timing (setup/hold, bit rates)
   - Clock frequency verification
   - Power mode transitions and wake-up time measurement

3. HARDWARE-IN-THE-LOOP  (HIL) TEST CASES
   - Tests where the firmware response to hardware stimuli is verified
   - Fault injection: disconnect sensor, short pin, over-voltage, under-voltage

4. TIMING MEASUREMENT RESULTS TEMPLATE
   | Signal | HSI Spec (min/typ/max) | Measured | Pass/Fail |

5. REGRESSION TEST SUITE
   - Which HIT tests must pass after every firmware build
   - Automated via CI with hardware test bench

6. TRACEABILITY MATRIX
   | HIT-ID | HSI Reference | QT-IDs | SFR-IDs |
   |--------|--------------|--------|---------|
"""


def run(context: dict) -> str:
    hsi     = context.get("hw_sw_interface", "")
    code    = context.get("implementation", "")
    swqt    = context.get("sw_qualification", "")
    prompt = f"""\
Write HW/SW Integration Tests to verify the software against every entry
in the HW/SW Interface document.

HW/SW INTERFACE SPECIFICATION:
{hsi[:4000]}

IMPLEMENTATION (driver/HAL functions):
{code[:1500]}

SW QUALIFICATION TESTS (already defined):
{swqt[:500]}
"""
    return call_agent(_ROLE, prompt)
