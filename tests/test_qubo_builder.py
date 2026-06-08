
"""test_qubo_builder.py — Unit tests for the QUBO matrix builder."""

import numpy as np, pytest, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
from rqaoa.qubo_builder import (
    build_qubo_from_tasks, compute_qubo_cost,num_slack_bits,
    DEFAULT_TASKS, TASKS_12, TASKS_16, Task,
    DRAM_LATENCY_NS, CXL_LATENCY_NS, DRAM_CAPACITY_MB, CAPACITY_PENALTY_WEIGHT
)
def expected_size(tasks):
    from rqaoa.qubo_builder import DRAM_CAPACITY_MB, num_slack_bits
    return len(tasks) + num_slack_bits(DRAM_CAPACITY_MB)


class TestMatrixShape:
    def test_8x8(self):
        assert build_qubo_from_tasks(DEFAULT_TASKS).shape == (
            expected_size(DEFAULT_TASKS),
            expected_size(DEFAULT_TASKS)
        )

    def test_12x12(self):
        assert build_qubo_from_tasks(TASKS_12).shape == (
            expected_size(TASKS_12),
            expected_size(TASKS_12)
        )

    def test_16x16(self):
        assert build_qubo_from_tasks(TASKS_16).shape == (
            expected_size(TASKS_16),
            expected_size(TASKS_16)
        )

    def test_custom_size(self):
        assert build_qubo_from_tasks(DEFAULT_TASKS[:4]).shape == (
            expected_size(DEFAULT_TASKS[:4]),
            expected_size(DEFAULT_TASKS[:4])
        )


class TestDiagonalValues:
    def test_diagonal_includes_both_terms(self):
        Q    = build_qubo_from_tasks(DEFAULT_TASKS)
        task = DEFAULT_TASKS[0]
        diff = CXL_LATENCY_NS - DRAM_LATENCY_NS
        latency_term  = task.memory_sensitivity * diff * task.memory_requirement_mb
        capacity_term = CAPACITY_PENALTY_WEIGHT * (
            task.memory_requirement_mb**2 - 2.0 * DRAM_CAPACITY_MB * task.memory_requirement_mb
        )
        assert abs(Q[0][0] - (latency_term + capacity_term)) < 1e-6

    def test_not_just_latency(self):
        Q    = build_qubo_from_tasks(DEFAULT_TASKS)
        task = DEFAULT_TASKS[0]
        diff = CXL_LATENCY_NS - DRAM_LATENCY_NS
        latency_only = task.memory_sensitivity * diff * task.memory_requirement_mb
        assert abs(Q[0][0] - latency_only) > 1e-6, "Capacity diagonal term is missing!"

    def test_high_sensitivity_costs_more(self):
        Q = build_qubo_from_tasks(DEFAULT_TASKS)
        assert Q[4][4] > Q[3][3]  # task4 sens=0.95 > task3 sens=0.20


class TestOffDiagonal:
    def test_lower_triangle_zero(self):
        Q = build_qubo_from_tasks(DEFAULT_TASKS)
        assert np.all(np.tril(Q, k=-1) == 0)

    def test_upper_triangle_nonzero(self):
        assert np.any(np.triu(build_qubo_from_tasks(DEFAULT_TASKS), k=1)) != 0

    def test_off_diagonal_formula(self):
        Q = build_qubo_from_tasks(DEFAULT_TASKS)
        expected = CAPACITY_PENALTY_WEIGHT * 2.0 * DEFAULT_TASKS[0].memory_requirement_mb \
                                                  * DEFAULT_TASKS[1].memory_requirement_mb
        assert abs(Q[0][1] - expected) < 1e-9


class TestCostComputation:
    def test_all_dram_lower_cost_than_all_cxl(self):
        Q           = build_qubo_from_tasks(DEFAULT_TASKS)
        all_dram    = {i: 0 for i in range(8)}
        all_cxl     = {i: 1 for i in range(8)}
        assert compute_qubo_cost(all_dram, Q) < compute_qubo_cost(all_cxl, Q)

    def test_cost_is_non_negative_for_all_dram(self):
        Q = build_qubo_from_tasks(DEFAULT_TASKS)
        assert compute_qubo_cost({i: 0 for i in range(8)}, Q) >= 0
