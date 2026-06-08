"""
Regression tests for Day 2 classical scheduler implementations.
"""

from typing import Dict

import pytest

from src.scheduler import CXL_CAPACITY_MB, DRAM_CAPACITY_MB, get_canonical_tasks
from src.scheduler.fcfs_scheduler import FCFSScheduler
from src.scheduler.greedy_scheduler import GreedyScheduler
from src.scheduler.greedy_priority_scheduler import GreedyPriorityScheduler
from src.scheduler.round_robin_scheduler import RoundRobinScheduler
from src.scheduler.task_model import Task


@pytest.mark.parametrize(
    "scheduler",
    [
        FCFSScheduler(DRAM_CAPACITY_MB, CXL_CAPACITY_MB),
        RoundRobinScheduler(DRAM_CAPACITY_MB, CXL_CAPACITY_MB),
        GreedyScheduler(DRAM_CAPACITY_MB, CXL_CAPACITY_MB),
        GreedyPriorityScheduler(DRAM_CAPACITY_MB, CXL_CAPACITY_MB),
    ],
)
def test_scheduler_assigns_every_task(scheduler: object) -> None:
    """Every classical scheduler should assign every canonical task once."""
    tasks = get_canonical_tasks()

    assignment: Dict[int, str] = scheduler.schedule(tasks)  # type: ignore[attr-defined]

    assert set(assignment.keys()) == {task.task_id for task in tasks}
    assert set(assignment.values()).issubset({"DRAM", "CXL"})


@pytest.mark.parametrize(
    "scheduler",
    [
        FCFSScheduler(DRAM_CAPACITY_MB, CXL_CAPACITY_MB),
        RoundRobinScheduler(DRAM_CAPACITY_MB, CXL_CAPACITY_MB),
        GreedyScheduler(DRAM_CAPACITY_MB, CXL_CAPACITY_MB),
        GreedyPriorityScheduler(DRAM_CAPACITY_MB, CXL_CAPACITY_MB),
    ],
)
def test_scheduler_respects_memory_capacity(scheduler: object) -> None:
    """Scheduler assignments must stay within DRAM and CXL capacities."""
    tasks = get_canonical_tasks()
    assignment: Dict[int, str] = scheduler.schedule(tasks)  # type: ignore[attr-defined]

    dram_used_mb = sum(
        task.memory_requirement_mb
        for task in tasks
        if assignment[task.task_id] == "DRAM"
    )
    cxl_used_mb = sum(
        task.memory_requirement_mb
        for task in tasks
        if assignment[task.task_id] == "CXL"
    )

    assert dram_used_mb <= DRAM_CAPACITY_MB
    assert cxl_used_mb <= CXL_CAPACITY_MB


def test_schedulers_reject_oversized_task_set() -> None:
    """Schedulers should reject tasks that exceed combined tier capacity."""
    oversized_tasks = [
        Task(
            task_id=0,
            memory_requirement_mb=DRAM_CAPACITY_MB + CXL_CAPACITY_MB + 1.0,
            priority=1,
            memory_sensitivity=0.5,
        )
    ]

    for scheduler in [
        FCFSScheduler(DRAM_CAPACITY_MB, CXL_CAPACITY_MB),
        RoundRobinScheduler(DRAM_CAPACITY_MB, CXL_CAPACITY_MB),
        GreedyScheduler(DRAM_CAPACITY_MB, CXL_CAPACITY_MB),
        GreedyPriorityScheduler(DRAM_CAPACITY_MB, CXL_CAPACITY_MB),
    ]:
        with pytest.raises(ValueError, match="exceeds"):
            scheduler.schedule(oversized_tasks)
