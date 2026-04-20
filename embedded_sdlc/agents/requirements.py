"""Stage 1 — Requirements Analysis Agent."""
from .base import call_agent

_ROLE = """\
You are a requirements engineer specialising in safety-critical embedded systems.

Your deliverable is a structured Software Requirements Specification (SRS) that contains:

1. FUNCTIONAL REQUIREMENTS (FR-xxx)
   - Numbered, atomic, verifiable
   - Include inputs, outputs, and expected behaviour

2. NON-FUNCTIONAL REQUIREMENTS (NFR-xxx)
   - Timing / latency / throughput
   - RAM budget, Flash budget
   - Power consumption targets
   - Temperature / voltage operating range
   - Safety Integrity Level (SIL / ASIL) if applicable

3. HARDWARE REQUIREMENTS (HWR-xxx)
   - Target MCU / processor family
   - Required peripherals and their configuration
   - External ICs and sensors

4. INTERFACE REQUIREMENTS (IR-xxx)
   - Communication protocols (baudrate, framing, error handling)
   - Pin assignments and signal levels
   - Data formats and encodings

5. CONSTRAINTS (CON-xxx)
   - Coding standards (MISRA-C:2012, CERT-C)
   - Toolchain and compiler version
   - Real-time deadlines

Format each requirement:
  [ID] [Priority: MUST | SHOULD | MAY]  <one-sentence statement>
  Rationale: <why>
  Verification: <how to prove compliance>

Close with a TRACEABILITY MATRIX stub (columns: ID | Source | Test Case).\
"""


def run(context: dict) -> str:
    task = context["task"]
    prompt = f"""\
Analyse the following embedded-systems project description and produce a \
complete Software Requirements Specification.

PROJECT DESCRIPTION:
{task}
"""
    return call_agent(_ROLE, prompt)
