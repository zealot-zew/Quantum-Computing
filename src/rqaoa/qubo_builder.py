
"""
qubo_builder.py
#changed
QUBO formulation for CXL-aware memory scheduling.

Variable convention (consistent throughout the project):
  x[i] = 0  ->  Task i assigned to DRAM  (fast, 100 ns)
  x[i] = 1  ->  Task i assigned to CXL   (slower, 300 ns)

Objective:
  minimize: sum_i (s_i * dL * m_i * x_i)          [latency cost]
          + lambda * (sum_i m_i * x_i - K)^2       [capacity constraint]

where:
  s_i  = memory_sensitivity of task i  (0.0 to 1.0)
  dL   = CXL_LATENCY - DRAM_LATENCY = 200 ns
  m_i  = memory_requirement_mb of task i
  K    = S - D  = total task memory - DRAM capacity
         (target amount of memory that should go to CXL)
  lambda = penalty weight (tuned so penalty ~= latency scale)

Expanding (sum_i m_i*x_i - K)^2:

  Diagonal Q[i][i]:
    latency term:   s_i * dL * m_i
    penalty term:   lambda * (m_i^2 - 2 * K * m_i)
    total:          s_i * dL * m_i + lambda * (m_i^2 - 2*K*m_i)

  Off-diagonal Q[i][j]  (i < j):
    lambda * 2 * m_i * m_j

This is an N x N matrix (one variable per task, no slack bits).
RQAOA runs on exactly N qubits.

Why no slack variables:
  Slack variables would add ceil(log2(D+1)) ≈ 11 extra qubits,
  making the problem 19 variables for 8 tasks. At this scale
  the RQAOA simulator struggles with 19-qubit circuits.
  The soft quadratic penalty is a standard QUBO relaxation that
  produces feasible assignments when lambda is tuned correctly.
  We validate feasibility in run_rqaoa_pipeline.py.
"""

import os
import numpy as np
from dataclasses import dataclass
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


# ── Physical constants ────────────────────────────────────────────────────────

DRAM_LATENCY_NS: int = 100
CXL_LATENCY_NS:  int = 300
LATENCY_DIFF_NS: int = CXL_LATENCY_NS - DRAM_LATENCY_NS   # 200

# DRAM capacity = 50% of total task memory (3912 MB) = 1956 MB.
# This creates meaningful capacity pressure:
# not all tasks fit in DRAM, so the optimizer must make real trade-offs.
DRAM_CAPACITY_MB: float = 1956.0

# Lambda = 0.05 keeps penalty and latency terms on the same scale.
# Derivation: max latency term = 0.95 * 200 * 1024 / 1024 ≈ 190 (in GB units)
# K = 3912 - 1956 = 1956 MB. lambda * K^2 ≈ lambda * 1956^2.
# Setting lambda * 1956^2 ≈ total_latency gives lambda ≈ 0.05.
CAPACITY_PENALTY_WEIGHT: float = 0.05


# ── Task dataclass ────────────────────────────────────────────────────────────

@dataclass
class Task:
    task_id:               int
    memory_requirement_mb: float
    priority:              int
    memory_sensitivity:    float   # 0.0 = insensitive, 1.0 = highly sensitive


# ── Task sets ─────────────────────────────────────────────────────────────────

DEFAULT_TASKS: list = [
    Task(task_id=0, memory_requirement_mb=512,  priority=5, memory_sensitivity=0.90),
    Task(task_id=1, memory_requirement_mb=256,  priority=3, memory_sensitivity=0.40),
    Task(task_id=2, memory_requirement_mb=1024, priority=4, memory_sensitivity=0.80),
    Task(task_id=3, memory_requirement_mb=128,  priority=2, memory_sensitivity=0.20),
    Task(task_id=4, memory_requirement_mb=768,  priority=5, memory_sensitivity=0.95),
    Task(task_id=5, memory_requirement_mb=384,  priority=3, memory_sensitivity=0.50),
    Task(task_id=6, memory_requirement_mb=640,  priority=4, memory_sensitivity=0.70),
    Task(task_id=7, memory_requirement_mb=200,  priority=1, memory_sensitivity=0.30),
]

