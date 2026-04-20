"""
Embedded SDLC Orchestrator
--------------------------
Runs the six-stage pipeline sequentially and writes artefacts to disk.

Pipeline:
  requirements → architecture → codegen → analysis → testgen → review

Each stage receives the full accumulated context from all prior stages.
"""
import sys
import time
from pathlib import Path

from agents import AGENTS
from config import STAGE_ORDER

STAGE_LABELS = {
    "requirements": "1/6  Requirements Analysis",
    "architecture": "2/6  Architecture Design",
    "codegen":      "3/6  Code Generation",
    "analysis":     "4/6  Static Analysis",
    "testgen":      "5/6  Test Generation",
    "review":       "6/6  Design Review",
}


def _banner(label: str) -> None:
    width = 60
    print("\n" + "=" * width)
    print(f"  STAGE  {label}")
    print("=" * width + "\n")


def run_pipeline(task: str, output_dir: Path) -> dict[str, str]:
    """
    Execute the full SDLC pipeline for *task*.

    Returns a dict mapping stage name → artefact text.
    Artefacts are also written as Markdown files under *output_dir*.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    context: dict[str, str] = {"task": task}

    for stage in STAGE_ORDER:
        label = STAGE_LABELS[stage]
        _banner(label)

        t0 = time.monotonic()
        agent_fn = AGENTS[stage]
        result = agent_fn(context)
        elapsed = time.monotonic() - t0

        context[stage] = result

        artifact = output_dir / f"{stage}.md"
        artifact.write_text(result, encoding="utf-8")
        print(f"\n✓  Artefact saved → {artifact}  ({elapsed:.1f}s)\n")

    _write_index(task, output_dir)
    return context


def _write_index(task: str, output_dir: Path) -> None:
    """Write a summary index.md linking all artefacts."""
    lines = [
        "# Embedded SDLC — Artefacts\n",
        f"**Project:** {task}\n",
        "\n## Pipeline Output\n",
    ]
    for stage in STAGE_ORDER:
        label = STAGE_LABELS[stage].split(None, 1)[1]
        lines.append(f"- [{label}]({stage}.md)")
    (output_dir / "index.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
