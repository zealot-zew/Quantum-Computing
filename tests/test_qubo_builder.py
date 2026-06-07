
"""
test_qubo_builder.py — Unit tests for the QUBO matrix builder.
"""

import numpy as np
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from rqaoa.qubo_builder import (
    build_qubo_from_tasks, DEFAULT_TASKS, TASKS_12, TASKS_16, Task,
    DRAM_LATENCY_NS, CXL_LATENCY_NS, CXL_CAPACITY_MB, CAPACITY_PENALTY_WEIGHT
)


class TestQUBOMatrixShape:
    def test_matrix_is_8x8_for_default_tasks(self) -> None:
        qubo = build_qubo_from_tasks(DEFAULT_TASKS)
        assert qubo.shape == (8, 8), f"Expected (8, 8), got {qubo.shape}"

    def test_matrix_size_matches_task_count(self) -> None:
        small_tasks = DEFAULT_TASKS[:4]
        qubo = build_qubo_from_tasks(small_tasks)
        assert qubo.shape == (4, 4)

    def test_tasks_12_produces_12x12_matrix(self) -> None:
        qubo = build_qubo_from_tasks(TASKS_12)
        assert qubo.shape == (12, 12)

    def test_tasks_16_produces_16x16_matrix(self) -> None:
        qubo = build_qubo_from_tasks(TASKS_16)
        assert qubo.shape == (16, 16)


class TestDiagonalValues:
    def test_diagonal_formula_includes_both_terms(self) -> None:
        """
        Diagonal must combine latency cost AND capacity penalty term.
        Q[i][i] = (sensitivity * latency_diff * mem)
                + penalty * (mem^2 - 2 * CXL_CAPACITY * mem)
        """
        qubo = build_qubo_from_tasks(DEFAULT_TASKS)
        task = DEFAULT_TASKS[0]
        latency_diff = CXL_LATENCY_NS - DRAM_LATENCY_NS

        latency_term = task.memory_sensitivity * latency_diff * task.memory_requirement_mb
        capacity_term = CAPACITY_PENALTY_WEIGHT * (
            task.memory_requirement_mb ** 2
            - 2.0 * CXL_CAPACITY_MB * task.memory_requirement_mb
        )
        expected = latency_term + capacity_term

        assert abs(qubo[0][0] - expected) < 1e-6, (
            f"Expected Q[0][0]={expected:.6f}, got {qubo[0][0]:.6f}."
        )

    def test_diagonal_is_not_just_latency_term(self) -> None:
        """Diagonal must differ from latency-only value."""
        qubo = build_qubo_from_tasks(DEFAULT_TASKS)
        task = DEFAULT_TASKS[0]
        latency_diff = CXL_LATENCY_NS - DRAM_LATENCY_NS
        latency_only = task.memory_sensitivity * latency_diff * task.memory_requirement_mb
        assert abs(qubo[0][0] - latency_only) > 1e-6, (
            "Q[0][0] equals latency-only — capacity diagonal term is missing!"
        )

    def test_high_sensitivity_diagonal_larger_than_low(self) -> None:
        qubo = build_qubo_from_tasks(DEFAULT_TASKS)
        assert qubo[4][4] > qubo[3][3]

    def test_zero_sensitivity_diagonal_is_capacity_penalty_only(self) -> None:
        """Zero sensitivity means latency term = 0, but capacity term remains."""
        tasks = [Task(task_id=0, memory_requirement_mb=500,
                      priority=3, memory_sensitivity=0.0)]
        qubo = build_qubo_from_tasks(tasks, cxl_capacity_mb=4096.0,
                                     penalty_weight=1e-5)
        expected_capacity = 1e-5 * (500.0 ** 2 - 2.0 * 4096.0 * 500.0)
        assert abs(qubo[0][0] - expected_capacity) < 1e-9


class TestOffDiagonalValues:
    def test_upper_triangle_is_nonzero(self) -> None:
        qubo = build_qubo_from_tasks(DEFAULT_TASKS)
        assert np.sum(np.triu(qubo, k=1)) > 0

    def test_lower_triangle_is_all_zeros(self) -> None:
        qubo = build_qubo_from_tasks(DEFAULT_TASKS)
        assert np.all(np.tril(qubo, k=-1) == 0)

    def test_off_diagonal_formula_is_correct(self) -> None:
        """Q[0][1] should equal penalty * 2 * mem_0 * mem_1."""
        qubo = build_qubo_from_tasks(DEFAULT_TASKS)
        mem_0 = DEFAULT_TASKS[0].memory_requirement_mb
        mem_1 = DEFAULT_TASKS[1].memory_requirement_mb
        expected = CAPACITY_PENALTY_WEIGHT * 2.0 * mem_0 * mem_1
        assert abs(qubo[0][1] - expected) < 1e-9