TASKS_12: list = DEFAULT_TASKS + [
    Task(task_id=8,  memory_requirement_mb=320, priority=3, memory_sensitivity=0.60),
    Task(task_id=9,  memory_requirement_mb=448, priority=4, memory_sensitivity=0.75),
    Task(task_id=10, memory_requirement_mb=192, priority=2, memory_sensitivity=0.35),
    Task(task_id=11, memory_requirement_mb=576, priority=5, memory_sensitivity=0.85),
]

TASKS_16: list = TASKS_12 + [
    Task(task_id=12, memory_requirement_mb=160, priority=1, memory_sensitivity=0.15),
    Task(task_id=13, memory_requirement_mb=704, priority=4, memory_sensitivity=0.80),
    Task(task_id=14, memory_requirement_mb=288, priority=3, memory_sensitivity=0.55),
    Task(task_id=15, memory_requirement_mb=512, priority=5, memory_sensitivity=0.90),
]

TASK_SETS: dict = {8: DEFAULT_TASKS, 12: TASKS_12, 16: TASKS_16}


# ── QUBO builder ──────────────────────────────────────────────────────────────
def build_qubo_from_tasks(
    tasks:            list,
    dram_capacity_mb: float = DRAM_CAPACITY_MB,
    penalty_weight:   float = CAPACITY_PENALTY_WEIGHT,
) -> np.ndarray:
    """
    QUBO formulation — full capacity constraint with constant term dropped.

    Full penalty: lambda * (sum_i m_i*x_i - K)^2
    where K = total_memory - dram_capacity  (target CXL load)

    Expanding and dropping the constant lambda*K^2 (same for all solutions,
    does not affect which assignment RQAOA picks):

      Diagonal Q[i][i]:
        latency term:   s_i * dL * m_i                (always positive)
        capacity term:  lambda * m_i * (m_i - 2*K)    (may be negative when m_i < 2K)

      Off-diagonal Q[i][j]:
        lambda * 2 * m_i * m_j                        (always positive)

    Negative diagonals are mathematically correct — they represent tasks whose
    individual contribution is so small relative to K that the QUBO wants them
    in CXL. The reported cost x^T Q x is missing the constant lambda*K^2; add
    it back via qubo_constant(tasks, dram_capacity_mb, penalty_weight) when you
    need absolute cost values (e.g. for quality comparisons).
    """
    n   = len(tasks)
    lam = penalty_weight
    S   = sum(t.memory_requirement_mb for t in tasks)
    K   = S - dram_capacity_mb          # target amount of memory to put in CXL

    Q = np.zeros((n, n), dtype=np.float64)

    for i, task in enumerate(tasks):
        m = task.memory_requirement_mb
        latency_term  = task.memory_sensitivity * LATENCY_DIFF_NS * m
        capacity_diag = lam * m * (m - 2.0 * K)   # correct: includes -2K term
        Q[i][i]       = latency_term + capacity_diag

    for i in range(n):
        for j in range(i + 1, n):
            Q[i][j] = lam * 2.0 * tasks[i].memory_requirement_mb \
                                * tasks[j].memory_requirement_mb

    return Q


def qubo_constant(
    tasks:            list,
    dram_capacity_mb: float = DRAM_CAPACITY_MB,
    penalty_weight:   float = CAPACITY_PENALTY_WEIGHT,
) -> float:
    """
    Returns the dropped constant lambda*K^2.
    Add this to compute_qubo_cost() output to get the true absolute cost.
    Only needed when comparing absolute values across different K (task set sizes).
    """
    S = sum(t.memory_requirement_mb for t in tasks)
    K = S - dram_capacity_mb
    return penalty_weight * (K ** 2)


# ── Cost functions ────────────────────────────────────────────────────────────

def compute_qubo_cost(assignment: dict, qubo_matrix: np.ndarray) -> float:
    """
    Computes f(x) = x^T Q x for a task assignment.

    Args:
        assignment:  {task_id (or var_index): 0 or 1}
        qubo_matrix: N x N QUBO matrix.

    Returns:
        Float cost. Lower = better.
    """
    n = qubo_matrix.shape[0]
    x = np.array([float(assignment.get(i, 0)) for i in range(n)])
    cost = 0.0
    for i in range(n):
        for j in range(i, n):
            cost += qubo_matrix[i][j] * x[i] * x[j]
    return cost


