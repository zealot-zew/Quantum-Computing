
"""
ibm_quantum_prep.py — 4-task QUBO prep + Aer reference for IBM hardware Day 5.
Default backend ibm_sherbrooke. Override: export IBM_BACKEND=ibm_kyoto
Check https://quantum.ibm.com for available backends before Day 5.
"""

import os, json, logging, sys

src_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if src_path not in sys.path:
    sys.path.insert(0, src_path)

PROJECT_ROOT  = os.path.dirname(src_path)
IBM_BACKEND   = "ibm_frez"
IBM_TASK_IDX  = [0, 2, 4, 6]   # sensitivities: 0.9, 0.8, 0.95, 0.7

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def build_reduced_qubo_for_ibm():
    from rqaoa.qubo_builder import build_qubo_from_tasks, DEFAULT_TASKS
    from rqaoa.qubo_converter import convert_numpy_qubo_to_openqaoa_dict
    tasks  = [DEFAULT_TASKS[i] for i in IBM_TASK_IDX]
    matrix = build_qubo_from_tasks(tasks)
    d      = convert_numpy_qubo_to_openqaoa_dict(matrix)
    logger.info(f"4-task QUBO ready: {len(d)} entries")
    return d, len(tasks), tasks   # ← return all three


def run_aer_reference(qubo_dict: dict) -> dict:
    from rqaoa.rqaoa_runner import run_rqaoa_optimizer
    logger.info("Aer reference simulation (4 tasks)...")
    result = run_rqaoa_optimizer(qubo_dict, num_variables=4)
    logger.info(f"Aer result: {result}")
    return result


if __name__ == "__main__":
    from rqaoa.qubo_builder import DEFAULT_TASKS
    print("IBM task subset:")
    for idx in IBM_TASK_IDX:
        t = DEFAULT_TASKS[idx]
        print(f"  Task {idx}: sens={t.memory_sensitivity}, mem={t.memory_requirement_mb}MB")

    qubo   = build_reduced_qubo_for_ibm()
    result = run_aer_reference(qubo)

    results_dir = os.path.join(PROJECT_ROOT, "results")
    os.makedirs(results_dir, exist_ok=True)
    path = os.path.join(results_dir, "ibm_aer_reference_result.json")
    with open(path, "w") as f:
        json.dump({"source": "aer_simulator", "task_indices": IBM_TASK_IDX,
                   "assignment": {str(k): v for k, v in result.items()}}, f, indent=2)

    print(f"\nSaved: {path}")
    print(f"IBM_BACKEND: {IBM_BACKEND}")
    print("Check https://quantum.ibm.com before Day 5 to confirm availability!")


