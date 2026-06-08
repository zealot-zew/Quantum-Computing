
"""
rqaoa_runner.py

Runs RQAOA on a QUBO problem using OpenQAOA + local vectorized simulator.
Supports 8, 12, and 16 task sizes with cutoff tuned per size.
Falls back to greedy assignment if OpenQAOA fails.

Variable convention: 0 = DRAM, 1 = CXL
"""

import logging, sys, os

src_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from rqaoa.rqaoa_config import RQAOA_LAYERS, SHOTS

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

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
    from openqaoa.problems import QUBO as OQ_QUBO

    terms   = []
    weights = []

    for (i, j), coeff in qubo_dict.items():
        if i == j:
            terms.append([i])
        else:
            terms.append([i, j])
        weights.append(float(coeff))

    return OQ_QUBO(n=num_variables, terms=terms, weights=weights)


def _extract_assignment_from_result(result, num_variables: int) -> dict:
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
    logger.info(f"Best bitstring: {best_bitstring} "
                f"(energy: {solution_dict[best_bitstring]:.4f})")

    # Convert bitstring to assignment dict
    # Pad with zeros on the left if shorter than num_variables
    padded = best_bitstring.zfill(num_variables)
    print("\nSOLUTION DICT")
    print(solution_dict)
    print("Best bitstring:", best_bitstring)
    forward = {i:int(best_bitstring[i])
           for i in range(num_variables)}

    reverse = {i:int(best_bitstring[::-1][i])
           for i in range(num_variables)}
    assignment = {
    i: int(padded[i])
    for i in range(num_variables)
}
    print("\nDECODED")
    for i in range(num_variables):
        print(i, padded[i], assignment[i])
    logger.info(f"Assignment: {assignment}")
    return assignment


def run_rqaoa_optimizer(qubo_dict: dict, num_variables: int) -> dict:
    """
    Runs RQAOA and returns the optimal variable assignment.

    Args:
        qubo_dict:     {(i,j): coefficient} from qubo_converter.py
        num_variables: number of binary variables (= number of tasks)

    Returns:
        Dict {variable_index: 0 (DRAM) or 1 (CXL)}
    """
    try:
        from openqaoa import RQAOA
        from openqaoa.backends import create_device

        cutoff = CUTOFF_BY_SIZE.get(num_variables, max(3, num_variables // 4))
        logger.info(f"RQAOA: {num_variables} vars | p={RQAOA_LAYERS} | cutoff={cutoff}")

        rqaoa_solver = RQAOA()
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

    except ImportError as e:
        logger.error(f"OpenQAOA import error: {e}")
        return _greedy_fallback(qubo_dict, num_variables)
    except Exception as e:
        logger.error(f"RQAOA failed: {e}")
        return _greedy_fallback(qubo_dict, num_variables)


def _greedy_fallback(qubo_dict: dict, num_variables: int) -> dict:
    """
    Sensitivity-based greedy fallback. NOT a quantum result.
    Used only when OpenQAOA fails.
    """
    logger.warning("GREEDY FALLBACK ACTIVE — result is NOT quantum!")

    diagonal_costs = {i: qubo_dict.get((i, i), 0.0) for i in range(num_variables)}
    sorted_tasks   = sorted(diagonal_costs.items(), key=lambda x: x[1], reverse=True)

    assignment: dict = {}
    cxl_budget: float = 4096.0

    try:
        from rqaoa.qubo_builder import DEFAULT_TASKS, TASKS_12, TASKS_16
        all_tasks = DEFAULT_TASKS + [t for t in TASKS_12 if t.task_id >= 8] \
                                  + [t for t in TASKS_16 if t.task_id >= 12]
        sizes = {t.task_id: t.memory_requirement_mb for t in all_tasks}
    except ImportError:
        sizes = {i: 200.0 for i in range(num_variables)}

    for task_id, _cost in sorted_tasks:
        size = sizes.get(task_id, 200.0)
        if cxl_budget >= size:
            assignment[task_id] = 1   # CXL
            cxl_budget -= size
        else:
            assignment[task_id] = 0   # DRAM
    return assignment
