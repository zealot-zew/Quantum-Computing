
"""(changed)test_qubo_builder.py — Unit tests for the simplified QUBO builder."""

import numpy as np, pytest, sys, os
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from rqaoa.qubo_builder import (
    build_qubo_from_tasks, compute_qubo_cost,
    DEFAULT_TASKS, TASKS_12, TASKS_16, Task,
    DRAM_LATENCY_NS, CXL_LATENCY_NS, DRAM_CAPACITY_MB, CAPACITY_PENALTY_WEIGHT
)


class TestMatrixShape:
    def test_8x8(self):
        assert build_qubo_from_tasks(DEFAULT_TASKS).shape == (8, 8)

    def test_12x12(self):
        assert build_qubo_from_tasks(TASKS_12).shape == (12, 12)

    def test_16x16(self):
        assert build_qubo_from_tasks(TASKS_16).shape == (16, 16)

    def test_custom_size(self):
        assert build_qubo_from_tasks(DEFAULT_TASKS[:4]).shape == (4, 4)


class TestDiagonalValues:
    def test_diagonal_includes_both_terms(self):
        """
        Diagonal = latency term + full capacity term (including -2K correction).
        Formula: lambda * m_i * (m_i - 2*K)  where K = total_mem - dram_cap.
        """
        Q    = build_qubo_from_tasks(DEFAULT_TASKS)
        task = DEFAULT_TASKS[0]
        diff = CXL_LATENCY_NS - DRAM_LATENCY_NS

        S = sum(t.memory_requirement_mb for t in DEFAULT_TASKS)
        K = S - DRAM_CAPACITY_MB
        m = task.memory_requirement_mb

        latency_term  = task.memory_sensitivity * diff * m
        capacity_term = CAPACITY_PENALTY_WEIGHT * m * (m - 2.0 * K)

        assert abs(Q[0][0] - (latency_term + capacity_term)) < 1e-6

    def test_not_just_latency(self):
        Q    = build_qubo_from_tasks(DEFAULT_TASKS)
        task = DEFAULT_TASKS[0]
        diff = CXL_LATENCY_NS - DRAM_LATENCY_NS
        latency_only = task.memory_sensitivity * diff * task.memory_requirement_mb
        assert abs(Q[0][0] - latency_only) > 1e-6

    def test_high_sensitivity_costs_more(self):
        Q = build_qubo_from_tasks(DEFAULT_TASKS)
        assert Q[4][4] > Q[3][3]


class TestOffDiagonal:
    def test_lower_triangle_zero(self):
        Q = build_qubo_from_tasks(DEFAULT_TASKS)
        assert np.all(np.tril(Q, k=-1) == 0)

    def test_upper_triangle_nonzero(self):
        Q = build_qubo_from_tasks(DEFAULT_TASKS)
        assert np.sum(np.triu(Q, k=1)) != 0

    def test_off_diagonal_formula(self):
        """Off-diagonal = lambda * 2 * m_i * m_j. No K term."""
        Q        = build_qubo_from_tasks(DEFAULT_TASKS)
        expected = CAPACITY_PENALTY_WEIGHT * 2.0 \
                 * DEFAULT_TASKS[0].memory_requirement_mb \
                 * DEFAULT_TASKS[1].memory_requirement_mb
        assert abs(Q[0][1] - expected) < 1e-9


class TestCostComputation:
    def test_smart_beats_all_cxl(self):
        """High-sensitivity tasks in DRAM should cost less than all-CXL."""
        from rqaoa.qubo_builder import verify_qubo_sanity, tune_lambda
        lam = tune_lambda(DEFAULT_TASKS, DRAM_CAPACITY_MB, verbose=False)
        Q   = build_qubo_from_tasks(DEFAULT_TASKS, penalty_weight=lam)
        assert verify_qubo_sanity(DEFAULT_TASKS, Q, DRAM_CAPACITY_MB, verbose=False)

    def test_cost_non_negative_all_dram(self):
        from rqaoa.qubo_builder import tune_lambda
        lam = tune_lambda(DEFAULT_TASKS, DRAM_CAPACITY_MB, verbose=False)
        Q   = build_qubo_from_tasks(DEFAULT_TASKS, penalty_weight=lam)
        assert compute_qubo_cost({i: 0 for i in range(8)}, Q) >= 0
