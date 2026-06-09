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
from src.scheduler.scheduler_interface import BaseScheduler
from src.scheduler.fcfs_scheduler import FCFSScheduler
from src.scheduler.round_robin_scheduler import RoundRobinScheduler
from src.scheduler.greedy_scheduler import GreedyScheduler
from src.scheduler.greedy_priority_scheduler import GreedyPriorityScheduler

__all__ = [
    # Task model
    'Task',
    # Task data
    'CANONICAL_TASKS',
    'DRAM_CAPACITY_MB',
    'CXL_CAPACITY_MB',
    'DRAM_LATENCY_NS',
    'CXL_LATENCY_NS',
    'get_canonical_tasks',
    'get_total_memory_requirement',
    'print_task_summary',
    # Schedulers
    'BaseScheduler',
    'FCFSScheduler',
    'RoundRobinScheduler',
    'GreedyScheduler',
    'GreedyPriorityScheduler',
]
