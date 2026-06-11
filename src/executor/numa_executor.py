"""
numa_executor.py — NUMA Execution Wrapper

Provides a high-level wrapper around the task orchestrator for single-task
or batch execution.

Maintained by: Hari (P2 — Infra + Quantum Algo)
"""

import logging
from typing import Dict, Optional

from src.scheduler.task_model import Task
from src.executor.task_orchestrator import run_all_tasks

logger = logging.getLogger(__name__)


def execute_with_numa_binding(
    task: Task,
    node: int,
    bandwidth_limit_mb_s: Optional[float] = None,
    dry_run: bool = False,
) -> Dict:
    """
    Execute a single task with NUMA binding.

    This is a convenience wrapper around `run_all_tasks` for executing
    individual tasks.

    Args:
        task: Task object to execute.
        node: NUMA node ID (0 for DRAM, 1 for CXL).
        bandwidth_limit_mb_s: Optional bandwidth limit for CXL.
        dry_run: If True, do not actually run the subprocess.

    Returns:
        Dict containing execution results (start time, duration, return code, etc.)
    """
    tier = "DRAM" if node == 0 else "CXL"
    assignment = {task.task_id: tier}

    logger.info("Executing single task %d on node %d (%s)...", task.task_id, node, tier)

    results = run_all_tasks(
        assignment=assignment,
        tasks=[task],
        dry_run=dry_run,
        bandwidth_limit_mb_s=bandwidth_limit_mb_s,
    )

    return results[0]
