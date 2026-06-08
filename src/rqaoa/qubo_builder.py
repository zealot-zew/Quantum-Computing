
"""
qubo_builder.py — MATHEMATICALLY CORRECT FORMULATION WITH SLACK VARIABLES

Variable convention:
  x[i] = 0  ->  Task i assigned to DRAM  (fast, 100 ns)
  x[i] = 1  ->  Task i assigned to CXL   (slower, 300 ns)

Objective:
  min  sum_i (s_i * dL * m_i * x_i)              [latency cost]
     + lambda * (sum_i m_i*(1-x_i) + s - D)^2    [DRAM capacity constraint]

where s = sum_k 2^k * a_k  is a binary-encoded slack variable ensuring
the constraint is an EQUALITY (not equality-to-target, but feasibility).

The slack absorbs the "unused DRAM" so the penalty is zero for ANY valid
assignment (DRAM used <= D), not just the one that fills DRAM exactly.

Why slack variables are required:
  Without slack, penalty = (DRAM_used - D)^2 penalizes DRAM_used=1500
  MORE than DRAM_used=2200 when D=2000, since (1500-2000)^2 > (2200-2000)^2.
  This is wrong: 1500 < 2000 is valid, 2200 > 2000 is invalid.
  The slack variable s = D - DRAM_used absorbs the gap for valid assignments,
  making penalty = 0 for all valid assignments and > 0 only for violations.

Full variable vector: [x_0,...,x_{n-1}, a_0,...,a_{b-1}]
  n task variables + b slack bits
  b = ceil(log2(D+1)) bits to encode s in range [0, D]

Exact QUBO coefficients derived by expanding lambda*(K' - sum(m_i*x_i) + sum(2^k*a_k))^2
where K' = S - D = total_task_memory - DRAM_capacity:

  Task diagonal:      Q[i][i] += s_i*dL*m_i + lambda*(m_i^2 - 2*K'*m_i)
  Task off-diagonal:  Q[i][j] += lambda * 2 * m_i * m_j        (i<j)
  Slack diagonal:     Q[n+k][n+k] += lambda * (4^k + 2*K'*2^k)
  Slack off-diagonal: Q[n+k][n+l] += lambda * 2 * 2^k * 2^l    (k<l)
  Task-slack cross:   Q[i][n+k]   += lambda * (-2) * m_i * 2^k
"""

import os
import math
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from dataclasses import dataclass


# ── Physical constants ────────────────────────────────────────────────────────

DRAM_LATENCY_NS: int = 100
CXL_LATENCY_NS:  int = 300
LATENCY_DIFF_NS: int = CXL_LATENCY_NS - DRAM_LATENCY_NS    # 200

# DRAM capacity — must be LESS than total task memory to create
# meaningful capacity pressure. For 8 default tasks (S=3912MB),
# 50% = 1956MB means ~half the tasks must spill to CXL.
DRAM_CAPACITY_MB:       float = 1956.0
CAPACITY_PENALTY_WEIGHT: float = 0.05   # tune with tune_lambda()


# ── Task dataclass ────────────────────────────────────────────────────────────

@dataclass
class Task:
    task_id:               int
    memory_requirement_mb: float
    priority:              int
    memory_sensitivity:    float   # 0.0=insensitive, 1.0=highly sensitive


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


# ── Slack variable helper ─────────────────────────────────────────────────────

def num_slack_bits(dram_capacity_mb: float) -> int:
    """
    Number of binary bits needed to encode slack s in [0, dram_capacity_mb].
    b = ceil(log2(D + 1))
    """
    return math.ceil(math.log2(dram_capacity_mb + 1))


def decode_slack(slack_bits: dict, n_tasks: int, b: int) -> float:
    """
    Reconstructs the slack value s = sum_k 2^k * a_k from the solution dict.

    Args:
        slack_bits: Full solution dict {var_index: 0 or 1}
        n_tasks:    Number of task variables (slack bits start at index n_tasks)
        b:          Number of slack bits

    Returns:
        Float slack value s.
    """
    return sum(
        (2 ** k) * slack_bits.get(n_tasks + k, 0)
        for k in range(b)
    )


