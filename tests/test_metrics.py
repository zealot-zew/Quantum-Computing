import sys
import os

sys.path.append(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..")
    )
)

from src.evaluation.metrics import (
    calculate_avg_completion_time,
    calculate_makespan,
    calculate_dram_utilization,
    calculate_latency_cost,
    compute_total_latency_cost,
)

from src.scheduler.task_model import Task


def test_average_completion_time():
    durations = [
        1.0,
        2.0,
        3.0,
    ]

    assert calculate_avg_completion_time(
        durations
    ) == 2.0


def test_average_completion_time_empty():
    assert calculate_avg_completion_time(
        []
    ) == 0.0


def test_makespan():
    starts = [
        0.0,
        2.0,
        4.0,
    ]

    ends = [
        1.0,
        5.0,
        7.0,
    ]

    assert calculate_makespan(
        starts,
        ends,
    ) == 7.0


def test_dram_utilization():
    assert (
        calculate_dram_utilization(
            1024.0,
            2048.0,
        )
        == 50.0
    )


def test_dram_utilization_full():
    assert (
        calculate_dram_utilization(
            2048.0,
            2048.0,
        )
        == 100.0
    )


def test_latency_cost_dram():
    cost = calculate_latency_cost(
        memory_requirement_mb=100.0,
        memory_sensitivity=1.0,
        assigned_tier="DRAM",
    )

    assert cost == 10000.0


def test_latency_cost_cxl():
    cost = calculate_latency_cost(
        memory_requirement_mb=100.0,
        memory_sensitivity=1.0,
        assigned_tier="CXL",
    )

    assert cost == 30000.0


def test_total_latency_cost():
    tasks = [
        Task(
            task_id=0,
            memory_requirement_mb=100.0,
            priority=1,
            memory_sensitivity=1.0,
        ),
        Task(
            task_id=1,
            memory_requirement_mb=200.0,
            priority=1,
            memory_sensitivity=0.5,
        ),
    ]

    assignment = {
        0: "DRAM",
        1: "CXL",
    }

    expected = (
        100.0 * 1.0 * 100.0
        + 200.0 * 0.5 * 300.0
    )

    assert (
        compute_total_latency_cost(
            assignment,
            tasks,
        )
        == expected
    )