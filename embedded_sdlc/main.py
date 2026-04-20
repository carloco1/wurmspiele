"""
Embedded SDLC — Full V-Model Pipeline  (Command-Line Entry Point)
=================================================================

Usage:
  python main.py "Design a CAN-bus motor controller for a BLDC motor"
  python main.py --task "FreeRTOS temperature logger on STM32F4"
  python main.py --task-file project.txt --out artefacts/my_project/
  python main.py --stages system_requirements system_architecture --task "..."

Runs all 16 V-Model stages (or a subset) and writes Markdown artefacts to the
output directory (default: ./output/<timestamp>/).
"""
import argparse
import sys
import time
from pathlib import Path

from config import STAGE_ORDER
from orchestrator import run_pipeline, print_vmodel


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Agentic Embedded SDLC — full V-Model via Claude claude-opus-4-7",
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
        help="Read project description from a text file",
    )
    group.add_argument(
        "--show-vmodel",
        action="store_true",
        help="Print the V-Model diagram and exit",
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
        choices=STAGE_ORDER,
        help=f"Run only these stages (subset of: {' '.join(STAGE_ORDER)})",
    )
    return parser.parse_args()


def _resolve_task(args: argparse.Namespace) -> str:
    if args.task_file:
        p = Path(args.task_file)
        if not p.exists():
            print(f"ERROR: task file not found: {p}", file=sys.stderr)
            sys.exit(1)
        return p.read_text(encoding="utf-8").strip()
    return (args.task or args.task_flag or "").strip()


def main() -> None:
    args = _parse_args()

    if getattr(args, "show_vmodel", False):
        print_vmodel()
        return

    task = _resolve_task(args)
    if not task:
        print("ERROR: no project description provided.", file=sys.stderr)
        sys.exit(1)

    timestamp  = time.strftime("%Y%m%d_%H%M%S")
    output_dir = Path(args.out) if args.out else Path("output") / timestamp

    # Optional stage filtering
    if args.stages:
        import config
        config.STAGE_ORDER = args.stages  # type: ignore[assignment]

    print_vmodel()
    print(f"Project : {task[:120]}{'…' if len(task) > 120 else ''}")
    print(f"Stages  : {len(config.STAGE_ORDER if args.stages else STAGE_ORDER)}/16")
    print(f"Output  : {output_dir}\n")

    t_start = time.monotonic()
    try:
        run_pipeline(task, output_dir)
    except KeyboardInterrupt:
        print("\n\nPipeline interrupted by user.", file=sys.stderr)
        sys.exit(130)

    elapsed = time.monotonic() - t_start
    print(f"\n{'='*68}")
    print(f"  V-Model pipeline complete in {elapsed:.1f}s")
    print(f"  Artefacts: {output_dir}/")
    print(f"{'='*68}\n")


if __name__ == "__main__":
    main()
