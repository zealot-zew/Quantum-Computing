
"""
changed
scaling_experiment.py — RQAOA + classical schedulers at 8/12/16 tasks.
No slack variables. QUBO size = N x N.
"""

import csv, os, sys, time, logging, itertools
import numpy as np

src_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if src_path not in sys.path:
    sys.path.insert(0, src_path)

PROJECT_ROOT = os.path.dirname(src_path)
logging.basicConfig(level=logging.WARNING)

from rqaoa.qubo_builder import (
    build_qubo_from_tasks, compute_qubo_cost,
    compute_dram_used, compute_latency_cost,
    tune_lambda, qubo_constant,
    DEFAULT_TASKS, TASKS_12, TASKS_16,
)
from rqaoa.qubo_converter import convert_numpy_qubo_to_openqaoa_dict
from rqaoa.rqaoa_runner import run_rqaoa_optimizer


def _dram_cap(tasks): return sum(t.memory_requirement_mb for t in tasks) * 0.5

def _fcfs(tasks, dram_cap):
    a, used = {}, 0.0
    for t in tasks:
        if used + t.memory_requirement_mb <= dram_cap:
            a[t.task_id] = 0; used += t.memory_requirement_mb
        else:
            a[t.task_id] = 1
    return a

def _round_robin(tasks, dram_cap):
    a, used, flip = {}, 0.0, True
    for t in tasks:
        if flip and used + t.memory_requirement_mb <= dram_cap:
            a[t.task_id] = 0; used += t.memory_requirement_mb
        else:
            a[t.task_id] = 1
        flip = not flip
    return a

def _greedy(tasks, dram_cap):
    a, used = {}, 0.0
    for t in sorted(tasks, key=lambda x: x.memory_sensitivity, reverse=True):
        if used + t.memory_requirement_mb <= dram_cap:
            a[t.task_id] = 0; used += t.memory_requirement_mb
        else:
            a[t.task_id] = 1
    return a

def _priority_greedy(tasks, dram_cap):
    a, used = {}, 0.0
    for t in sorted(tasks,
                    key=lambda x: x.priority * x.memory_sensitivity,
                    reverse=True):
        if used + t.memory_requirement_mb <= dram_cap:
            a[t.task_id] = 0; used += t.memory_requirement_mb
        else:
            a[t.task_id] = 1
    return a


def compute_optimal_cost(tasks, qubo_matrix, dram_capacity_mb, q_const: float = 0.0) -> float:
    """Brute-force optimal over feasible assignments. Feasible for n<=20."""
    n, best = len(tasks), float("inf")
    for bits in itertools.product([0, 1], repeat=n):
        assignment = {tasks[i].task_id: bits[i] for i in range(n)}
        if compute_dram_used(assignment, tasks) > dram_capacity_mb:
            continue
        vi_assignment = {i: bits[i] for i in range(n)}
        cost = compute_qubo_cost(vi_assignment, qubo_matrix)
        if cost < best:
            best = cost
    return best + q_const

def enforce_capacity(task_assignment, tasks, dram_cap):
    assignment = dict(task_assignment)
    dram_used  = compute_dram_used(assignment, tasks)

    if dram_used <= dram_cap:
        return assignment

    if dram_used > dram_cap * 1.20:
        # Heavy violation: rebuild from scratch but RESPECT RQAOA's CXL choices first.
        # Tasks RQAOA wanted in CXL stay there. Fill remaining DRAM with
        # sensitivity-sorted tasks that RQAOA put in DRAM.
        rqaoa_cxl  = [t for t in tasks if assignment[t.task_id] == 1]
        rqaoa_dram = sorted(
            [t for t in tasks if assignment[t.task_id] == 0],
            key=lambda t: t.memory_sensitivity, reverse=True  # most sensitive first
        )
        result, used = {t.task_id: 1 for t in rqaoa_cxl}, 0.0
        for t in rqaoa_dram:
            if used + t.memory_requirement_mb <= dram_cap:
                result[t.task_id] = 0; used += t.memory_requirement_mb
            else:
                result[t.task_id] = 1
        return result

    # Small violation: evict large low-sensitivity tasks first
    dram_tasks = sorted(
        [t for t in tasks if assignment[t.task_id] == 0],
        key=lambda t: (t.memory_sensitivity, -t.memory_requirement_mb)
    )
    for task in dram_tasks:
        if dram_used <= dram_cap:
            break
        assignment[task.task_id] = 1
        dram_used -= task.memory_requirement_mb

    return assignment
def solution_quality_score(actual, optimal, worst) -> float:
    if abs(worst - optimal) < 1e-9:
        return 100.0
    return max(0.0, 100.0 * (worst - actual) / (worst - optimal))


