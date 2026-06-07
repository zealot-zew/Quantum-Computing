"""
main.py — Pipeline Entry Point

CLI interface for the Quantum-Assisted CXL-Aware Scheduler.
Selects a scheduler, runs the full pipeline (QUBO → schedule → execute → evaluate),
and outputs results to results/.

Usage:
    python main.py --scheduler fcfs
    python main.py --scheduler rr
    python main.py --scheduler greedy
    python main.py --scheduler rqaoa
    python main.py --scheduler all   # Run all schedulers sequentially

Status:
    Scaffold only — CLI args work. Full pipeline wired on Day 5 by Devandra (P5).

Maintained by: Devandra (P5 — Documentation & Integration Lead)
"""

import argparse
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    """Parse CLI args and dispatch to the selected scheduler pipeline."""
    parser = argparse.ArgumentParser(
        description="Quantum-Assisted CXL-Aware Scheduler — full pipeline runner."
    )
    parser.add_argument(
        "--scheduler",
        type=str,
        choices=["fcfs", "rr", "greedy", "rqaoa", "all"],
        required=True,
        help="Scheduler to run: fcfs | rr | greedy | rqaoa | all",
    )
    args = parser.parse_args()

    logger.info("Scheduler selected: %s", args.scheduler)
    logger.info("Pipeline not yet wired — will be completed on Day 5.")
    logger.info("Scaffold confirmed working. ✓")


if __name__ == "__main__":
    main()