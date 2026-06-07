"""
System metrics and benchmark evaluation module.
"""


def calculate_avg_completion_time(tasks):
    """
    tasks = [
        {"completion_time": 10},
        {"completion_time": 15}
    ]
    """

    if not tasks:
        return 0

    total = sum(task["completion_time"] for task in tasks)

    return total / len(tasks)


def calculate_makespan(tasks):
    """
    Returns longest completion time.
    """

    if not tasks:
        return 0

    return max(task["completion_time"] for task in tasks)


def calculate_latency_cost(tasks):
    """
    Sum of all task latencies.
    """

    if not tasks:
        return 0

    return sum(task["latency"] for task in tasks)


def calculate_dram_utilization(used_memory, total_memory):
    """
    Returns DRAM utilization percentage.
    """

    if total_memory == 0:
        return 0

    return (used_memory / total_memory) * 100