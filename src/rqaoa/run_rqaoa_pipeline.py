
"""
#changed
run_rqaoa_pipeline.py — QUBO -> RQAOA -> decode -> validate -> save

No slack variables. QUBO size = N x N where N = number of tasks.
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
    tune_lambda,
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

    Args:
        tasks:            Task list. Defaults to DEFAULT_TASKS.
        dram_capacity_mb: DRAM capacity in MB.
        label:            Tag for output CSV filename.

    Returns:
        Dict {task_id: "DRAM" or "CXL"}
    """
    if tasks is None:
        tasks = DEFAULT_TASKS

    n_tasks = len(tasks)
    logger.info(f"=== Pipeline: {n_tasks} tasks | {n_tasks} QUBO variables ===")

    # Step 1: Tune lambda and build QUBO
    best_lambda = tune_lambda(tasks, dram_capacity_mb, verbose=False)
    logger.info(f"Lambda (tuned): {best_lambda:.6f}")

    qubo_matrix = build_qubo_from_tasks(
        tasks,
        dram_capacity_mb=dram_capacity_mb,
        penalty_weight=best_lambda,
    )
    assert qubo_matrix.shape == (n_tasks, n_tasks)
    logger.info(f"QUBO shape: {qubo_matrix.shape}")

    # Step 2: Convert to OpenQAOA format
    qubo_dict = convert_numpy_qubo_to_openqaoa_dict(qubo_matrix)
    logger.info(f"Non-zero entries: {len(qubo_dict)}")

    # Step 3: Run RQAOA on n_tasks qubits
    logger.info(f"Running RQAOA ({n_tasks} qubits)...")
    raw_solution = run_rqaoa_optimizer(
    qubo_dict,
    num_variables=n_tasks,
    dram_capacity_mb=dram_capacity_mb,
)

    # raw_solution keys are variable indices (0..n_tasks-1)
    # map to task_ids
    task_assignment = {tasks[i].task_id: int(raw_solution.get(i, 0))
                       for i in range(n_tasks)}

    # Step 4: Validate
    if not validate_assignment(task_assignment, n_tasks):
        raise RuntimeError("Assignment failed validation.")

    dram_used = compute_dram_used(task_assignment, tasks)
    if dram_used > dram_capacity_mb + 1.0:
        logger.warning(
            f"DRAM slightly over capacity: {dram_used:.0f}MB > "
            f"{dram_capacity_mb:.0f}MB. "
            f"Increase lambda or DRAM capacity."
        )

    # Step 5: Decode to human-readable map
    memory_map   = decode_assignment_to_memory_map(task_assignment)
    latency_cost = compute_latency_cost(task_assignment, tasks)

    logger.info("=== Assignment Result ===")
    for i in sorted(range(n_tasks),
                    key=lambda i: tasks[i].memory_sensitivity, reverse=True):
        tid  = tasks[i].task_id
        tier = memory_map[tid]
        logger.info(f"  Task {tid}: sens={tasks[i].memory_sensitivity:.2f} "
                    f"mem={tasks[i].memory_requirement_mb:.0f}MB -> {tier}")
    logger.info(f"  DRAM used: {dram_used:.0f} / {dram_capacity_mb:.0f} MB")
    logger.info(f"  Latency cost: {latency_cost:.1f} ns·MB")

    # Step 6: Save CSV
    results_dir = os.path.join(PROJECT_ROOT, "results")
    os.makedirs(results_dir, exist_ok=True)
    out = os.path.join(results_dir, f"rqaoa_assignment_{label}.csv")

    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["task_id", "memory_tier", "memory_sensitivity",
                    "memory_mb", "latency_contribution_ns_mb"])
        for tid, tier in sorted(memory_map.items()):
            t = tasks[tid]
            contrib = (t.memory_sensitivity * 200 * t.memory_requirement_mb
                       if tier == "CXL" else 0.0)
            w.writerow([tid, tier, t.memory_sensitivity,
                        t.memory_requirement_mb, round(contrib, 2)])
        w.writerow([])
        w.writerow(["# DRAM used MB", dram_used, "", "", ""])
        w.writerow(["# DRAM cap MB",  dram_capacity_mb, "", "", ""])
        w.writerow(["# Latency cost", latency_cost, "", "", ""])
        w.writerow(["# Feasible",
                    "YES" if dram_used <= dram_capacity_mb else "NO",
                    "", "", ""])

    logger.info(f"Saved: {out}")
    return memory_map


if __name__ == "__main__":
    result = run_full_rqaoa_pipeline()
    print("\nDone ✅")
    for tid, tier in sorted(result.items()):
        print(f"  Task {tid} -> {tier}")
