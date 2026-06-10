"""
main.py — Pipeline Entry Point

CLI interface for the Quantum-Assisted CXL-Aware Scheduler.
Selects a scheduler, runs the full pipeline (QUBO → schedule → execute → evaluate),
and outputs results to results/.

Usage:
    python main.py --scheduler fcfs
    python main.py --scheduler rr
    python main.py --scheduler greedy
    python main.py --scheduler greedy_priority
    python main.py --scheduler rqaoa
    python main.py --scheduler all   # Run all schedulers sequentially
    python main.py --scheduler fcfs --dry-run  # Run without actual task execution
"""

import argparse
import logging
import os
import sys

from run_benchmarks import run_benchmarks
from src.evaluation.graphs import generate_all_plots

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
        choices=["fcfs", "rr", "greedy", "greedy_priority", "rqaoa", "all"],
        required=True,
        help="Scheduler to run: fcfs | rr | greedy | greedy_priority | rqaoa | all",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip actual subprocess execution (print commands only).",
    )
    parser.add_argument(
        "--scale-factor",
        type=float,
        default=1.0,
        help="Scale factor for task memory sizes (default: 1.0). Use 0.1 for quick simulation.",
    )
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("Quantum-Assisted CXL-Aware Scheduler Pipeline")
    logger.info("=" * 60)

    schedulers_to_run = (
        ["fcfs", "rr", "greedy", "greedy_priority", "rqaoa"]
        if args.scheduler == "all"
        else [args.scheduler]
    )

    try:
        all_summaries = run_benchmarks(
            dry_run=args.dry_run,
            scale_factor=args.scale_factor,
            schedulers=schedulers_to_run,
        )
        
        if all_summaries:
            logger.info("Generating evaluation plots...")
            results_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
            summary_csv = os.path.join(results_dir, "all_schedulers_summary.csv")
            plots_dir = os.path.join(results_dir, "plots")
            
            generate_all_plots(summary_csv, plots_dir)
            logger.info(f"Plots saved to {plots_dir}")

        logger.info("Pipeline completed successfully. ✓")
    except Exception as exc:
        logger.error("Pipeline failed: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()