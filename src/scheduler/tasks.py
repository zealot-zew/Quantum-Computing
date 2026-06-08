"""
Canonical set of 8 tasks for the scheduling problem.

These tasks represent a realistic mix of memory-intensive workloads
with varying sensitivity to memory latency.
"""

from src.scheduler.task_model import Task


# Define the canonical 8-task set
CANONICAL_TASKS = [
    Task(
        task_id=0,
        memory_requirement_mb=512.0,
        priority=5,
        memory_sensitivity=0.9
    ),
    Task(
        task_id=1,
        memory_requirement_mb=256.0,
        priority=3,
        memory_sensitivity=0.7
    ),
    Task(
        task_id=2,
        memory_requirement_mb=1024.0,
        priority=4,
        memory_sensitivity=0.85
    ),
    Task(
        task_id=3,
        memory_requirement_mb=128.0,
        priority=2,
        memory_sensitivity=0.4
    ),
    Task(
        task_id=4,
        memory_requirement_mb=768.0,
        priority=5,
        memory_sensitivity=0.95
    ),
    Task(
        task_id=5,
        memory_requirement_mb=384.0,
        priority=1,
        memory_sensitivity=0.3
    ),
    Task(
        task_id=6,
        memory_requirement_mb=640.0,
        priority=4,
        memory_sensitivity=0.8
    ),
    Task(
        task_id=7,
        memory_requirement_mb=192.0,
        priority=3,
        memory_sensitivity=0.5
    ),
]


# Memory tier capacities (in MB)
DRAM_CAPACITY_MB = 2048.0  # 2 GB DRAM
CXL_CAPACITY_MB = 4096.0   # 4 GB CXL memory

# Memory tier latency characteristics (in nanoseconds)
DRAM_LATENCY_NS = 100.0    # ~80-120 ns typical
CXL_LATENCY_NS = 300.0     # ~200-400+ ns typical


def get_canonical_tasks():
    """
    Returns the canonical set of 8 tasks.

    Returns:
        List of Task objects
    """
    return CANONICAL_TASKS.copy()


def get_total_memory_requirement():
    """
    Calculate total memory requirement across all tasks.

    Returns:
        Total memory in MB
    """
    return sum(task.memory_requirement_mb for task in CANONICAL_TASKS)


def print_task_summary():
    """Print a formatted summary of all tasks."""
    print("=" * 80)
    print("CANONICAL TASK SET SUMMARY")
    print("=" * 80)
    print(f"{'ID':<5} {'Memory (MB)':<12} {'Priority':<10} {'Sensitivity':<12}")
    print("-" * 80)
    for task in CANONICAL_TASKS:
        print(f"{task.task_id:<5} {task.memory_requirement_mb:<12.1f} "
              f"{task.priority:<10} {task.memory_sensitivity:<12.2f}")
    print("-" * 80)
    print(f"Total Memory: {get_total_memory_requirement():.1f} MB")
    print(f"DRAM Capacity: {DRAM_CAPACITY_MB:.1f} MB")
    print(f"CXL Capacity: {CXL_CAPACITY_MB:.1f} MB")
    print("=" * 80)


if __name__ == "__main__":
    print_task_summary()
