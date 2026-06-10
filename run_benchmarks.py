"""
run_benchmarks.py — Run all schedulers through the full execution pipeline.

Executes each scheduler against the canonical 8-task set, records per-task
completion times, computes aggregate metrics, and saves results to CSV.

Output files:
    results/execution_log.csv          — One row per task per scheduler
    results/all_schedulers_summary.csv — One row per scheduler (aggregated)

Usage:
    python run_benchmarks.py                  # Full execution (real subprocesses)
    python run_benchmarks.py --dry-run        # Skip subprocess execution
    python run_benchmarks.py --scale-factor 0.1  # Scale memory down for quick runs

Maintained by: Hari (P2 — Infra + Quantum Algo)
"""

import argparse
import csv
import logging
import os
import sys
import time
from typing import Dict, List, Tuple

# Ensure project root is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.scheduler.task_model import Task
from src.scheduler.tasks import (
    CANONICAL_TASKS,
    DRAM_CAPACITY_MB,
    CXL_CAPACITY_MB,
    DRAM_LATENCY_NS,
    CXL_LATENCY_NS,
)
from src.scheduler.fcfs_scheduler import FCFSScheduler
from src.scheduler.round_robin_scheduler import RoundRobinScheduler
from src.scheduler.greedy_scheduler import GreedyScheduler
from src.scheduler.greedy_priority_scheduler import GreedyPriorityScheduler
from src.executor.task_orchestrator import run_all_tasks
from src.evaluation.metrics import (
    calculate_avg_completion_time,
    calculate_makespan,
    calculate_latency_cost,
    calculate_dram_utilization,
    compute_total_latency_cost,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

RESULTS_DIR: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
EXECUTION_LOG_PATH: str = os.path.join(RESULTS_DIR, "execution_log.csv")
SUMMARY_PATH: str = os.path.join(RESULTS_DIR, "all_schedulers_summary.csv")

EXECUTION_LOG_HEADERS: List[str] = [
    "scheduler_name",
    "task_id",
    "memory_requirement_mb",
    "priority",
    "memory_sensitivity",
    "assigned_node",
    "assigned_tier",
    "start_time_s",
    "end_time_s",
    "duration_s",
    "latency_cost_ns",
]

SUMMARY_HEADERS: List[str] = [
    "scheduler_name",
    "num_tasks",
    "dram_tasks",
    "cxl_tasks",
    "dram_usage_mb",
    "cxl_usage_mb",
    "dram_utilization_pct",
    "avg_completion_time_s",
    "makespan_s",
    "total_latency_cost_ns",
    "avg_latency_cost_ns",
    "scheduling_time_s",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _scale_tasks(tasks: List[Task], scale_factor: float) -> List[Task]:
    """Scale task memory requirements for faster simulation runs.

    Args:
        tasks: Original task list.
        scale_factor: Multiplier for memory_requirement_mb (e.g. 0.1 = 10%).

    Returns:
        New list of Task objects with scaled memory.
    """
    return [
        Task(
            task_id=t.task_id,
            memory_requirement_mb=t.memory_requirement_mb * scale_factor,
            priority=t.priority,
            memory_sensitivity=t.memory_sensitivity,
        )
        for t in tasks
    ]


def _get_scheduler_assignment(
    scheduler_name: str,
    tasks: List[Task],
    dram_cap: float,
    cxl_cap: float,
) -> Dict[int, str]:
    """Run a single scheduler and return its assignment dict.

    Args:
        scheduler_name: One of 'fcfs', 'rr', 'greedy', 'greedy_priority', 'rqaoa'.
        tasks: Task list.
        dram_cap: DRAM capacity in MB.
        cxl_cap: CXL capacity in MB.

    Returns:
        Assignment dict: {task_id: "DRAM" | "CXL"}.
    """
    if scheduler_name == "fcfs":
        scheduler = FCFSScheduler(dram_cap, cxl_cap)
        return scheduler.schedule(tasks)

    elif scheduler_name == "rr":
        scheduler = RoundRobinScheduler(dram_cap, cxl_cap)
        return scheduler.schedule(tasks)

    elif scheduler_name == "greedy":
        scheduler = GreedyScheduler(dram_cap, cxl_cap)
        return scheduler.schedule(tasks)

    elif scheduler_name == "greedy_priority":
        scheduler = GreedyPriorityScheduler(dram_cap, cxl_cap)
        return scheduler.schedule(tasks)

    elif scheduler_name == "rqaoa":
        return _run_rqaoa_scheduler(tasks, dram_cap)

    else:
        raise ValueError(f"Unknown scheduler: {scheduler_name}")


def _run_rqaoa_scheduler(
    tasks: List[Task],
    dram_cap: float,
) -> Dict[int, str]:
    """Run RQAOA optimizer and return a tier assignment dict.

    Builds the QUBO matrix from tasks, converts to OpenQAOA format,
    runs RQAOA, and decodes the result into {task_id: "DRAM"|"CXL"}.

    Args:
        tasks: Task list.
        dram_cap: DRAM capacity in MB.

    Returns:
        Assignment dict.
    """
    try:
        from src.rqaoa.qubo_builder import (
            build_qubo_from_tasks as _build_qubo,
            DEFAULT_TASKS,
            num_slack_bits,
            compute_dram_used,
            DRAM_CAPACITY_MB as UNSCALED_DRAM_CAP,
        )
        from src.rqaoa.qubo_converter import convert_numpy_qubo_to_openqaoa_dict
        from src.rqaoa.rqaoa_runner import run_rqaoa_optimizer
        from src.rqaoa.result_parser import decode_assignment_to_memory_map

        # Use the QUBO builder's own task definitions for RQAOA
        # because it has its own Task dataclass.
        qubo_tasks = DEFAULT_TASKS
        n_tasks = len(qubo_tasks)
        n_slack = num_slack_bits(UNSCALED_DRAM_CAP)
        n_total = n_tasks + n_slack

        logger.info(
            "RQAOA: Building QUBO (%d tasks + %d slack = %d variables)...",
            n_tasks, n_slack, n_total,
        )
        # Use unscaled DRAM cap to match the unscaled DEFAULT_TASKS
        qubo_matrix = _build_qubo(qubo_tasks, dram_capacity_mb=UNSCALED_DRAM_CAP)
        qubo_dict = convert_numpy_qubo_to_openqaoa_dict(qubo_matrix)

        logger.info("RQAOA: Running optimizer...")
        raw_solution = run_rqaoa_optimizer(qubo_dict, num_variables=n_total)

        # Extract only task bits (first n_tasks indices)
        task_assignment_int = {
            qubo_tasks[i].task_id: int(raw_solution.get(i, 0))
            for i in range(n_tasks)
        }

        memory_map = decode_assignment_to_memory_map(task_assignment_int)
        logger.info("RQAOA assignment: %s", memory_map)
        return memory_map

    except Exception as exc:
        logger.error("RQAOA pipeline failed: %s. Using greedy fallback.", exc)
        # Fallback to greedy scheduler
        scheduler = GreedyScheduler(dram_cap, CXL_CAPACITY_MB)
        return scheduler.schedule(tasks)


def _compute_summary_row(
    scheduler_name: str,
    assignment: Dict[int, str],
    tasks: List[Task],
    results: List[Dict],
    dram_cap: float,
    scheduling_time_s: float,
) -> Dict:
    """Compute a single summary row for the aggregate CSV.

    Args:
        scheduler_name: Scheduler identifier string.
        assignment: {task_id: "DRAM"|"CXL"}.
        tasks: Task list.
        results: Per-task result dicts from the orchestrator.
        dram_cap: DRAM capacity for utilization calculation.
        scheduling_time_s: Time taken to compute the assignment.

    Returns:
        Dict with all SUMMARY_HEADERS keys populated.
    """
    task_map = {t.task_id: t for t in tasks}

    dram_tasks = sum(1 for tier in assignment.values() if tier == "DRAM")
    cxl_tasks = sum(1 for tier in assignment.values() if tier == "CXL")
    dram_usage = sum(
        task_map[tid].memory_requirement_mb
        for tid, tier in assignment.items() if tier == "DRAM"
    )
    cxl_usage = sum(
        task_map[tid].memory_requirement_mb
        for tid, tier in assignment.items() if tier == "CXL"
    )
    dram_util = calculate_dram_utilization(dram_usage, dram_cap)

    durations = [r["duration_s"] for r in results]
    start_times = [r["start_time_s"] for r in results]
    end_times = [r["end_time_s"] for r in results]

    avg_completion = calculate_avg_completion_time(durations)
    makespan = calculate_makespan(start_times, end_times)

    total_latency = compute_total_latency_cost(assignment, tasks)
    avg_latency = total_latency / len(tasks) if tasks else 0.0

    return {
        "scheduler_name": scheduler_name,
        "num_tasks": len(tasks),
        "dram_tasks": dram_tasks,
        "cxl_tasks": cxl_tasks,
        "dram_usage_mb": round(dram_usage, 2),
        "cxl_usage_mb": round(cxl_usage, 2),
        "dram_utilization_pct": round(dram_util, 2),
        "avg_completion_time_s": round(avg_completion, 6),
        "makespan_s": round(makespan, 6),
        "total_latency_cost_ns": round(total_latency, 2),
        "avg_latency_cost_ns": round(avg_latency, 2),
        "scheduling_time_s": round(scheduling_time_s, 4),
    }


def _print_comparison_table(summaries: List[Dict]) -> None:
    """Print a formatted comparison table to stdout.

    Args:
        summaries: List of summary dicts (one per scheduler).
    """
    header_fmt = (
        "{:<18} {:>6} {:>6} {:>10} {:>10} {:>10} {:>14} {:>10}"
    )
    row_fmt = (
        "{:<18} {:>6} {:>6} {:>10.4f} {:>10.4f} {:>10.1f} {:>14.2f} {:>10.4f}"
    )

    print("\n" + "=" * 105)
    print("SCHEDULER COMPARISON — All schedulers vs canonical 8-task set")
    print("=" * 105)
    print(header_fmt.format(
        "Scheduler", "DRAM", "CXL",
        "Avg Time", "Makespan", "DRAM %", "Latency Cost", "Sched Time"
    ))
    print("-" * 105)

    for s in summaries:
        print(row_fmt.format(
            s["scheduler_name"],
            s["dram_tasks"],
            s["cxl_tasks"],
            s["avg_completion_time_s"],
            s["makespan_s"],
            s["dram_utilization_pct"],
            s["total_latency_cost_ns"],
            s["scheduling_time_s"],
        ))

    print("=" * 105)

    # Highlight best scheduler by latency cost
    best = min(summaries, key=lambda s: s["total_latency_cost_ns"])
    print(f"\n✅ Lowest latency cost: {best['scheduler_name']} "
          f"({best['total_latency_cost_ns']:.2f} ns·MB)")
    print()


# ---------------------------------------------------------------------------
# Main benchmark runner
# ---------------------------------------------------------------------------

def run_benchmarks(
    dry_run: bool = False,
    scale_factor: float = 1.0,
    schedulers: List[str] = None,
) -> List[Dict]:
    """Run all schedulers through the full pipeline and save results.

    Args:
        dry_run: If True, skip actual subprocess execution.
        scale_factor: Scale factor for task memory sizes.
        schedulers: List of scheduler names to run. Defaults to all 5.

    Returns:
        List of summary dicts for each scheduler.
    """
    if schedulers is None:
        schedulers = ["fcfs", "rr", "greedy", "greedy_priority", "rqaoa"]

    os.makedirs(RESULTS_DIR, exist_ok=True)
    os.makedirs(os.path.join(RESULTS_DIR, "plots"), exist_ok=True)

    # Scale tasks for manageable memory allocation on dev machines
    tasks = _scale_tasks(CANONICAL_TASKS, scale_factor)
    dram_cap = DRAM_CAPACITY_MB * scale_factor
    cxl_cap = CXL_CAPACITY_MB * scale_factor

    logger.info(
        "Benchmark config: %d schedulers | %d tasks | "
        "scale=%.2f | dry_run=%s",
        len(schedulers), len(tasks), scale_factor, dry_run,
    )
    logger.info(
        "Memory: DRAM=%.1f MB | CXL=%.1f MB | "
        "Total tasks=%.1f MB",
        dram_cap, cxl_cap,
        sum(t.memory_requirement_mb for t in tasks),
    )

    all_execution_rows: List[Dict] = []
    all_summaries: List[Dict] = []

    for scheduler_name in schedulers:
        logger.info("=" * 60)
        logger.info("Running scheduler: %s", scheduler_name.upper())
        logger.info("=" * 60)

        # Step 1: Get assignment
        t0 = time.perf_counter()
        try:
            assignment = _get_scheduler_assignment(
                scheduler_name, tasks, dram_cap, cxl_cap,
            )
        except Exception as exc:
            logger.error(
                "Scheduler '%s' failed: %s. Skipping.", scheduler_name, exc,
            )
            continue
        scheduling_time_s = time.perf_counter() - t0

        logger.info("Assignment: %s", assignment)

        # Step 2: Execute through orchestrator
        results = run_all_tasks(
            assignment=assignment,
            tasks=tasks,
            dry_run=dry_run,
        )

        # Step 3: Build per-task execution log rows
        task_map = {t.task_id: t for t in tasks}
        for result in results:
            tid = result["task_id"]
            task = task_map[tid]
            tier = assignment[tid]

            latency_cost = calculate_latency_cost(
                memory_requirement_mb=task.memory_requirement_mb,
                memory_sensitivity=task.memory_sensitivity,
                assigned_tier=tier,
            )

            row = {
                "scheduler_name": scheduler_name,
                "task_id": tid,
                "memory_requirement_mb": task.memory_requirement_mb,
                "priority": task.priority,
                "memory_sensitivity": task.memory_sensitivity,
                "assigned_node": result["node"],
                "assigned_tier": tier,
                "start_time_s": result["start_time_s"],
                "end_time_s": result["end_time_s"],
                "duration_s": result["duration_s"],
                "latency_cost_ns": round(latency_cost, 2),
            }
            all_execution_rows.append(row)

        # Step 4: Compute summary
        summary = _compute_summary_row(
            scheduler_name, assignment, tasks, results, dram_cap, scheduling_time_s
        )
        all_summaries.append(summary)

        logger.info(
            "%s done: avg=%.4fs | makespan=%.4fs | "
            "latency_cost=%.2f | DRAM%%=%.1f",
            scheduler_name.upper(),
            summary["avg_completion_time_s"],
            summary["makespan_s"],
            summary["total_latency_cost_ns"],
            summary["dram_utilization_pct"],
        )

    # Step 5: Save execution log CSV
    with open(EXECUTION_LOG_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=EXECUTION_LOG_HEADERS)
        writer.writeheader()
        writer.writerows(all_execution_rows)
    logger.info("Saved execution log: %s", EXECUTION_LOG_PATH)

    # Step 6: Save summary CSV
    with open(SUMMARY_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=SUMMARY_HEADERS)
        writer.writeheader()
        writer.writerows(all_summaries)
    logger.info("Saved summary: %s", SUMMARY_PATH)

    # Step 7: Print comparison
    if all_summaries:
        _print_comparison_table(all_summaries)

    return all_summaries


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Parse CLI args and run benchmarks."""
    parser = argparse.ArgumentParser(
        description="Run all schedulers through the full execution pipeline.",
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
        help=(
            "Scale factor for task memory sizes (default: 1.0 = 100%%). "
            "Use 0.1 for quick dev simulation."
        ),
    )
    parser.add_argument(
        "--schedulers",
        nargs="+",
        default=None,
        choices=["fcfs", "rr", "greedy", "greedy_priority", "rqaoa"],
        help="Specific schedulers to run (default: all).",
    )
    args = parser.parse_args()

    run_benchmarks(
        dry_run=args.dry_run,
        scale_factor=args.scale_factor,
        schedulers=args.schedulers,
    )


if __name__ == "__main__":
    main()
