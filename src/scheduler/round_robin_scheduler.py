"""
Round Robin (RR) Scheduler.

Alternates task assignment between DRAM and CXL memory tiers.
"""

from typing import Dict, List
from src.scheduler.task_model import Task
from src.scheduler.scheduler_interface import BaseScheduler


class RoundRobinScheduler(BaseScheduler):
    """
    Round Robin scheduler.

    This scheduler alternates assignment between DRAM and CXL memory tiers,
    providing a simple load-balancing approach without considering task
    characteristics.

    Attributes:
        dram_capacity_mb: Maximum DRAM capacity in megabytes
        cxl_capacity_mb: Maximum CXL memory capacity in megabytes
    """

    def __init__(self, dram_capacity_mb: float, cxl_capacity_mb: float):
        """
        Initialize Round Robin scheduler with memory tier capacities.

        Args:
            dram_capacity_mb: DRAM capacity in MB
            cxl_capacity_mb: CXL memory capacity in MB
        """
        self.dram_capacity_mb = dram_capacity_mb
        self.cxl_capacity_mb = cxl_capacity_mb

    def schedule(self, tasks: List[Task]) -> Dict[int, str]:
        """
        Schedule tasks using Round Robin policy.

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

        # Sort tasks by task_id for consistent ordering
        sorted_tasks = sorted(tasks, key=lambda t: t.task_id)

        assignment = {}
        dram_used = 0.0
        cxl_used = 0.0

        # Alternate between DRAM and CXL
        for i, task in enumerate(sorted_tasks):
            # Even index -> try DRAM, Odd index -> try CXL
            if i % 2 == 0:
                # Try DRAM first
                if dram_used + task.memory_requirement_mb <= self.dram_capacity_mb:
                    assignment[task.task_id] = "DRAM"
                    dram_used += task.memory_requirement_mb
                # Fallback to CXL
                elif cxl_used + task.memory_requirement_mb <= self.cxl_capacity_mb:
                    assignment[task.task_id] = "CXL"
                    cxl_used += task.memory_requirement_mb
                else:
                    raise ValueError(
                        f"Cannot fit task {task.task_id} into remaining capacity"
                    )
            else:
                # Try CXL first
                if cxl_used + task.memory_requirement_mb <= self.cxl_capacity_mb:
                    assignment[task.task_id] = "CXL"
                    cxl_used += task.memory_requirement_mb
                # Fallback to DRAM
                elif dram_used + task.memory_requirement_mb <= self.dram_capacity_mb:
                    assignment[task.task_id] = "DRAM"
                    dram_used += task.memory_requirement_mb
                else:
                    raise ValueError(
                        f"Cannot fit task {task.task_id} into remaining capacity"
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
