#!/usr/bin/env python3
"""
Task Runner Skeleton

Accepts CLI arguments for task ID, memory requirement, and target NUMA node,
and logs the configuration to standard output.
"""

import argparse
import sys
import logging

# Set up logging to stdout
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

def parse_arguments() -> argparse.Namespace:
    """Parses command line arguments for the task runner."""
    parser = argparse.ArgumentParser(description="Simulate task execution bound to a NUMA node.")
    parser.add_argument(
        "--task-id",
        type=int,
        required=True,
        help="Unique identifier for the task"
    )
    parser.add_argument(
        "--memory-mb",
        type=float,
        required=True,
        help="Memory allocation requirement in Megabytes (MB)"
    )
    parser.add_argument(
        "--node",
        type=int,
        required=True,
        help="Target NUMA node ID (e.g., 0 for DRAM, 1 for CXL)"
    )
    return parser.parse_args()

def main() -> None:
    """Main entry point for the task runner."""
    args = parse_arguments()
    
    # Log the parameters received
    logger.info(
        f"Initializing task: ID={args.task_id}, "
        f"Memory={args.memory_mb:.1f} MB, Target NUMA Node={args.node}"
    )

if __name__ == "__main__":
    main()