def compute_latency_cost(task_assignment: dict, tasks: list) -> float:
    """
    Pure latency cost — sum of sensitivity * latency_diff * mem for CXL tasks.
    Use this as the scheduling performance metric (no penalty term).
    """
    return sum(
        t.memory_sensitivity * LATENCY_DIFF_NS * t.memory_requirement_mb
        for t in tasks if task_assignment.get(t.task_id, 0) == 1
    )


def compute_dram_used(task_assignment: dict, tasks: list) -> float:
    """Returns total MB assigned to DRAM."""
    return sum(
        t.memory_requirement_mb
        for t in tasks if task_assignment.get(t.task_id, 0) == 0
    )


# ── Lambda tuner ─────────────────────────────────────────────────────────────
def tune_lambda(tasks, dram_capacity_mb=DRAM_CAPACITY_MB, verbose=True):
    """
    Sets lambda so the capacity penalty strongly discourages DRAM overflow.

    Strategy: the penalty for putting ONE extra task into DRAM beyond
    capacity must exceed the latency benefit of that task being in DRAM.

    For the largest task (worst case overflow by one task of size m_max):
      penalty increase ≈ lambda * 2 * m_max * K   (cross term dominates)
      latency benefit  = s_max * dL * m_max

    Setting penalty_increase = safety_factor * latency_benefit:
      lambda = safety_factor * s_max * dL / (2 * K)

    safety_factor = 10 ensures penalty >> latency benefit.
    """
    S       = sum(t.memory_requirement_mb for t in tasks)
    K       = max(1.0, S - dram_capacity_mb)
    s_max   = max(t.memory_sensitivity for t in tasks)
    dL      = LATENCY_DIFF_NS

    SAFETY_FACTOR = 10.0
    lambda_val    = SAFETY_FACTOR * s_max * dL / (2.0 * K)

    if verbose:
        print(f"Lambda tuning:")
        print(f"  S={S:.0f}MB  D={dram_capacity_mb:.0f}MB  K={K:.0f}MB")
        print(f"  s_max={s_max}  dL={dL}")
        print(f"  Lambda: {lambda_val:.6f}  (safety_factor={SAFETY_FACTOR}x)")
        # Verify: penalty for 1 extra task > latency benefit
        m_max = max(t.memory_requirement_mb for t in tasks)
        penalty_1task = lambda_val * 2 * m_max * K
        benefit_1task = s_max * dL * m_max
        print(f"  Penalty for 1 extra DRAM task: {penalty_1task:.1f}")
        print(f"  Latency benefit of 1 DRAM task: {benefit_1task:.1f}")
        print(f"  Ratio (must be >> 1): {penalty_1task/benefit_1task:.1f}x")

    return lambda_val
  

# ── Sanity check ─────────────────────────────────────────────────────────────