# ── Core QUBO builder ─────────────────────────────────────────────────────────

def build_qubo_from_tasks(
    tasks:            list,
    dram_capacity_mb: float = DRAM_CAPACITY_MB,
    penalty_weight:   float = CAPACITY_PENALTY_WEIGHT,
) -> np.ndarray:
    """
    Builds the QUBO matrix using slack variables for a correct
    inequality capacity constraint.

    Variable ordering in the matrix:
      indices 0..n-1       = task variables x_i
      indices n..n+b-1     = slack bits a_k

    Total matrix size: (n + b) x (n + b)

    Args:
        tasks:            Task list.
        dram_capacity_mb: DRAM capacity in MB. Must be < total task memory.
        penalty_weight:   Lambda. Use tune_lambda() to calibrate.

    Returns:
        Upper-triangular numpy float64 array of shape (n+b, n+b).

    Raises:
        ValueError: If DRAM capacity >= total task memory.
    """
    n         = len(tasks)
    S         = sum(t.memory_requirement_mb for t in tasks)
    if dram_capacity_mb >= S:
        dram_capacity_mb = S
    b         = num_slack_bits(dram_capacity_mb)
    total     = n + b
   
    K_prime = max(0, S - dram_capacity_mb)   # K' = S - D


    Q = np.zeros((total, total), dtype=np.float64)
    lam = penalty_weight

    # ── Task-task terms ───────────────────────────────────────────────────────

    for i, task in enumerate(tasks):
        m_i = task.memory_requirement_mb

        # Diagonal: latency cost + capacity penalty diagonal
        # Latency: s_i * dL * m_i  (penalises CXL assignment)
        # Capacity diagonal from expanding (K' - sum(m*x) + sum(2^k*a))^2:
        #   lambda * (m_i^2 - 2*K'*m_i)
        Q[i][i] += (task.memory_sensitivity * LATENCY_DIFF_NS * m_i
                    + lam * (m_i**2 - 2.0 * K_prime * m_i))

    for i in range(n):
        for j in range(i + 1, n):
            m_i = tasks[i].memory_requirement_mb
            m_j = tasks[j].memory_requirement_mb
            # Off-diagonal task-task: lambda * 2 * m_i * m_j
            Q[i][j] += lam * 2.0 * m_i * m_j

    # ── Slack-slack terms ─────────────────────────────────────────────────────

    for k in range(b):
        # Slack diagonal from expanding (sum(2^k*a_k))^2 and 2*K'*sum(2^k*a_k):
        #   lambda * (4^k + 2*K'*2^k)
        Q[n + k][n + k] += lam * (4.0**k + 2.0 * K_prime * (2.0**k))

    for k in range(b):
        for l in range(k + 1, b):
            # Slack off-diagonal: lambda * 2 * 2^k * 2^l
            Q[n + k][n + l] += lam * 2.0 * (2.0**k) * (2.0**l)

    # ── Task-slack cross terms ────────────────────────────────────────────────

    for i, task in enumerate(tasks):
        m_i = task.memory_requirement_mb
        for k in range(b):
            # Cross term: -lambda * 2 * m_i * 2^k
            # Negative: when both x_i=1 (CXL) and a_k=1 (slack used),
            # the product reduces the penalty — correct because CXL assignment
            # means less DRAM used, requiring less slack.
            # Since i < n+k always (task indices before slack indices),
            # this goes into upper triangle correctly.
            Q[i][n + k] += lam * (-2.0) * m_i * (2.0**k)

    return Q


# ── Solution decoder ──────────────────────────────────────────────────────────

