
"""
statistical_robustness.py

Runs RQAOA 5 times on the 8-task problem and computes mean ± std dev of:
  - QUBO cost
  - Solution quality %
  - DRAM task count

Purpose: Demonstrates that RQAOA produces consistent results (low variance),
which is important evidence that the quantum approach is reliable and not
just getting lucky on a single run.

This is a key internship-quality addition — showing statistical confidence
in your results is what separates a research project from a demo.
"""

import csv, os, sys, time, logging
import numpy as np

src_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if src_path not in sys.path:
    sys.path.insert(0, src_path)

PROJECT_ROOT = os.path.dirname(src_path)
logging.basicConfig(level=logging.WARNING)

from rqaoa.qubo_builder import build_qubo_from_tasks, compute_qubo_cost, DEFAULT_TASKS,DRAM_CAPACITY_MB
from rqaoa.qubo_converter import convert_numpy_qubo_to_openqaoa_dict
from rqaoa.rqaoa_runner import run_rqaoa_optimizer
from rqaoa.scaling_experiment import compute_optimal_cost, solution_quality_score,enforce_capacity
from rqaoa.qubo_builder import tune_lambda, qubo_constant


def run_statistical_robustness(n_runs: int = 5) -> dict:
    """
    Runs RQAOA n_runs times on the 8-task problem.

    Args:
        n_runs: Number of independent RQAOA runs (default 5).
                Each run is independent with random QAOA parameter init.

    Returns:
        Dict with per-run results and aggregate statistics.
    """
    print(f"Running RQAOA {n_runs} times on 8-task problem...")
    print("Each run takes ~3-5 min. Total: ~15-25 min.\n")

    dram_cap     = DRAM_CAPACITY_MB
    best_lambda  = tune_lambda(DEFAULT_TASKS, dram_cap, verbose=False)
    qubo_matrix  = build_qubo_from_tasks(DEFAULT_TASKS, 
                   dram_capacity_mb=dram_cap, penalty_weight=best_lambda)
    q_const      = qubo_constant(DEFAULT_TASKS, dram_cap, best_lambda)  # ← must add this back
    n_tasks      = len(DEFAULT_TASKS)

    optimal_cost = compute_optimal_cost(DEFAULT_TASKS, qubo_matrix, dram_cap, q_const)
    worst_cost   = compute_qubo_cost({i: 1 for i in range(n_tasks)}, qubo_matrix) + q_const
    
    qubo_dict    = convert_numpy_qubo_to_openqaoa_dict(qubo_matrix)

    print(f"Optimal cost (brute-force): {optimal_cost:.4f}")
    print(f"Worst cost (all CXL):       {worst_cost:.4f}\n")

    per_run = []
    for run_idx in range(n_runs):
        print(f"Run {run_idx+1}/{n_runs}...")
        t0         = time.perf_counter()
        elapsed    = time.perf_counter() - t0
        raw_assignment = run_rqaoa_optimizer(qubo_dict, num_variables=8)
        task_a = {DEFAULT_TASKS[i].task_id: int(raw_assignment.get(i, 0)) for i in range(n_tasks)}
        task_a = enforce_capacity(task_a, DEFAULT_TASKS, DRAM_CAPACITY_MB)

        # remap back to var-index keys for cost computation
        assignment = {i: task_a[DEFAULT_TASKS[i].task_id] for i in range(n_tasks)}

        cost    = compute_qubo_cost(assignment, qubo_matrix)+q_const
        quality = solution_quality_score(cost, optimal_cost, worst_cost)
        dram    = sum(1 for v in assignment.values() if v == 0)

        cxl     = sum(1 for v in assignment.values() if v == 1)  # ← add this
        per_run.append({
            "run":        run_idx + 1,
            "qubo_cost":  round(cost, 4),
            "quality_pct": round(quality, 2),
            "dram_tasks": dram,
            "cxl_tasks":  cxl,
            "elapsed_s":  round(elapsed, 2),
        })
        print(f"  Cost: {cost:.4f} | Quality: {quality:.1f}% | "
              f"DRAM: {dram} | CXL: {cxl} | Time: {elapsed:.1f}s")

    # Compute statistics
    costs    = [r["qubo_cost"]  for r in per_run]
    qualities= [r["quality_pct"] for r in per_run]
    drams    = [r["dram_tasks"] for r in per_run]

    stats = {
        "n_runs":           n_runs,
        "optimal_cost":     round(optimal_cost, 4),
        "worst_cost":       round(worst_cost, 4),
        "cost_mean":        round(float(np.mean(costs)), 4),
        "cost_std":         round(float(np.std(costs)), 4),
        "cost_min":         round(min(costs), 4),
        "cost_max":         round(max(costs), 4),
        "quality_mean_pct": round(float(np.mean(qualities)), 2),
        "quality_std_pct":  round(float(np.std(qualities)), 2),
        "dram_mean":        round(float(np.mean(drams)), 2),
        "dram_std":         round(float(np.std(drams)), 2),
        "per_run":          per_run,
    }

    print(f"\n{'='*50}")
    print(f"RQAOA Statistical Robustness ({n_runs} runs, 8 tasks)")
    print(f"{'='*50}")
    print(f"  Cost:    {stats['cost_mean']:.4f} ± {stats['cost_std']:.4f}  "
          f"(min={stats['cost_min']:.4f}, max={stats['cost_max']:.4f})")
    print(f"  Quality: {stats['quality_mean_pct']:.1f}% ± {stats['quality_std_pct']:.1f}%")
    print(f"  DRAM:    {stats['dram_mean']:.1f} ± {stats['dram_std']:.1f} tasks")
    print(f"  Optimal: {optimal_cost:.4f}")

    results_dir = os.path.join(PROJECT_ROOT, "results")
    os.makedirs(results_dir, exist_ok=True)

    # Save per-run CSV
    csv_path = os.path.join(results_dir, "rqaoa_robustness.csv")
    with open(csv_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=per_run[0].keys())
        w.writeheader()
        w.writerows(per_run)

    # Save stats summary
    import json
    json_path = os.path.join(results_dir, "rqaoa_robustness_stats.json")
    with open(json_path, "w") as f:
        json.dump({k: v for k, v in stats.items() if k != "per_run"}, f, indent=2)

    print(f"\nSaved: {csv_path}")
    print(f"Saved: {json_path}")
    return stats
