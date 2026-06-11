"""
Greedy Priority-Weighted Scheduler.

A variant of the Greedy scheduler that assigns tasks to memory tiers
based on a combined score of both task priority and memory sensitivity.

This differs from the plain GreedyScheduler (sensitivity-only) by giving
high-priority tasks an extra boost — ensuring that urgent workloads are
protected from CXL latency even when their raw sensitivity score is moderate.

Maintained by: Vikas (P4 — Simulation & Evaluation Engineer)
"""

from typing import Dict, List

from src.evaluation.metrics import calculate_latency_cost
from src.scheduler.task_model import Task


# Blending coefficient for the composite score.
# PRIORITY_WEIGHT + SENSITIVITY_WEIGHT must equal 1.0.
PRIORITY_WEIGHT: float = 0.5       # Contribution from task priority (normalised)
SENSITIVITY_WEIGHT: float = 0.5    # Contribution from memory_sensitivity

# Assumed maximum priority value used for normalisation.
MAX_PRIORITY: int = 5


class GreedyPriorityScheduler:
    """
    Greedy scheduler using a composite priority-sensitivity score.

    For each task a composite score is computed:

        score = PRIORITY_WEIGHT    × (priority / MAX_PRIORITY)
              + SENSITIVITY_WEIGHT × memory_sensitivity

    Tasks are sorted by this score in descending order. The highest-scoring
    tasks are assigned to DRAM first until the DRAM capacity is exhausted;
    remaining tasks fall through to CXL memory.

    Compared to the plain GreedyScheduler (which uses sensitivity alone),
    this variant ensures that high-priority but moderately sensitive tasks
    still get DRAM placement, which is important for latency-critical
    production workloads.

    Attributes:
        dram_capacity_mb: Maximum DRAM capacity in megabytes.
        cxl_capacity_mb:  Maximum CXL memory capacity in megabytes.
    """

    def __init__(self, dram_capacity_mb: float, cxl_capacity_mb: float) -> None:
        """
        Initialise the scheduler with memory tier capacities.

        Args:
            dram_capacity_mb: DRAM capacity in MB.
            cxl_capacity_mb:  CXL memory capacity in MB.

        Raises:
            ValueError: If either capacity is zero or negative.
        """
        if dram_capacity_mb <= 0:
            raise ValueError(
                f"dram_capacity_mb must be positive, got {dram_capacity_mb}"
            )
        if cxl_capacity_mb <= 0:
            raise ValueError(
                f"cxl_capacity_mb must be positive, got {cxl_capacity_mb}"
            )
        self.dram_capacity_mb = dram_capacity_mb
        self.cxl_capacity_mb = cxl_capacity_mb

    def _composite_score(self, task: Task) -> float:
        """
        Compute the priority-weighted composite score for a single task.

        A higher score means the task benefits more from DRAM placement.

        Args:
            task: A Task object.

        Returns:
            Composite score in [0.0, 1.0].
        """
        normalised_priority = task.priority / MAX_PRIORITY
        return (
            PRIORITY_WEIGHT * normalised_priority
            + SENSITIVITY_WEIGHT * task.memory_sensitivity
        )

    def schedule(self, tasks: List[Task]) -> Dict[int, str]:
        """
        Schedule tasks using the priority-weighted greedy policy.

        Algorithm:
            1. Compute a composite score for every task.
            2. Sort tasks by composite score, highest first.
            3. Greedily assign each task to DRAM while capacity allows.
            4. Assign remaining tasks to CXL.

        Args:
            tasks: List of Task objects to schedule.

        Returns:
            Dictionary mapping task_id -> memory tier ("DRAM" or "CXL").

        Raises:
            ValueError: If total memory requirement exceeds combined
                        DRAM + CXL capacity.
        """
        total_memory_mb = sum(task.memory_requirement_mb for task in tasks)
        total_capacity_mb = self.dram_capacity_mb + self.cxl_capacity_mb
        if total_memory_mb > total_capacity_mb:
            raise ValueError(
                f"Total memory requirement ({total_memory_mb:.1f} MB) exceeds "
                f"total available capacity ({total_capacity_mb:.1f} MB)"
            )

        scored_tasks = sorted(tasks, key=self._composite_score, reverse=True)
        assignment: Dict[int, str] = {}
        dram_used_mb = 0.0
        cxl_used_mb = 0.0

        for task in scored_tasks:
            if dram_used_mb + task.memory_requirement_mb <= self.dram_capacity_mb:
                assignment[task.task_id] = "DRAM"
                dram_used_mb += task.memory_requirement_mb
            elif cxl_used_mb + task.memory_requirement_mb <= self.cxl_capacity_mb:
                assignment[task.task_id] = "CXL"
                cxl_used_mb += task.memory_requirement_mb
            else:
                remaining_dram_mb = self.dram_capacity_mb - dram_used_mb
                remaining_cxl_mb = self.cxl_capacity_mb - cxl_used_mb
                raise ValueError(
                    f"Cannot fit task {task.task_id} "
                    f"(requires {task.memory_requirement_mb:.1f} MB) into "
                    f"remaining capacity (DRAM: {remaining_dram_mb:.1f} MB, "
                    f"CXL: {remaining_cxl_mb:.1f} MB)"
                )

        return assignment

    def compute_total_cost(
        self,
        tasks: List[Task],
        assignment: Dict[int, str],
    ) -> float:
        """
        Compute the total weighted latency cost for a given assignment.

        Uses the same cost formula as evaluation/metrics.py:
            cost_i = memory_sensitivity_i × tier_latency_ns × memory_mb_i

        Args:
            tasks:      List of Task objects.
            assignment: Mapping of task_id -> "DRAM" or "CXL".

        Returns:
            Total weighted latency cost in nanosecond-megabyte units (ns·MB).
        """
        total_cost = 0.0
        for task in tasks:
            total_cost += calculate_latency_cost(
                memory_requirement_mb=task.memory_requirement_mb,
                memory_sensitivity=task.memory_sensitivity,
                assigned_tier=assignment[task.task_id],
            )
        return total_cost
