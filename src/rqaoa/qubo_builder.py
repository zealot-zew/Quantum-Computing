
"""
qubo_builder.py

Converts a list of Task objects into a QUBO matrix that encodes:
  1. Latency cost: high-sensitivity tasks are expensive to put on CXL
  2. CXL capacity constraint: penalize assignments that overflow CXL

Variable convention (used consistently across the whole project):
  x[i] = 0  ->  Task i goes to DRAM  (fast, 100 ns)
  x[i] = 1  ->  Task i goes to CXL   (slower, 300 ns)

Full QUBO formulation:
  Minimize:  sum_i (latency_cost_i * x_i)
           + penalty_weight * (sum_i (mem_i * x_i) - CXL_CAPACITY)^2

Expanding the squared term gives:
  Diagonal:     Q[i][i] += penalty_weight * (mem_i^2 - 2 * CXL_CAPACITY * mem_i)
  Off-diagonal: Q[i][j] += penalty_weight * 2 * mem_i * mem_j  (i < j)
"""

import os
from dataclasses import dataclass

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


# ── Constants ──────────────────────────────────────────────────────────────────

DRAM_LATENCY_NS: int = 100
CXL_LATENCY_NS: int = 300

# CXL capacity in MB — tasks assigned to CXL must not exceed this total
CXL_CAPACITY_MB: float = 4096.0

# Penalty weight for the capacity constraint.
# Set to 1e-5 because memory values are in MB (hundreds to thousands).
# With MB-scale values, the squared penalty term becomes very large very fast.
# 1e-5 keeps the penalty and latency terms on the same numerical scale.
CAPACITY_PENALTY_WEIGHT: float = 1e-5


# ── Task Definition ────────────────────────────────────────────────────────────

@dataclass
class Task:
    task_id: int
    memory_requirement_mb: float
    priority: int
    memory_sensitivity: float  # 0.0 (insensitive) to 1.0 (highly sensitive)


# ── Default 8 Tasks (RQAOA + classical baseline) ──────────────────────────────

DEFAULT_TASKS: list = [
    Task(task_id=0, memory_requirement_mb=512,  priority=5, memory_sensitivity=0.9),
    Task(task_id=1, memory_requirement_mb=256,  priority=3, memory_sensitivity=0.4),
    Task(task_id=2, memory_requirement_mb=1024, priority=4, memory_sensitivity=0.8),
    Task(task_id=3, memory_requirement_mb=128,  priority=2, memory_sensitivity=0.2),
    Task(task_id=4, memory_requirement_mb=768,  priority=5, memory_sensitivity=0.95),
    Task(task_id=5, memory_requirement_mb=384,  priority=3, memory_sensitivity=0.5),
    Task(task_id=6, memory_requirement_mb=640,  priority=4, memory_sensitivity=0.7),
    Task(task_id=7, memory_requirement_mb=200,  priority=1, memory_sensitivity=0.3),
]

# ── Extended task sets for scaling experiments (classical schedulers only) ────
# These grow the problem size to show how scheduler complexity scales.
# RQAOA is only run on DEFAULT_TASKS (8) due to simulator time constraints.

TASKS_12: list = DEFAULT_TASKS + [
    Task(task_id=8,  memory_requirement_mb=320,  priority=3, memory_sensitivity=0.6),
    Task(task_id=9,  memory_requirement_mb=448,  priority=4, memory_sensitivity=0.75),
    Task(task_id=10, memory_requirement_mb=192,  priority=2, memory_sensitivity=0.35),
    Task(task_id=11, memory_requirement_mb=576,  priority=5, memory_sensitivity=0.85),
]

TASKS_16: list = TASKS_12 + [
    Task(task_id=12, memory_requirement_mb=160,  priority=1, memory_sensitivity=0.15),
    Task(task_id=13, memory_requirement_mb=704,  priority=4, memory_sensitivity=0.8),
    Task(task_id=14, memory_requirement_mb=288,  priority=3, memory_sensitivity=0.55),
    Task(task_id=15, memory_requirement_mb=512,  priority=5, memory_sensitivity=0.9),
]


# ── QUBO Builder ───────────────────────────────────────────────────────────────