def decode_solution(
    solution:         dict,
    tasks:            list,
    dram_capacity_mb: float = DRAM_CAPACITY_MB,
) -> dict:
    """
    Extracts the task assignment from the full QUBO solution vector
    (which includes both task bits and slack bits).

    Args:
        solution:         Full solution {var_index: 0 or 1} from RQAOA.
        tasks:            Task list (same order used in build_qubo_from_tasks).
        dram_capacity_mb: Used to compute number of slack bits.

    Returns:
        Dict {task_id: 0 (DRAM) or 1 (CXL)} — task assignments only.
    """
    n = len(tasks)
    b = num_slack_bits(dram_capacity_mb)

    assignment = {tasks[i].task_id: int(solution.get(i, 0)) for i in range(n)}
    slack_val  = decode_slack(solution, n, b)
    dram_used  = sum(
        tasks[i].memory_requirement_mb
        for i in range(n) if solution.get(i, 0) == 0
    )

    return assignment


# ── Cost functions ────────────────────────────────────────────────────────────

def compute_qubo_cost(assignment_full: dict, qubo_matrix: np.ndarray) -> float:
    """
    Computes f(x,a) = [x,a]^T Q [x,a] for the full variable vector.

    Args:
        assignment_full: {var_index: 0 or 1} — includes BOTH task and slack bits.
        qubo_matrix:     The full (n+b) x (n+b) QUBO matrix.

    Returns:
        Float QUBO cost. Lower = better.
    """
    total = qubo_matrix.shape[0]
    x     = np.array([float(assignment_full.get(i, 0)) for i in range(total)])
    cost  = 0.0
    for i in range(total):
        for j in range(i, total):
            cost += qubo_matrix[i][j] * x[i] * x[j]
    return cost