def run_scaling_experiment(run_rqaoa: bool = True) -> list:
    task_sets = [(8, DEFAULT_TASKS), (12, TASKS_12), (16, TASKS_16)]
    classical = {"FCFS": _fcfs, "RoundRobin": _round_robin,
                 "Greedy": _greedy, "PriorityGreedy": _priority_greedy}
    all_results = []

    for n_tasks, tasks in task_sets:
        dram_cap  = _dram_cap(tasks)
        total_mem = sum(t.memory_requirement_mb for t in tasks)

        print(f"\n{'─'*55}")
        print(f"Tasks: {n_tasks} | Mem: {total_mem:.0f}MB | "
              f"DRAM cap: {dram_cap:.0f}MB | QUBO: {n_tasks}x{n_tasks}")

        best_lambda = tune_lambda(tasks, dram_cap, verbose=False)
        print(f"  Lambda: {best_lambda:.6f}")

        qubo_matrix = build_qubo_from_tasks(
            tasks, dram_capacity_mb=dram_cap, penalty_weight=best_lambda
        )
        # Constant dropped from matrix (lambda*K^2). Add back so all reported
        # costs are positive absolute values on the same scale across task sets.
        q_const = qubo_constant(tasks, dram_cap, best_lambda)

        print(f"  Computing brute-force optimal...")
        t0           = time.perf_counter()
        optimal_cost = compute_optimal_cost(tasks, qubo_matrix, dram_cap,q_const)
        print(f"  Optimal: {optimal_cost:.4f}  ({time.perf_counter()-t0:.1f}s)")

        # Worst = all CXL (max latency, variable indices = task indices)
        worst_cost = compute_qubo_cost({i: 1 for i in range(n_tasks)}, qubo_matrix) + q_const

        # Classical schedulers
        for sname, fn in classical.items():
            t0         = time.perf_counter()
            task_a     = fn(tasks, dram_cap)
            elapsed_ms = (time.perf_counter() - t0) * 1000

            # Remap task_id -> var_index for cost computation
            vi_a      = {tasks[i].task_id: task_a[tasks[i].task_id]
                         for i in range(n_tasks)}
            vi_a_idx  = {i: task_a[tasks[i].task_id] for i in range(n_tasks)}
            cost      = compute_qubo_cost(vi_a_idx, qubo_matrix) + q_const
            quality   = solution_quality_score(cost, optimal_cost, worst_cost)
            latency   = compute_latency_cost(task_a, tasks)
            dram_used = compute_dram_used(task_a, tasks)
            dram_cnt  = sum(1 for v in task_a.values() if v == 0)
            cxl_cnt   = sum(1 for v in task_a.values() if v == 1)

            print(f"  {sname:<18} cost={cost:.2f} | q={quality:.1f}% | "
                  f"DRAM={dram_cnt} ({dram_used:.0f}MB) | CXL={cxl_cnt}")

            all_results.append({
                "task_count": n_tasks, "scheduler": sname,
                "qubo_cost": round(cost, 4), "latency_cost": round(latency, 2),
                "optimal_cost": round(optimal_cost, 4),
                "quality_pct": round(quality, 2),
                "dram_tasks": dram_cnt, "cxl_tasks": cxl_cnt,
                "dram_mb": round(dram_used, 1), "dram_cap_mb": round(dram_cap, 1),
                "elapsed_ms": round(elapsed_ms, 4), "is_quantum": False,
                "lambda": round(best_lambda, 6),
            })

        # RQAOA
        if run_rqaoa:
            print(f"\n  Running RQAOA ({n_tasks} qubits)...")
            try:
                qubo_dict = convert_numpy_qubo_to_openqaoa_dict(qubo_matrix)
                t0        = time.perf_counter()
                raw = run_rqaoa_optimizer(qubo_dict, num_variables=n_tasks, dram_capacity_mb=dram_cap)
                elapsed_s = time.perf_counter() - t0

                # build once, repair once
                task_a = {tasks[i].task_id: int(raw.get(i, 0)) for i in range(n_tasks)}
                print("\nRAW RQAOA OUTPUT"); print(raw)

                task_a = enforce_capacity(task_a, tasks, dram_cap)   # repaired in-place
                print("TASK ASSIGNMENT (repaired)"); print(task_a)
                print("DRAM USED"); print(compute_dram_used(task_a, tasks))

                # cost/quality from the REPAIRED assignment
                vi_idx    = {i: task_a[tasks[i].task_id] for i in range(n_tasks)}  # ← from task_a, not raw
                cost      = compute_qubo_cost(vi_idx, qubo_matrix) + q_const
                quality   = solution_quality_score(cost, optimal_cost, worst_cost)
                latency   = compute_latency_cost(task_a, tasks)
                dram_used = compute_dram_used(task_a, tasks)
                dram_cnt  = sum(1 for v in task_a.values() if v == 0)
                cxl_cnt   = sum(1 for v in task_a.values() if v == 1)

                if dram_used > dram_cap + 1.0:
                    print(f"  ⚠️  DRAM over capacity: {dram_used:.0f}MB > "
                          f"{dram_cap:.0f}MB")

                print(f"  {'RQAOA':<18} cost={cost:.2f} | q={quality:.1f}% | "
                      f"DRAM={dram_cnt} ({dram_used:.0f}MB) | CXL={cxl_cnt} | "
                      f"time={elapsed_s:.1f}s")

                all_results.append({
                    "task_count": n_tasks, "scheduler": "RQAOA",
                    "qubo_cost": round(cost, 4), "latency_cost": round(latency, 2),
                    "optimal_cost": round(optimal_cost, 4),
                    "quality_pct": round(quality, 2),
                    "dram_tasks": dram_cnt, "cxl_tasks": cxl_cnt,
                    "dram_mb": round(dram_used, 1), "dram_cap_mb": round(dram_cap, 1),
                    "elapsed_ms": round(elapsed_s * 1000, 1), "is_quantum": True,
                    "lambda": round(best_lambda, 6),
                })
            except Exception as e:
                print(f"  ❌ RQAOA failed: {e}")

    return all_results


def save_scaling_csv(results: list, path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fields = ["task_count", "scheduler", "qubo_cost", "latency_cost",
              "optimal_cost", "quality_pct", "dram_tasks", "cxl_tasks",
              "dram_mb", "dram_cap_mb", "elapsed_ms", "is_quantum", "lambda"]
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader(); w.writerows(results)
    print(f"Saved: {path}")
