"""
Embedded SDLC — Command-Line Entry Point
========================================

Usage:
  python main.py "Design a CAN-bus motor controller for a 24 V BLDC motor"
  python main.py --task "Temperature logger with FreeRTOS on STM32F4"
  python main.py --task-file project.txt --out artefacts/

The system runs all six SDLC stages sequentially and writes artefacts to the
output directory (default: ./output/<timestamp>/).
"""
import argparse
import sys
import time
from pathlib import Path

from orchestrator import run_pipeline


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Agentic Embedded SDLC — orchestrates Requirements → Review via Claude",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "task",
        nargs="?",
        metavar="TASK",
        help="Project description as a positional argument",
    )
    group.add_argument(
        "--task",
        dest="task_flag",
        metavar="DESCRIPTION",
        help="Project description as a named flag",
    )
    group.add_argument(
        "--task-file",
        metavar="FILE",
        help="Read the project description from a text file",
    )
    parser.add_argument(
        "--out",
        default=None,
        metavar="DIR",
        help="Output directory (default: ./output/<timestamp>/)",
    )
    parser.add_argument(
        "--stages",
        nargs="+",
        metavar="STAGE",
        help="Run only specific stages (space-separated subset of: requirements architecture codegen analysis testgen review)",
    )
    return parser.parse_args()


def _resolve_task(args: argparse.Namespace) -> str:
    if args.task_file:
        path = Path(args.task_file)
        if not path.exists():
            print(f"ERROR: task file not found: {path}", file=sys.stderr)
            sys.exit(1)
        return path.read_text(encoding="utf-8").strip()
    return (args.task or args.task_flag or "").strip()


def main() -> None:
    args = _parse_args()
    task = _resolve_task(args)

    if not task:
        print("ERROR: no project description provided.", file=sys.stderr)
        sys.exit(1)

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    output_dir = Path(args.out) if args.out else Path("output") / timestamp

    print("\n╔══════════════════════════════════════════════════════════╗")
    print("║        Embedded SDLC — Agentic Pipeline                 ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print(f"\nProject : {task[:100]}{'…' if len(task) > 100 else ''}")
    print(f"Output  : {output_dir}\n")

    # Optional stage filtering
    if args.stages:
        from config import STAGE_ORDER
        from agents import AGENTS

        valid = set(STAGE_ORDER)
        requested = [s for s in args.stages if s in valid]
        unknown = [s for s in args.stages if s not in valid]
        if unknown:
            print(f"WARNING: unknown stages ignored: {unknown}", file=sys.stderr)

        # Monkey-patch STAGE_ORDER for the filtered run
        import config
        config.STAGE_ORDER = requested

    t_start = time.monotonic()
    try:
        run_pipeline(task, output_dir)
    except KeyboardInterrupt:
        print("\n\nPipeline interrupted by user.", file=sys.stderr)
        sys.exit(130)

    elapsed = time.monotonic() - t_start
    print(f"\n{'='*60}")
    print(f"  Pipeline complete in {elapsed:.1f}s")
    print(f"  Artefacts: {output_dir}/")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
