"""
Embedded SDLC Orchestrator — Full V-Model Pipeline
----------------------------------------------------
Runs all 16 stages of the V-Model sequentially and writes artefacts to disk.

V-Model layout:
  LEFT (development)               RIGHT (verification)
  ─────────────────────────────    ─────────────────────────────
  1  System Requirements      ──►  14 System Validation
  2  System Architecture      ──►  13 HW/SW Integration Tests
  3  HW/SW Interface          ──►  12 SW Qualification Tests
  4  SW Requirements          ──►  11 Integration Tests
  5  SW Architecture          ──►  10 Unit Tests
  6  Detailed Design
  7  Implementation (Code)
        ↓ cross-cutting
  8  Static Analysis (MISRA/CERT-C)
  9  Safety Analysis (FMEA/FTA)
        ↓ infrastructure
  15 CI/CD Pipeline
  16 Design Review (Go/No-Go)
"""
import sys
import time
from pathlib import Path

from agents import AGENTS
from config import STAGE_ORDER, STAGE_LABELS

# ── V-Model ASCII banner ───────────────────────────────────────────────────────
_VMODEL = """\
   DEVELOPMENT (left)                    VERIFICATION (right)
   ─────────────────────────────────     ──────────────────────────────────
   1  System Requirements          ───►  14  System Validation
      2  System Architecture       ──►  13  HW/SW Integration Tests
         3  HW/SW Interface        ─►   12  SW Qualification Tests
            4  SW Requirements     ►    11  Integration Tests
               5  SW Architecture  ┐    10  Unit Tests
                  6  Detailed Design│
                  7  Implementation ┘
                     ↓ cross-cutting ↓
                  8  Static Analysis  (MISRA / CERT-C)
                  9  Safety Analysis  (FMEA / FTA)
                     ↓ infrastructure ↓
                 15  CI/CD Pipeline
                 16  Design Review  ──  Go / No-Go\
"""

_WIDTH = 68


def _banner(stage: str) -> None:
    label = STAGE_LABELS[stage]
    print("\n" + "=" * _WIDTH)
    print(f"  STAGE {label}")
    print("=" * _WIDTH + "\n")


def _progress_bar(done: int, total: int, width: int = 40) -> str:
    filled = int(width * done / total)
    bar = "█" * filled + "░" * (width - filled)
    return f"[{bar}] {done}/{total}"


def run_pipeline(task: str, output_dir: Path) -> dict[str, str]:
    """
    Execute the full V-Model pipeline for *task*.
    Returns a dict of stage → artefact text.
    Artefacts are written as Markdown files under *output_dir*.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    context: dict[str, str] = {"task": task}
    total = len(STAGE_ORDER)
    timings: dict[str, float] = {}

    for idx, stage in enumerate(STAGE_ORDER, 1):
        _banner(stage)
        print(_progress_bar(idx - 1, total))
        print()

        t0 = time.monotonic()
        result = AGENTS[stage](context)
        elapsed = time.monotonic() - t0
        timings[stage] = elapsed

        context[stage] = result
        artifact = output_dir / f"{stage}.md"
        artifact.write_text(result, encoding="utf-8")

        print(f"\n✓  {artifact}  ({elapsed:.1f}s)\n")
        print(_progress_bar(idx, total))

    _write_index(task, output_dir, timings)
    return context


def _write_index(task: str, output_dir: Path, timings: dict[str, float]) -> None:
    total_s = sum(timings.values())
    lines = [
        "# Embedded SDLC — V-Model Artefacts\n",
        f"**Project:** {task}\n",
        f"**Total pipeline time:** {total_s:.0f}s\n",
        "\n```\n" + _VMODEL + "\n```\n",
        "\n## Artefacts\n",
        "| Stage | Artefact | Time |",
        "|-------|---------|------|",
    ]
    for stage in STAGE_ORDER:
        label = STAGE_LABELS[stage]
        t = timings.get(stage, 0)
        lines.append(f"| {label} | [{stage}.md]({stage}.md) | {t:.1f}s |")

    (output_dir / "index.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def print_vmodel() -> None:
    print("\n" + "=" * _WIDTH)
    print("  Embedded SDLC — Full V-Model Pipeline")
    print("=" * _WIDTH)
    print(_VMODEL)
    print("=" * _WIDTH + "\n")
