"""
Scheduler module for quantum-assisted CXL-aware scheduling.

This module contains the task model and various scheduling algorithms.
"""

from src.scheduler.task_model import Task
from src.scheduler.tasks import (
    CANONICAL_TASKS,
    DRAM_CAPACITY_MB,
    CXL_CAPACITY_MB,
    DRAM_LATENCY_NS,
    CXL_LATENCY_NS,
    get_canonical_tasks,
    get_total_memory_requirement,
    print_task_summary
)

__all__ = [
    'Task',
    'CANONICAL_TASKS',
    'DRAM_CAPACITY_MB',
    'CXL_CAPACITY_MB',
    'DRAM_LATENCY_NS',
    'CXL_LATENCY_NS',
    'get_canonical_tasks',
    'get_total_memory_requirement',
    'print_task_summary',
]
