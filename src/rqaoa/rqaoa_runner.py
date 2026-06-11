"""
changed
rqaoa_runner.py — RQAOA optimizer.
Variable convention: 0 = DRAM, 1 = CXL.
"""

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

CUTOFF_BY_SIZE: dict = {8: 2, 12: 2, 16: 3}


def _build_openqaoa_qubo_object(qubo_dict: dict, num_variables: int):
    """Converts QUBO dict to OpenQAOA QUBO object using terms/weights constructor."""
    from openqaoa.problems import QUBO as OQ_QUBO
    terms, weights = [], []
    for (i, j), coeff in qubo_dict.items():
        terms.append([i] if i == j else [i, j])
        weights.append(float(coeff))
    return OQ_QUBO(n=num_variables, terms=terms, weights=weights)


def _extract_best_solution(result, num_variables: int) -> dict:
    """
    Extracts the best assignment from RQAOAResult.

    OpenQAOA stores results differently across versions:
      - Newer: result.best_solution  -> {var_index: 0_or_1}
      - Older: result['solution']    -> {'bitstring': energy, ...}
                bitstring is MSB-first so variable 0 = rightmost character.

    We try both, then fall back to reading the lowest-energy bitstring.
    """
    # Attempt 1: attribute access (newer OpenQAOA)
    if hasattr(result, "best_solution") and result.best_solution:
        logger.info("Using result.best_solution")
        return {int(k): int(v) for k, v in result.best_solution.items()}

    # Attempt 2: dict-style access (older OpenQAOA)
    try:
        solution_dict = result["solution"]
        best_bs = min(solution_dict, key=lambda k: solution_dict[k])
        logger.info(f"Using result['solution'], best bitstring: {best_bs}")
        padded = best_bs.zfill(num_variables)
        # Variable 0 = rightmost character (MSB-first convention)
        return {i: int(padded[-(i + 1)]) for i in range(num_variables)}
    except (KeyError, TypeError):
        pass

    # Attempt 3: result.optimized_results (some intermediate versions)
    try:
        sol = result.optimized_results
        best_bs = min(sol, key=lambda k: sol[k])
        logger.info(f"Using result.optimized_results, best bitstring: {best_bs}")
        padded = best_bs.zfill(num_variables)
        return {i: int(padded[-(i + 1)]) for i in range(num_variables)}
    except (AttributeError, TypeError):
        pass

    raise RuntimeError(
        f"Cannot extract solution from RQAOAResult. "
        f"Available attributes: {[a for a in dir(result) if not a.startswith('_')]}"
    )


def run_rqaoa_optimizer(
    qubo_dict:        dict,
    num_variables:    int,
    dram_capacity_mb: float = 1956.0,
) -> dict:
    """
    Runs RQAOA and returns the variable assignment.

    Args:
        qubo_dict:        {(i,j): coefficient} from qubo_converter.
        num_variables:    Number of binary variables (= number of tasks).
        dram_capacity_mb: Passed to fallback if RQAOA fails.

    Returns:
        {variable_index: 0 (DRAM) or 1 (CXL)}
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

        logger.info("Optimising... (2-8 min)")
        rqaoa_solver.optimize()

        assignment = _extract_best_solution(rqaoa_solver.result, num_variables)
        logger.info(f"Raw assignment from RQAOA: {assignment}")
        return assignment

    except ImportError as e:
        logger.error(f"OpenQAOA import error: {e}")
        return _greedy_fallback(qubo_dict, num_variables, dram_capacity_mb)
    except Exception as e:
        print(f"  [RQAOA FAILED SILENTLY]: {e}")
        return _greedy_fallback(qubo_dict, num_variables, dram_capacity_mb)


def _greedy_fallback(
    qubo_dict:        dict,
    num_variables:    int,
    dram_capacity_mb: float,
) -> dict:
    """
    Sensitivity-based greedy. NOT quantum. Used only when OpenQAOA fails.
    High diagonal = high sensitivity = assign to DRAM first.
    """
    logger.warning("GREEDY FALLBACK ACTIVE — result is NOT quantum!")

    diagonal_costs = {i: qubo_dict.get((i, i), 0.0) for i in range(num_variables)}
    sorted_vars    = sorted(diagonal_costs.items(), key=lambda x: x[1], reverse=True)

    assignment:  dict  = {}
    dram_budget: float = dram_capacity_mb

    try:
        from rqaoa.qubo_builder import DEFAULT_TASKS, TASKS_12, TASKS_16
        all_tasks = (DEFAULT_TASKS
                     + [t for t in TASKS_12 if t.task_id >= 8]
                     + [t for t in TASKS_16 if t.task_id >= 12])
        sizes = {t.task_id: t.memory_requirement_mb for t in all_tasks}
    except ImportError:
        sizes = {}

    for var_id, _cost in sorted_vars:
        size = sizes.get(var_id, 200.0)
        if dram_budget >= size:
            assignment[var_id] = 0
            dram_budget -= size
        else:
            assignment[var_id] = 1

    return assignment
