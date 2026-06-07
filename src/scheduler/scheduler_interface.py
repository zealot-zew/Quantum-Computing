"""
scheduler_interface.py
----------------------
Abstract base class for all memory-tier schedulers in the
Quantum-Assisted Optimization Engine for CXL-Aware Hybrid Scheduling.

All scheduler implementations (FCFS, RoundRobin, Greedy, RQAOA-based)
must inherit from BaseScheduler and implement the `schedule` method.
"""

from abc import ABC, abstractmethod
from typing import Dict, List
from dataclasses import dataclass


@dataclass
class Task:
    """Canonical task representation used across all scheduler modules."""
    task_id: int
    memory_requirement_mb: float
    priority: int
    memory_sensitivity: float  # 0.0 to 1.0


class BaseScheduler(ABC):
    """
    Abstract base class for all memory-tier schedulers.

    Each concrete scheduler must implement `schedule()`, which maps
    a list of tasks to memory tiers: either "DRAM" (local, low-latency)
    or "CXL" (remote, higher-latency).

    Constants
    ---------
    DRAM_LATENCY_NS : float
        Baseline DRAM access latency in nanoseconds (~100 ns typical).
    CXL_LATENCY_NS : float
        CXL-attached memory access latency in nanoseconds (~300 ns typical).
    DRAM_CAPACITY_MB : float
        Total available DRAM capacity for scheduling in megabytes.
    """

    DRAM_LATENCY_NS: float = 100.0
    CXL_LATENCY_NS: float = 300.0
    DRAM_CAPACITY_MB: float = 4096.0  # 4 GB default

    @abstractmethod
    def schedule(self, tasks: List[Task]) -> Dict[int, str]:
        """
        Assign each task to a memory tier.

        Parameters
        ----------
        tasks : List[Task]
            Ordered list of Task objects to be scheduled.

        Returns
        -------
        Dict[int, str]
            Mapping of task_id -> "DRAM" or "CXL" for every task in `tasks`.
            Every task_id in the input must appear as a key in the output.

        Raises
        ------
        ValueError
            If `tasks` is empty or any task has invalid field values.
        """
        pass

    def compute_total_latency_cost(
        self,
        assignment: Dict[int, str],
        tasks: List[Task]
    ) -> float:
        """
        Compute the total weighted latency cost for a given assignment.

        Uses memory_sensitivity and memory_requirement_mb as weights.
        Higher sensitivity tasks incur a larger cost penalty when placed on CXL.

        Parameters
        ----------
        assignment : Dict[int, str]
            Output of `schedule()` — task_id -> "DRAM" | "CXL".
        tasks : List[Task]
            Same task list passed to `schedule()`.

        Returns
        -------
        float
            Scalar total latency cost (lower is better).
        """
        task_map = {t.task_id: t for t in tasks}
        total_cost = 0.0
        for task_id, tier in assignment.items():
            task = task_map[task_id]
            latency = self.CXL_LATENCY_NS if tier == "CXL" else self.DRAM_LATENCY_NS
            total_cost += task.memory_sensitivity * latency * task.memory_requirement_mb
        return total_cost

    def validate_assignment(
        self,
        assignment: Dict[int, str],
        tasks: List[Task]
    ) -> bool:
        """
        Validate that an assignment covers all tasks and uses valid tier labels.

        Parameters
        ----------
        assignment : Dict[int, str]
            The assignment dict to validate.
        tasks : List[Task]
            Expected task list.

        Returns
        -------
        bool
            True if valid, raises ValueError otherwise.
        """
        expected_ids = {t.task_id for t in tasks}
        assigned_ids = set(assignment.keys())
        missing = expected_ids - assigned_ids
        if missing:
            raise ValueError(f"Assignment missing task IDs: {missing}")
        invalid_tiers = {
            tid: tier for tid, tier in assignment.items()
            if tier not in ("DRAM", "CXL")
        }
        if invalid_tiers:
            raise ValueError(f"Invalid tier labels in assignment: {invalid_tiers}")
        return True
