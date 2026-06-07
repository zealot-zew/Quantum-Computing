"""
Evaluation metrics for the Quantum-Assisted CXL-Aware Scheduler.

This module provides functions to compute scheduling quality metrics and
defines the canonical schema for all CSV output files produced by the
evaluation pipeline.

Maintained by: Vikas (P4 — Simulation & Evaluation Engineer)
"""

from typing import List

from src.scheduler.tasks import CXL_LATENCY_NS, DRAM_LATENCY_NS


# =============================================================================
# CSV SCHEMA DEFINITIONS
# =============================================================================
#
# These schemas must remain stable across all scheduler implementations so that
# results from FCFS, Round Robin, Greedy, and RQAOA can be directly compared.
#
# -----------------------------------------------------------------------------
# FILE: results/execution_log.csv
# PURPOSE: One row per task execution. Raw event-level log.
# -----------------------------------------------------------------------------
#
# Column                | Type  | Description
# ----------------------|-------|---------------------------------------------
# scheduler_name        | str   | Scheduler name (e.g. "fcfs", "rqaoa")
# task_id               | int   | Unique task identifier (0–7)
# memory_requirement_mb | float | Memory allocated for this task run (MB)
# priority              | int   | Task priority level
# memory_sensitivity    | float | Latency sensitivity (0.0–1.0)
# assigned_node         | int   | NUMA node assigned: 0=DRAM, 1=CXL
# assigned_tier         | str   | Human-readable tier: "DRAM" or "CXL"
# start_time_s          | float | Task start timestamp (seconds since epoch)
# end_time_s            | float | Task end timestamp (seconds since epoch)
# duration_s            | float | end_time_s - start_time_s
# latency_cost_ns       | float | sensitivity × tier_latency_ns × memory_mb
#
# -----------------------------------------------------------------------------
# FILE: results/all_schedulers_summary.csv
# PURPOSE: One row per scheduler run. Aggregated summary for comparison.
# -----------------------------------------------------------------------------
#
# Column                 | Type  | Description
# -----------------------|-------|--------------------------------------------
# scheduler_name         | str   | Scheduler name (e.g. "fcfs", "rqaoa")
# num_tasks              | int   | Total tasks scheduled (always 8)
# dram_tasks             | int   | Tasks assigned to DRAM
# cxl_tasks              | int   | Tasks assigned to CXL
# dram_usage_mb          | float | Total MB placed in DRAM
# cxl_usage_mb           | float | Total MB placed in CXL
# dram_utilization_pct   | float | dram_usage_mb / DRAM_CAPACITY_MB × 100
# avg_completion_time_s  | float | Mean of all task duration_s values
# makespan_s             | float | max(end_time_s) - min(start_time_s)
# total_latency_cost_ns  | float | Sum of latency_cost_ns across all tasks
# avg_latency_cost_ns    | float | Mean latency_cost_ns per task
# =============================================================================


# Latency constants (nanoseconds). Imported from src.scheduler.tasks to keep values consistent across the codebase.


def calculate_avg_completion_time(durations_s: List[float]) -> float:
    """
    Compute the average task completion time across all scheduled tasks.

    Args:
        durations_s: List of individual task durations in seconds.

    Returns:
        Mean duration in seconds. Returns 0.0 for an empty list.
    """
    # TODO (Day 3): Implement after task_runner.py produces timing output.
    pass


def calculate_makespan(
    start_times_s: List[float],
    end_times_s: List[float],
) -> float:
    """
    Compute the makespan of a scheduling run.

    Makespan is defined as the wall-clock time from when the first task
    starts to when the last task finishes. It measures how long the full
    batch takes end-to-end.

    Args:
        start_times_s: List of task start timestamps (seconds since epoch).
        end_times_s:   List of task end timestamps (seconds since epoch).

    Returns:
        Makespan in seconds. Returns 0.0 if inputs are empty.
    """
    # TODO (Day 3): Implement after task_runner.py produces timing output.
    pass


def calculate_latency_cost(
    memory_requirement_mb: float,
    memory_sensitivity: float,
    assigned_tier: str,
) -> float:
    """
    Compute the weighted latency cost for a single task assignment.

    The cost captures how much a task 'suffers' from its assigned tier.
    A highly sensitive task placed in CXL incurs a high cost; a
    latency-insensitive task placed in CXL incurs very little cost.

    Formula:
        cost = memory_sensitivity × tier_latency_ns × memory_requirement_mb

    Args:
        memory_requirement_mb: Memory footprint of the task in MB.
        memory_sensitivity:    Sensitivity value in [0.0, 1.0].
        assigned_tier:         "DRAM" or "CXL".

    Returns:
        Weighted latency cost in nanosecond-megabyte units (ns·MB).

    Raises:
        ValueError: If assigned_tier is not "DRAM" or "CXL".
    """
    # TODO (Day 3): Implement after scheduler assignments are available.
    pass


def calculate_dram_utilization(
    dram_usage_mb: float,
    dram_capacity_mb: float,
) -> float:
    """
    Compute DRAM utilization as a percentage of total DRAM capacity.

    A utilization close to 100% means DRAM is being used efficiently.
    Very low utilization suggests the scheduler is over-provisioning CXL.

    Args:
        dram_usage_mb:    Total MB of tasks assigned to DRAM.
        dram_capacity_mb: Total available DRAM capacity in MB.

    Returns:
        Utilization percentage in [0.0, 100.0].

    Raises:
        ValueError: If dram_capacity_mb is zero or negative.
    """
    # TODO (Day 3): Implement after scheduler assignments are available.
    pass