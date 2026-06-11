"""
Greedy Scheduler.

Assigns tasks to memory tiers based on memory sensitivity.
Most sensitive tasks get DRAM first.
"""

from typing import Dict, List
from src.scheduler.task_model import Task
from src.scheduler.scheduler_interface import BaseScheduler


class GreedyScheduler(BaseScheduler):
    """
    Greedy scheduler based on memory sensitivity.

    This scheduler sorts tasks by memory_sensitivity in descending order
    and assigns the most sensitive tasks to DRAM first, placing remaining
    tasks in CXL memory.

    This represents a heuristic that aims to minimize the impact of high
    memory latency by prioritizing latency-sensitive workloads for fast
    memory placement.

    Attributes:
        dram_capacity_mb: Maximum DRAM capacity in megabytes
        cxl_capacity_mb: Maximum CXL memory capacity in megabytes
    """

    def __init__(self, dram_capacity_mb: float, cxl_capacity_mb: float):
        """
        Initialize Greedy scheduler with memory tier capacities.

        Args:
            dram_capacity_mb: DRAM capacity in MB
            cxl_capacity_mb: CXL memory capacity in MB
        """
        self.dram_capacity_mb = dram_capacity_mb
        self.cxl_capacity_mb = cxl_capacity_mb

    def schedule(self, tasks: List[Task]) -> Dict[int, str]:
        """
        Schedule tasks using Greedy policy based on memory sensitivity.

        Args:
            tasks: List of Task objects to schedule

        Returns:
            Dictionary mapping task_id to memory tier ("DRAM" or "CXL")

        Raises:
            ValueError: If total memory requirement exceeds total available capacity
        """
        # Check total capacity
        total_memory = sum(task.memory_requirement_mb for task in tasks)
        total_capacity = self.dram_capacity_mb + self.cxl_capacity_mb

        if total_memory > total_capacity:
            raise ValueError(
                f"Total memory requirement ({total_memory:.1f} MB) exceeds "
                f"total available capacity ({total_capacity:.1f} MB)"
            )

        # Sort tasks by memory_sensitivity descending (most sensitive first)
        sorted_tasks = sorted(tasks, key=lambda t: t.memory_sensitivity, reverse=True)

        assignment = {}
        dram_used = 0.0
        cxl_used = 0.0

        for task in sorted_tasks:
            # Try to assign high-sensitivity tasks to DRAM first
            if dram_used + task.memory_requirement_mb <= self.dram_capacity_mb:
                assignment[task.task_id] = "DRAM"
                dram_used += task.memory_requirement_mb
            # Otherwise assign to CXL
            elif cxl_used + task.memory_requirement_mb <= self.cxl_capacity_mb:
                assignment[task.task_id] = "CXL"
                cxl_used += task.memory_requirement_mb
            else:
                remaining_dram_mb = self.dram_capacity_mb - dram_used
                remaining_cxl_mb = self.cxl_capacity_mb - cxl_used
                raise ValueError(
                    f"Cannot fit task {task.task_id} "
                    f"(requires {task.memory_requirement_mb:.1f} MB) into "
                    f"remaining capacity (DRAM: {remaining_dram_mb:.1f} MB, "
                    f"CXL: {remaining_cxl_mb:.1f} MB)"
                )

        return assignment

    def compute_total_cost(self, tasks: List[Task], assignment: Dict[int, str]) -> float:
        """
        Compute total latency cost for the given assignment.

        Args:
            tasks: List of Task objects
            assignment: Task-to-tier mapping

        Returns:
            Total weighted latency cost
        """
        from src.scheduler.tasks import DRAM_LATENCY_NS, CXL_LATENCY_NS

        total_cost = 0.0

        for task in tasks:
            tier = assignment[task.task_id]

            if tier == "CXL":
                # CXL tasks incur latency penalty
                latency_penalty = CXL_LATENCY_NS - DRAM_LATENCY_NS
                cost = task.memory_sensitivity * latency_penalty * task.memory_requirement_mb
                total_cost += cost

        return total_cost