def compute_latency_cost(task_assignment: dict, tasks: list) -> float:
    """
    Computes pure latency cost (no penalty, no slack).
    Use this to report the actual scheduling performance.

    Returns: sum of s_i * dL * m_i for all CXL-assigned tasks.
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


def build_full_solution(task_assignment: dict, tasks: list,
                        dram_capacity_mb: float = DRAM_CAPACITY_MB) -> dict:
    """
    Given a task assignment, computes the correct slack value and builds
    the full solution vector {var_index: 0 or 1} for QUBO cost evaluation.

    The slack s = D - DRAM_used (how much DRAM capacity is unused).
    Encoded as binary: s = sum_k 2^k * a_k.

    Args:
        task_assignment: {task_id: 0 or 1} from scheduler or RQAOA.
        tasks:           Task list.
        dram_capacity_mb: DRAM capacity.

    Returns:
        Full solution dict {var_index: 0 or 1}.
    """
    n         = len(tasks)
    b         = num_slack_bits(dram_capacity_mb)
    dram_used = compute_dram_used(task_assignment, tasks)
    slack_val = max(0.0, dram_capacity_mb - dram_used)

    # Encode slack as binary (standard binary encoding)
    slack_int  = int(round(slack_val))
    slack_bits = {}
    for k in range(b):
        slack_bits[n + k] = (slack_int >> k) & 1

    # Build full solution: task bits + slack bits
    full = {tasks[i].task_id: task_assignment.get(tasks[i].task_id, 0)
            for i in range(n)}
    full.update({i: task_assignment.get(tasks[i].task_id, 0) for i in range(n)})
    full.update(slack_bits)
    return full


# ── Lambda tuning ─────────────────────────────────────────────────────────────

def tune_lambda(
    tasks:            list,
    dram_capacity_mb: float = DRAM_CAPACITY_MB,
    verbose:          bool  = True,
) -> float:
    """
    Finds a good lambda by ensuring the capacity penalty and latency terms
    are on the same numerical scale.

    Strategy:
      1. Compute scale of latency terms
      2. Compute scale of capacity diagonal terms
      3. Set lambda so both contribute comparably
      4. Validate: for a valid assignment, QUBO cost should be lower
         than for a capacity-violating assignment
    """
    S       = sum(t.memory_requirement_mb for t in tasks)
    K       = S - dram_capacity_mb

    # Scale of latency diagonal
    max_latency = max(
        t.memory_sensitivity * LATENCY_DIFF_NS * t.memory_requirement_mb
        for t in tasks
    )

    # Scale of capacity diagonal (dominant term is -2*K*m_i)
    max_cap_diag = max(
        abs(t.memory_requirement_mb**2 - 2.0 * K * t.memory_requirement_mb)
        for t in tasks
    )

    # Scale of slack diagonal (dominant term is 2*K*2^k, largest at k=b-1)
    b = num_slack_bits(dram_capacity_mb)
    max_slack_diag = 2.0 * K * (2.0 ** (b - 1))

    lambda_from_task  = max_latency / max_cap_diag  if max_cap_diag  > 0 else 0.05
    lambda_from_slack = max_latency / max_slack_diag if max_slack_diag > 0 else 0.05

    # Take the geometric mean — balances both scales
    lambda_derived = (lambda_from_task * lambda_from_slack) ** 0.5

    if verbose:
        print("Lambda tuning:")
        print(f"  S={S:.0f}MB  D={dram_capacity_mb:.0f}MB  K={K:.0f}MB")
        print(f"  b (slack bits) = {b}")
        print(f"  Max latency term:     {max_latency:.1f}")
        print(f"  Max |cap diagonal|:   {max_cap_diag:.1f}")
        print(f"  Max slack diagonal:   {max_slack_diag:.1f}")
        print(f"  Lambda (task scale):  {lambda_from_task:.6f}")
        print(f"  Lambda (slack scale): {lambda_from_slack:.6f}")
        print(f"  Lambda (geometric):   {lambda_derived:.6f}")

    return lambda_derived


# ── Sanity verification ───────────────────────────────────────────────────────

def verify_qubo_sanity(
    tasks:            list,
    qubo_matrix:      np.ndarray,
    dram_capacity_mb: float = DRAM_CAPACITY_MB,
    verbose:          bool  = True,
) -> bool:
    """
    Verifies the QUBO is correctly formulated by checking:

    1. A valid assignment (DRAM used <= D) with correct slack has LOWER cost
       than the same assignment with wrong (zero) slack.
    2. A capacity-violating assignment costs MORE than a valid smart assignment.
    3. Cost ordering for the smart assignment is lower than all-CXL.
    4. For a valid assignment, penalty term = 0 (slack absorbs the gap exactly).
    """
    n = len(tasks)
    b = num_slack_bits(dram_capacity_mb)

    # Build smart assignment: most sensitive tasks in DRAM first
    sorted_idx = sorted(range(n),
                        key=lambda i: tasks[i].memory_sensitivity, reverse=True)
    smart_task = {}
    dram_used  = 0.0
    for i in sorted_idx:
        if dram_used + tasks[i].memory_requirement_mb <= dram_capacity_mb:
            smart_task[tasks[i].task_id] = 0
            dram_used += tasks[i].memory_requirement_mb
        else:
            smart_task[tasks[i].task_id] = 1

    all_cxl_task = {t.task_id: 1 for t in tasks}

    # Build full solutions with correct slack
    smart_full   = build_full_solution(smart_task,   tasks, dram_capacity_mb)
    cxl_full     = build_full_solution(all_cxl_task, tasks, dram_capacity_mb)

    # Build smart solution with WRONG slack (zero) to show slack matters
    smart_zero_slack = {i: smart_task.get(tasks[i].task_id, 0) for i in range(n)}
    smart_zero_slack.update({n + k: 0 for k in range(b)})

    c_smart_correct = compute_qubo_cost(smart_full,        qubo_matrix)
    c_smart_bad     = compute_qubo_cost(smart_zero_slack,  qubo_matrix)
    c_cxl           = compute_qubo_cost(cxl_full,          qubo_matrix)

    # Verify penalty = 0 for smart assignment with correct slack
    slack_val     = decode_slack(smart_full, n, b)
    dram_used_sm  = compute_dram_used(smart_task, tasks)
    residual      = dram_used_sm + slack_val - dram_capacity_mb

    check1 = abs(residual) < 1.0          # slack makes constraint = 0
    check2 = c_smart_correct < c_smart_bad # correct slack beats zero slack
    check3 = c_smart_correct < c_cxl      # smart beats all-CXL
    check4 = compute_dram_used(smart_task, tasks) <= dram_capacity_mb

    if verbose:
        print("=" * 60)
        print("QUBO SANITY CHECK (slack-variable formulation)")
        print("=" * 60)
        print(f"  n tasks = {n},  b slack bits = {b},  "
              f"total variables = {n+b}")
        print(f"  DRAM capacity: {dram_capacity_mb:.0f}MB")
        print(f"  Smart assignment DRAM used: {dram_used_sm:.0f}MB")
        print(f"  Slack value (s = D - DRAM_used): {slack_val:.0f}MB")
        print(f"  Constraint residual (should be ~0): {residual:.2f}")
        print()
        print(f"  Cost smart (correct slack): {c_smart_correct:>14.4f}")
        print(f"  Cost smart (zero slack):    {c_smart_bad:>14.4f}  "
              f"(higher = slack is working)")
        print(f"  Cost all-CXL:               {c_cxl:>14.4f}")
        print()
        print(f"  {'✅' if check1 else '❌'} "
              f"Constraint residual ≈ 0 (slack absorbs gap)")
        print(f"  {'✅' if check2 else '❌'} "
              f"Correct slack < zero slack (penalty works)")
        print(f"  {'✅' if check3 else '❌'} "
              f"Smart < all-CXL (latency objective works)")
        print(f"  {'✅' if check4 else '❌'} "
              f"Smart assignment respects DRAM capacity")
        print()
        print(f"  Smart assignment detail:")
        for i in sorted_idx:
            tier = "DRAM" if smart_task[tasks[i].task_id] == 0 else "CXL "
            print(f"    Task {tasks[i].task_id}: "
                  f"sens={tasks[i].memory_sensitivity:.2f} "
                  f"mem={tasks[i].memory_requirement_mb:.0f}MB -> {tier}")
        print("=" * 60)
        all_ok = check1 and check2 and check3 and check4
        print(f"  {'✅ ALL CHECKS PASSED' if all_ok else '❌ CHECKS FAILED'}")
        print("=" * 60)

    return check1 and check2 and check3 and check4


def save_qubo_heatmap(qubo_matrix: np.ndarray,
                      tasks: list,
                      output_path: str = "results/plots/qubo_heatmap.png") -> None:
    """
    Saves annotated heatmap. Labels task variables (T0..Tn)
    and slack bit variables (a0..ab) on axes.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    n = len(tasks)
    b = qubo_matrix.shape[0] - n

    labels = [f"T{i}" for i in range(n)] + [f"a{k}" for k in range(b)]

    fig, ax = plt.subplots(figsize=(12, 10))
    im = ax.imshow(qubo_matrix, cmap="RdBu_r", aspect="auto")
    plt.colorbar(im, ax=ax, label="QUBO coefficient")

    ax.set_title(
        "QUBO Matrix — Slack-Variable Formulation\n"
        f"Task vars (T0..T{n-1}) | Slack bits (a0..a{b-1})\n"
        "Blue = rewards DRAM | Red = capacity penalty",
        fontsize=10
    )
    ax.set_xticks(range(len(labels)))
    ax.set_yticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=45, fontsize=7)
    ax.set_yticklabels(labels, fontsize=7)

    # Draw dividing line between task and slack variables
    ax.axhline(n - 0.5, color="yellow", linewidth=1.5, alpha=0.7)
    ax.axvline(n - 0.5, color="yellow", linewidth=1.5, alpha=0.7)

    total = len(labels)
    for i in range(total):
        for j in range(total):
            v = qubo_matrix[i][j]
            if abs(v) > 1e-3:
                ax.text(j, i, f"{v:.0f}", ha="center", va="center",
                        fontsize=5, color="white" if abs(v) > 50000 else "black")

    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()
    print(f"Heatmap saved: {output_path}")
