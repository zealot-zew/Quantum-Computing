
"""
run_rqaoa_pipeline.py — QUBO -> RQAOA -> decode -> validate -> save

Updated for slack-variable formulation:
  - Total QUBO variables = n_tasks + n_slack_bits (e.g. 8 + 11 = 19)
  - RQAOA is run on all 19 variables
  - Only task bits (first n_tasks indices) are extracted as the assignment
  - Slack bits are decoded separately for validation
  - Validation checks DRAM capacity is not exceeded
"""

import logging, os, csv, sys

src_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if src_path not in sys.path:
    sys.path.insert(0, src_path)

PROJECT_ROOT = os.path.dirname(src_path)

from rqaoa.qubo_builder import (
    build_qubo_from_tasks,
    compute_latency_cost,
    compute_dram_used,
    decode_solution,
    num_slack_bits,
    DEFAULT_TASKS,
    DRAM_CAPACITY_MB,
)
from rqaoa.qubo_converter import convert_numpy_qubo_to_openqaoa_dict
from rqaoa.rqaoa_runner import run_rqaoa_optimizer
from rqaoa.result_parser import decode_assignment_to_memory_map, validate_assignment

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def run_full_rqaoa_pipeline(
    tasks:            list  = None,
    dram_capacity_mb: float = DRAM_CAPACITY_MB,
    label:            str   = "8tasks",
) -> dict:
    """
    Runs the complete QUBO -> RQAOA -> decode -> validate -> save pipeline.

    The QUBO has n_tasks + n_slack_bits variables total. RQAOA optimises
    over all of them. Only the first n_tasks bits form the scheduling
    decision; the remaining bits are slack and are decoded separately
    to verify the capacity constraint is satisfied.

    Args:
        tasks:            Task list. Defaults to DEFAULT_TASKS (8 tasks).
        dram_capacity_mb: DRAM capacity in MB. Must match what was used
                          in build_qubo_from_tasks().
        label:            Tag for the output CSV filename.

    Returns:
        Dict {task_id: "DRAM" or "CXL"}

    Raises:
        RuntimeError: If RQAOA returns wrong number of variables or
                      the decoded assignment violates DRAM capacity.
    """
    if tasks is None:
        tasks = DEFAULT_TASKS

    n_tasks     = len(tasks)
    n_slack     = num_slack_bits(dram_capacity_mb)
    n_total     = n_tasks + n_slack

    logger.info(f"=== Pipeline: {n_tasks} tasks | {n_slack} slack bits | "
                f"{n_total} total QUBO variables ===")

    # ── Step 1: Build QUBO ────────────────────────────────────────────────────
    logger.info("Step 1: Building QUBO matrix...")
    qubo_matrix = build_qubo_from_tasks(tasks, dram_capacity_mb=dram_capacity_mb)

    assert qubo_matrix.shape == (n_total, n_total), (
        f"QUBO shape mismatch: expected ({n_total},{n_total}), "
        f"got {qubo_matrix.shape}"
    )
    logger.info(f"  QUBO shape: {qubo_matrix.shape}")

    # ── Step 2: Convert to OpenQAOA format ───────────────────────────────────
    logger.info("Step 2: Converting to OpenQAOA dict format...")
    qubo_dict = convert_numpy_qubo_to_openqaoa_dict(qubo_matrix)
    logger.info(f"  Non-zero entries: {len(qubo_dict)}")

    # ── Step 3: Run RQAOA on the full n_total variables ──────────────────────
    logger.info(f"Step 3: Running RQAOA ({n_total} variables)...")
    raw_solution = run_rqaoa_optimizer(qubo_dict, num_variables=n_total)
    print("\nRAW RQAOA SOLUTION")
    print(raw_solution)

    # Verify RQAOA returned all expected variables
    if len(raw_solution) != n_total:
        raise RuntimeError(
            f"RQAOA returned {len(raw_solution)} variables, "
            f"expected {n_total}. "
            f"Check that num_variables={n_total} was passed correctly."
        )

    # ── Step 4: Extract task assignment from full solution ────────────────────
    logger.info("Step 4: Decoding task assignment from full solution...")

    # Task bits: indices 0 .. n_tasks-1
    task_assignment_int = {
        tasks[i].task_id: int(raw_solution.get(i, 0))
        for i in range(n_tasks)
    }
   

    # Slack bits: indices n_tasks .. n_total-1
    slack_val = sum(
        (2 ** k) * int(raw_solution.get(n_tasks + k, 0))
        for k in range(n_slack)
    )

    dram_used = compute_dram_used(task_assignment_int, tasks)

    logger.info(f"  Slack value decoded: s = {slack_val:.0f} MB")
    logger.info(f"  DRAM used: {dram_used:.0f} MB / {dram_capacity_mb:.0f} MB capacity")

    # ── Step 5: Validate ──────────────────────────────────────────────────────
    logger.info("Step 5: Validating assignment...")

    # Check all task variables are present and binary
    if not validate_assignment(task_assignment_int, n_tasks):
        raise RuntimeError("Task assignment failed binary validation.")

    # Check DRAM capacity is not exceeded
    if dram_used > dram_capacity_mb + 0.5:   # 0.5 MB tolerance for rounding
        raise RuntimeError(
            f"DRAM capacity violated: {dram_used:.0f}MB used > "
            f"{dram_capacity_mb:.0f}MB capacity. "
            f"Increase penalty_weight in build_qubo_from_tasks()."
        )

    # Check constraint residual (DRAM_used + slack should equal D)
    residual = abs(dram_used + slack_val - dram_capacity_mb)
    if residual > 10.0:   # 10 MB tolerance
        logger.warning(
            f"Constraint residual = {residual:.1f}MB "
            f"(DRAM_used={dram_used:.0f} + slack={slack_val:.0f} "
            f"!= D={dram_capacity_mb:.0f}). "
            f"RQAOA may not have found the exact feasible solution. "
            f"Result is still usable but suboptimal."
        )

    logger.info("  Validation passed ✅")

    # ── Step 6: Decode to human-readable tier map ─────────────────────────────
    print("TASK ASSIGNMENT INT")
    print(task_assignment_int)
    memory_map = decode_assignment_to_memory_map(task_assignment_int)

    # Compute actual latency cost (pure scheduling metric, no penalty)
    latency_cost = compute_latency_cost(task_assignment_int, tasks)

    logger.info("=== Assignment Result ===")
    for i in sorted(range(n_tasks), key=lambda i: tasks[i].memory_sensitivity,
                    reverse=True):
        tid  = tasks[i].task_id
        tier = memory_map[tid]
        logger.info(
            f"  Task {tid}: sens={tasks[i].memory_sensitivity:.2f} "
            f"mem={tasks[i].memory_requirement_mb:.0f}MB -> {tier}"
        )

    logger.info(f"  DRAM used: {dram_used:.0f} / {dram_capacity_mb:.0f} MB")
    logger.info(f"  Latency cost (CXL penalty): {latency_cost:.1f} ns·MB")

    # ── Step 7: Save to CSV ───────────────────────────────────────────────────
    results_dir = os.path.join(PROJECT_ROOT, "results")
    os.makedirs(results_dir, exist_ok=True)
    out = os.path.join(results_dir, f"rqaoa_assignment_{label}.csv")

    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "task_id", "memory_tier", "memory_sensitivity",
            "memory_mb", "latency_contribution_ns_mb"
        ])
        for tid, tier in sorted(memory_map.items()):
            t = tasks[tid]
            latency_contrib = (
                t.memory_sensitivity * 200 * t.memory_requirement_mb
                if tier == "CXL" else 0.0
            )
            w.writerow([
                tid, tier, t.memory_sensitivity,
                t.memory_requirement_mb, round(latency_contrib, 2)
            ])

        # Append summary row
        w.writerow([])
        w.writerow(["# Summary", "", "", "", ""])
        w.writerow(["# DRAM used MB",  dram_used,        "", "", ""])
        w.writerow(["# DRAM cap MB",   dram_capacity_mb, "", "", ""])
        w.writerow(["# Slack MB",      slack_val,        "", "", ""])
        w.writerow(["# Latency cost",  latency_cost,     "", "", ""])
        w.writerow(["# Constraint OK",
                    "YES" if dram_used <= dram_capacity_mb else "NO", "", "", ""])

    logger.info(f"Saved: {out}")
    return memory_map


if __name__ == "__main__":
    result = run_full_rqaoa_pipeline()
    print("\nDone ✅")
    for tid, tier in sorted(result.items()):
        print(f"  Task {tid} -> {tier}")
