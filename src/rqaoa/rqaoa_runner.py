"""
rqaoa_runner.py — Runs RQAOA on a QUBO problem.

Uses OpenQAOA + local vectorized simulator. Supports 8, 12, and 16
task sizes with recursive cutoff tuned per problem size.
Falls back to a greedy assignment if OpenQAOA is unavailable or fails.

Variable convention: 0 = DRAM, 1 = CXL

Maintained by: Hari (P2 — Infra + Quantum Algo)
"""

import logging
import os
from typing import Dict, Any

from dotenv import load_dotenv
from src.rqaoa.rqaoa_config import (
    RQAOA_LAYERS,
    SHOTS,
    FALLBACK_CXL_BUDGET_MB,
    DEFAULT_FALLBACK_TASK_SIZE_MB,
    IBM_DEVICE_NAME
)

logger = logging.getLogger(__name__)

CUTOFF_BY_SIZE: dict = {
    19: 8,   # 8 tasks + 11 slack bits
    23: 10,   # 12 tasks + 11 slack bits
    27: 12,   # 16 tasks + 12 slack bits
}


def _build_openqaoa_qubo_object(qubo_dict: dict, num_variables: int):
    """
    Converts QUBO dict to OpenQAOA QUBO object.

    OpenQAOA QUBO.__init__ expects:
      n:       number of variables
      terms:   list of lists — [i] for diagonal, [i,j] for off-diagonal
      weights: list of floats, same length as terms

    Args:
        qubo_dict:     {(i, j): coefficient} from qubo_converter.py
        num_variables: total number of binary variables

    Returns:
        openqaoa.problems.QUBO object
    """
    from openqaoa.problems import QUBO as OQ_QUBO  # type: ignore

    terms = []
    weights = []

    for (i, j), coeff in qubo_dict.items():
        if i == j:
            terms.append([i])
        else:
            terms.append([i, j])
        weights.append(float(coeff))

    return OQ_QUBO(n=num_variables, terms=terms, weights=weights)


def _extract_assignment_from_result(result: Any, num_variables: int) -> dict:
    """
    Extracts the best assignment from an RQAOAResult object.

    RQAOAResult is dict-like. The solution is in result['solution'],
    which is a dict of {bitstring: energy}. We take the bitstring
    with the lowest (most negative) energy.

    Args:
        result:        RQAOAResult object from rqaoa_solver.result
        num_variables: expected number of variables

    Returns:
        Dict {variable_index: 0 (DRAM) or 1 (CXL)}
    """
    solution_dict = result['solution']

    # Pick the bitstring with the lowest energy value
    best_bitstring = min(solution_dict, key=lambda k: solution_dict[k])
    best_energy = solution_dict[best_bitstring]
    logger.info(
        "Best bitstring: %s (energy: %.4f)", best_bitstring, best_energy
    )

    # Convert bitstring to assignment dict
    # Pad with zeros on the left if shorter than num_variables
    padded = best_bitstring.zfill(num_variables)
    assignment: Dict[int, int] = {
        i: int(padded[i])
        for i in range(num_variables)
    }

    logger.debug("Solution dict: %s", solution_dict)
    logger.debug("Assignment: %s", assignment)
    return assignment


def run_rqaoa_optimizer(
    qubo_dict: dict,
    num_variables: int,
    use_ibm: bool = False
) -> Dict[int, int]:
    """
    Runs RQAOA and returns the optimal variable assignment.

    Args:
        qubo_dict:     {(i,j): coefficient} from qubo_converter.py
        num_variables: number of binary variables (= number of tasks)
        use_ibm:       if True, attempt to run on IBM Quantum backend

    Returns:
        Dict {variable_index: 0 (DRAM) or 1 (CXL)}
    """
    try:
        from openqaoa import RQAOA  # type: ignore
        from openqaoa.backends import create_device  # type: ignore

        cutoff = CUTOFF_BY_SIZE.get(num_variables, max(3, num_variables // 4))
        logger.info(f"RQAOA: {num_variables} vars | p={RQAOA_LAYERS} | cutoff={cutoff}")

        rqaoa_solver = RQAOA()

        device = None
        if use_ibm:
            load_dotenv()
            token = os.getenv("IBM_QUANTUM_TOKEN")
            if token:
                from qiskit_ibm_provider import IBMProvider  # type: ignore
                try:
                    IBMProvider.save_account(token=token, overwrite=True)
                    logger.info("Saved IBM Quantum token.")
                except Exception as e:
                    logger.warning(f"Could not save IBM Quantum token: {e}")

                device = create_device(location="ibmq", name=IBM_DEVICE_NAME)
                logger.info(f"Configured IBM Quantum device: {IBM_DEVICE_NAME}")
            else:
                logger.warning(
                    "IBM_QUANTUM_TOKEN not found in environment. "
                    "Falling back to local vectorized simulator."
                )

        if device is None:
            device = create_device(location="local", name="vectorized")

        rqaoa_solver.set_device(device)
        rqaoa_solver.set_circuit_properties(p=RQAOA_LAYERS, init_type="ramp")
        rqaoa_solver.set_classical_optimizer(method="cobyla", maxiter=200)
        rqaoa_solver.set_backend_properties(n_shots=SHOTS)
        rqaoa_solver.set_rqaoa_parameters(rqaoa_type="custom", n_cutoff=cutoff)

        oq_qubo = _build_openqaoa_qubo_object(qubo_dict, num_variables)
        rqaoa_solver.compile(oq_qubo)

        logger.info("Optimising... (2-8 min depending on size)")
        rqaoa_solver.optimize()

        return _extract_assignment_from_result(rqaoa_solver.result, num_variables)

    except ImportError as exc:
        logger.error("OpenQAOA import error: %s", exc)
        return _greedy_fallback(qubo_dict, num_variables)
    except Exception as exc:
        logger.error("RQAOA failed: %s", exc)
        return _greedy_fallback(qubo_dict, num_variables)


def _greedy_fallback(qubo_dict: dict, num_variables: int) -> Dict[int, int]:
    """
    Sensitivity-based greedy fallback. NOT a quantum result.
    Used only when OpenQAOA fails.
    """
    logger.warning("GREEDY FALLBACK ACTIVE — result is NOT quantum!")

    diagonal_costs = {i: qubo_dict.get((i, i), 0.0) for i in range(num_variables)}
    sorted_tasks = sorted(diagonal_costs.items(), key=lambda x: x[1], reverse=True)

    assignment: Dict[int, int] = {}
    cxl_budget: float = FALLBACK_CXL_BUDGET_MB

    try:
        from src.rqaoa.qubo_builder import DEFAULT_TASKS, TASKS_12, TASKS_16
        all_tasks = DEFAULT_TASKS + [t for t in TASKS_12 if t.task_id >= 8] \
                                  + [t for t in TASKS_16 if t.task_id >= 12]
        sizes = {t.task_id: t.memory_requirement_mb for t in all_tasks}
    except ImportError:
        sizes = {i: DEFAULT_FALLBACK_TASK_SIZE_MB for i in range(num_variables)}

    for task_id, _cost in sorted_tasks:
        size = sizes.get(task_id, DEFAULT_FALLBACK_TASK_SIZE_MB)
        if cxl_budget >= size:
            assignment[task_id] = 1   # CXL
            cxl_budget -= size
        else:
            assignment[task_id] = 0   # DRAM
    return assignment
