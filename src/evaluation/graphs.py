"""
Visualization functions for scheduler evaluation results.

This module generates comparison plots for all scheduler benchmarks.
All plots are saved to results/plots/ with publication-quality formatting.

Maintained by: Vikas (P4 — Simulation & Evaluation Engineer)

See src/evaluation/README.md for:
  - Full list of planned plots and output filenames
  - Data format expected by each function
"""

# TODO (Day 4): Implement all three functions using matplotlib.
# Import pattern:
#   import matplotlib.pyplot as plt
#   from src.evaluation.metrics import calculate_latency_cost


def plot_latency_comparison(results: list) -> None:
    """
    Generate a bar chart comparing total weighted latency cost per scheduler.

    Args:
        results: List of per-scheduler summary dicts. Each dict must contain:
            - "scheduler_name" (str): Scheduler identifier.
            - "total_latency_cost_ns" (float): Sum of latency costs across tasks.

    Returns:
        None. Saves plot to results/plots/latency_comparison.png.
    """
    # TODO (Day 4): Implement bar chart using matplotlib.
    pass


def plot_makespan_comparison(results: list) -> None:
    """
    Generate a bar chart comparing makespan (wall-clock time) per scheduler.

    Args:
        results: List of per-scheduler summary dicts. Each dict must contain:
            - "scheduler_name" (str): Scheduler identifier.
            - "makespan_s" (float): Total wall-clock time for the full batch.

    Returns:
        None. Saves plot to results/plots/makespan_comparison.png.
    """
    # TODO (Day 4): Implement bar chart using matplotlib.
    pass


def plot_utilization(results: list) -> None:
    """
    Generate a stacked bar chart showing DRAM vs CXL task counts per scheduler.

    Args:
        results: List of per-scheduler summary dicts. Each dict must contain:
            - "scheduler_name" (str): Scheduler identifier.
            - "dram_tasks" (int): Number of tasks assigned to DRAM.
            - "cxl_tasks" (int): Number of tasks assigned to CXL.

    Returns:
        None. Saves plot to results/plots/utilization.png.
    """
    # TODO (Day 4): Implement stacked bar chart using matplotlib.
    pass