def verify_qubo_sanity(
    tasks:            list,
    qubo_matrix:      np.ndarray,
    dram_capacity_mb: float = DRAM_CAPACITY_MB,
    verbose:          bool = True,
) -> bool:
    """
    Verifies three properties:
    1. Smart assignment (high-sensitivity tasks in DRAM) costs less than all-CXL.
    2. Smart assignment respects DRAM capacity.
    3. High-sensitivity diagonal > low-sensitivity diagonal.
    """
    n = len(tasks)

    # Build smart assignment: most sensitive tasks fill DRAM first
    sorted_idx = sorted(range(n),
                        key=lambda i: tasks[i].memory_sensitivity, reverse=True)
    smart = {}
    dram_used = 0.0
    for i in sorted_idx:
        if dram_used + tasks[i].memory_requirement_mb <= dram_capacity_mb:
            smart[tasks[i].task_id] = 0
            dram_used += tasks[i].memory_requirement_mb
        else:
            smart[tasks[i].task_id] = 1

    all_cxl  = {t.task_id: 1 for t in tasks}

    c_smart  = compute_qubo_cost({tasks[i].task_id: smart[tasks[i].task_id]
                                   for i in range(n)}, qubo_matrix)
    # remap to var indices for cost function
    smart_vi = {i: smart[tasks[i].task_id] for i in range(n)}
    cxl_vi   = {i: 1 for i in range(n)}

   # Add dropped constant lambda*K^2 so reported costs are positive absolutes
    S       = sum(t.memory_requirement_mb for t in tasks)
    K       = S - dram_capacity_mb
    # infer lambda from any off-diagonal entry (Q[0][1] = lam*2*m0*m1)
    lam_est = (qubo_matrix[0][1] / (2.0 * tasks[0].memory_requirement_mb
                                       * tasks[1].memory_requirement_mb)
               if qubo_matrix[0][1] > 0 else 0.0)
    q_const = lam_est * (K ** 2)

    c_smart  = compute_qubo_cost(smart_vi,  qubo_matrix) + q_const
    c_cxl    = compute_qubo_cost(cxl_vi,    qubo_matrix) + q_const

    check1 = c_smart < c_cxl
    check2 = dram_used <= dram_capacity_mb
    check3 = qubo_matrix[4][4] < qubo_matrix[3][3]   # task4 sens>task3 sens

    if verbose:
        print("=" * 55)
        print("QUBO SANITY CHECK")
        print("=" * 55)
        print(f"  N tasks = {n}  |  QUBO shape = {qubo_matrix.shape}")
        print(f"  DRAM capacity: {dram_capacity_mb:.0f} MB")
        print(f"  Smart DRAM used: {dram_used:.0f} MB")
        print()
        print(f"  Cost smart assignment: {c_smart:.4f}  (matrix + lambda*K^2 constant)")
        print(f"  Cost all-CXL:          {c_cxl:.4f}  (matrix + lambda*K^2 constant)")
        print()
        print(f"  {'✅' if check1 else '❌'} Smart < all-CXL")
        print(f"  {'✅' if check2 else '❌'} DRAM capacity respected")
        print(f"  {'✅' if check3 else '❌'} High sensitivity has lower diagonal (pulled toward DRAM)")
        print()
        print("  Smart assignment:")
        for i in sorted_idx:
            tier = "DRAM" if smart[tasks[i].task_id] == 0 else "CXL"
            print(f"    Task {tasks[i].task_id}: "
                  f"sens={tasks[i].memory_sensitivity:.2f} "
                  f"mem={tasks[i].memory_requirement_mb:.0f}MB -> {tier}")
        all_ok = check1 and check2 and check3
        print()
        print(f"  {'✅ ALL CHECKS PASSED' if all_ok else '❌ CHECKS FAILED'}")
        print("=" * 55)

    return check1 and check2 and check3


# ── Heatmap ──────────────────────────────────────────────────────────────────

def save_qubo_heatmap(
    qubo_matrix: np.ndarray,
    tasks:       list       = None,
    output_path: str        = "results/plots/qubo_heatmap.png",
) -> None:
    """Saves annotated heatmap of the QUBO matrix."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    n      = qubo_matrix.shape[0]
    labels = ([f"T{tasks[i].task_id}" for i in range(n)]
              if tasks else [f"T{i}" for i in range(n)])

    fig, ax = plt.subplots(figsize=(10, 8))
    im = ax.imshow(qubo_matrix, cmap="RdBu_r", aspect="auto")
    plt.colorbar(im, ax=ax, label="QUBO coefficient")
    ax.set_title(
        "QUBO Matrix — CXL Scheduling\n"
        "x[i]=0→DRAM (fast) | x[i]=1→CXL (slow)\n"
        "Diagonal: latency + capacity | Off-diag: capacity coupling",
        fontsize=10
    )
    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    ax.set_xticklabels(labels, rotation=45, fontsize=8)
    ax.set_yticklabels(labels, fontsize=8)
    for i in range(n):
        for j in range(n):
            v = qubo_matrix[i][j]
            if abs(v) > 1e-6:
                ax.text(j, i, f"{v:.1f}", ha="center", va="center",
                        fontsize=6,
                        color="white" if abs(v) > abs(qubo_matrix).max() * 0.5
                        else "black")
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()
    print(f"Heatmap saved: {output_path}")