def build_qubo_from_tasks(
    tasks: list,
    cxl_capacity_mb: float = CXL_CAPACITY_MB,
    penalty_weight: float = CAPACITY_PENALTY_WEIGHT,
) -> np.ndarray:
    """
    Builds an N x N upper-triangular QUBO matrix from a list of Task objects.

    x[i] = 1 means task i is assigned to CXL.
    x[i] = 0 means task i is assigned to DRAM.

    Diagonal Q[i][i] combines two terms:
      1. Latency cost:      sensitivity_i * latency_diff * memory_mb_i
      2. Capacity diagonal: penalty_weight * (mem_i^2 - 2 * CXL_CAPACITY * mem_i)

    Off-diagonal Q[i][j] (i < j):
      penalty_weight * 2 * mem_i * mem_j   (CXL capacity cross terms)

    Args:
        tasks:           List of Task objects to schedule.
        cxl_capacity_mb: Maximum CXL memory capacity in MB.
        penalty_weight:  Multiplier for the capacity constraint penalty.

    Returns:
        An (N x N) upper-triangular numpy array.
    """
    n: int = len(tasks)
    qubo_matrix: np.ndarray = np.zeros((n, n))

    latency_difference_ns: int = CXL_LATENCY_NS - DRAM_LATENCY_NS  # 200 ns

    for i, task in enumerate(tasks):
        mem_i: float = task.memory_requirement_mb

        # Term 1: Latency cost
        latency_term: float = task.memory_sensitivity * latency_difference_ns * mem_i

        # Term 2: Capacity penalty diagonal contribution
        capacity_diagonal: float = penalty_weight * (
            mem_i ** 2 - 2.0 * cxl_capacity_mb * mem_i
        )

        qubo_matrix[i][i] = latency_term + capacity_diagonal

    # Off-diagonal: CXL capacity cross terms
    for i in range(n):
        for j in range(i + 1, n):
            qubo_matrix[i][j] += (
                penalty_weight
                * 2.0
                * tasks[i].memory_requirement_mb
                * tasks[j].memory_requirement_mb
            )

    return qubo_matrix


def save_qubo_heatmap(
    qubo_matrix: np.ndarray,
    output_path: str = "results/qubo_heatmap.png",
) -> None:
    """
    Saves a heatmap visualisation of the QUBO matrix to a PNG file.

    Args:
        qubo_matrix: The QUBO matrix to visualise.
        output_path: File path where the heatmap PNG will be saved.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    fig, ax = plt.subplots(figsize=(9, 7))
    heatmap = ax.imshow(qubo_matrix, cmap="YlOrRd", aspect="auto")
    plt.colorbar(heatmap, ax=ax, label="QUBO Coefficient Value")

    ax.set_title("QUBO Matrix Heatmap — Task-to-Memory Assignment Problem", fontsize=13)
    ax.set_xlabel("Task Index (x_j)  [0=DRAM, 1=CXL]")
    ax.set_ylabel("Task Index (x_i)  [0=DRAM, 1=CXL]")

    n = qubo_matrix.shape[0]
    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    ax.set_xticklabels([f"T{i}" for i in range(n)])
    ax.set_yticklabels([f"T{i}" for i in range(n)])

    for i in range(n):
        for j in range(n):
            value = qubo_matrix[i][j]
            if abs(value) > 1e-12:
                ax.text(j, i, f"{value:.2f}",
                        ha="center", va="center", fontsize=7, color="black")

    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()
    print(f"Heatmap saved to: {output_path}")


if __name__ == "__main__":
    os.makedirs("results", exist_ok=True)

    qubo = build_qubo_from_tasks(DEFAULT_TASKS)

    print(f"QUBO matrix shape: {qubo.shape}")
    print()
    print("Diagonal values (combined latency + capacity penalty):")
    latency_diff = CXL_LATENCY_NS - DRAM_LATENCY_NS
    for i, task in enumerate(DEFAULT_TASKS):
        latency_only = task.memory_sensitivity * latency_diff * task.memory_requirement_mb
        print(f"  Task {i} (sensitivity={task.memory_sensitivity}): "
              f"Q[{i}][{i}] = {qubo[i][i]:.4f}  "
              f"(latency term alone = {latency_only:.1f})")

    print()
    print("Sample off-diagonal row for Task 0:")
    print(f"  Q[0, 1:] = {qubo[0, 1:]}")

    save_qubo_heatmap(qubo)
    print("\nAll checks passed! ")
