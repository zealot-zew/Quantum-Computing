"""
ibm_quantum_submit.py — Submits 5-task QUBO to IBM Quantum hardware via Qiskit Runtime.
Bypasses OpenQAOA device layer (ibmq location unavailable in openqaoa-core only installs).
Uses SamplerV2 + QAOA ansatz directly via qiskit_ibm_runtime.
"""
import logging, warnings

# Silence all the noisy qiskit/pkg_resources errors
warnings.filterwarnings("ignore")
for noisy in [
    "qiskit",
    "qiskit_ibm_runtime",
    "backend_converter",
    "qiskit.transpiler",
    "stevedore",        # pkg_resources loader
]:
    logging.getLogger(noisy).setLevel(logging.CRITICAL)
import json, os, logging, sys, numpy as np
src_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if src_path not in sys.path:
    sys.path.insert(0, src_path)
PROJECT_ROOT = os.path.dirname(src_path)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

IBM_BACKEND =  "ibm_fez"


def load_api_token() -> str:
    env_path = os.path.join(PROJECT_ROOT, ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                if line.startswith("IBM_QUANTUM_TOKEN="):
                    return line.strip().split("=", 1)[1]
    raise FileNotFoundError(f".env not found at {env_path}")


def load_crn() -> str:
    env_path = os.path.join(PROJECT_ROOT, ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                if line.startswith("IBM_CRN="):
                    return line.strip().split("=", 1)[1]
    raise FileNotFoundError("IBM_CRN not found in .env")


def _build_qaoa_circuit(qubo_dict: dict, n: int, p: int = 1):
    """Build a QAOA ansatz circuit from a QUBO dict using Qiskit."""
    from qiskit.circuit import QuantumCircuit, ParameterVector
    from qiskit.circuit.library import ZZFeatureMap
    import numpy as np

    # Build cost operator as a list of (coeff, [qubit_i], [qubit_j]) terms
    # then construct the QAOA circuit manually for full control
    gamma = ParameterVector("γ", p)
    beta  = ParameterVector("β", p)

    qc = QuantumCircuit(n)
    # Initial state: uniform superposition
    qc.h(range(n))

    for layer in range(p):
        # Cost layer: ZZ terms from off-diagonal, Z terms from diagonal
        for (i, j), coeff in qubo_dict.items():
            if abs(coeff) < 1e-10:
                continue
            if i == j:
                # Z_i term: Rz rotation
                qc.rz(2 * gamma[layer] * coeff, i)
            else:
                # ZZ_ij term: CNOT + Rz + CNOT
                qc.cx(i, j)
                qc.rz(2 * gamma[layer] * coeff, j)
                qc.cx(i, j)
        # Mixer layer: Rx rotations
        qc.rx(2 * beta[layer], range(n))

    qc.measure_all()
    return qc, gamma, beta


def _counts_to_best_assignment(counts: dict, n: int) -> dict:
    """Extract the most-frequent bitstring and convert to {var: 0/1} dict."""
    best_bs = max(counts, key=counts.get)
    # Qiskit bitstrings are MSB-first (rightmost = qubit 0)
    padded = best_bs.replace(" ", "").zfill(n)
    return {i: int(padded[-(i + 1)]) for i in range(n)}


def _run_local_aer_reference(qubo_dict: dict, n: int) -> dict:
    from openqaoa import QAOA
    from openqaoa.backends import create_device
    from rqaoa.rqaoa_runner import _build_openqaoa_qubo_object

    device = create_device(location="local", name="vectorized")
    qaoa = QAOA()
    qaoa.set_device(device)
    qaoa.set_circuit_properties(p=1, init_type="ramp")
    qaoa.set_classical_optimizer(method="cobyla", maxiter=200)
    qaoa.set_backend_properties(n_shots=1024)
    oq_qubo = _build_openqaoa_qubo_object(qubo_dict, num_variables=n)
    qaoa.compile(oq_qubo)
    qaoa.optimize()

    # Try best_solution dict first (newer OpenQAOA)
    if hasattr(qaoa.result, "best_solution") and qaoa.result.best_solution:
        return {int(k): int(v) for k, v in qaoa.result.best_solution.items()}

    # Fall back to most_probable_states bitstring (older OpenQAOA)
    bs = qaoa.result.most_probable_states["solutions_bitstrings"][0]
    padded = bs.zfill(n)
    return {i: int(padded[-(i + 1)]) for i in range(n)}


def submit_to_ibm_and_compare() -> dict:
    from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2, Session
    from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
    from rqaoa.ibm_quantum_prep import build_reduced_qubo_for_ibm, IBM_TASK_IDX

    api_token = load_api_token()
    crn       = load_crn()

    # ── 1. Build QUBO ────────────────────────────────────────────────────────
    qubo_dict, n_vars, tasks = build_reduced_qubo_for_ibm()
    logger.info(f"QUBO: {n_vars} variables, {len(qubo_dict)} terms")

    # ── 2. Local Aer reference (save to disk so we have it even if IBM fails) ─
    results_dir = os.path.join(PROJECT_ROOT, "results")
    os.makedirs(results_dir, exist_ok=True)
    aer_path = os.path.join(results_dir, "ibm_aer_reference_result.json")

    if not os.path.exists(aer_path):
        logger.info("Running local Aer reference first...")
        aer_assignment = _run_local_aer_reference(qubo_dict, n_vars)
        with open(aer_path, "w") as f:
            json.dump({"assignment": {str(k): v for k, v in aer_assignment.items()}}, f)
        logger.info(f"Aer reference saved: {aer_path}")
    else:
        with open(aer_path) as f:
            aer_assignment = {int(k): v for k, v in json.load(f)["assignment"].items()}

    # ── 3. Build + transpile QAOA circuit ────────────────────────────────────
    qc, gamma_params, beta_params = _build_qaoa_circuit(qubo_dict, n_vars, p=1)

    service = QiskitRuntimeService(
        channel="ibm_cloud",
        token=api_token,
        instance=crn,
    )
    backend = service.backend(IBM_BACKEND)
    logger.info(f"Connecting to: {backend.name} ({backend.num_qubits} qubits)")

    pm = generate_preset_pass_manager(optimization_level=1, backend=backend)

    # Bind parameters to COBYLA-optimised angles (use π/4 as reasonable default
    # if you want a quick hardware test without re-optimising on hardware)
    import numpy as np
    gamma_vals = [np.pi / 4] * 1
    beta_vals  = [np.pi / 8] * 1
    param_map  = {**dict(zip(gamma_params, gamma_vals)),
                  **dict(zip(beta_params,  beta_vals))}
    bound_qc   = qc.assign_parameters(param_map)
    isa_qc     = pm.run(bound_qc)

    # ── 4. Submit via SamplerV2 ───────────────────────────────────────────────
    logger.info("Submitting to IBM hardware...")
    sampler  = SamplerV2(backend=backend)          # no Session wrapper
    job      = sampler.run([isa_qc], shots=512)
    logger.info(f"Job ID: {job.job_id()}  |  https://quantum.ibm.com/jobs/{job.job_id()}")
    logger.info("Waiting for result...")
    pub_result = job.result()[0]

    counts         = pub_result.data.meas.get_counts()
    ibm_assignment = _counts_to_best_assignment(counts, n_vars)
    job_id         = job.job_id()

    # ── 5. Compare + save ────────────────────────────────────────────────────
    matches = sum(1 for i in range(n_vars)
                  if ibm_assignment.get(i) == aer_assignment.get(i))

    comparison = {
        "aer_simulator":      {str(k): v for k, v in aer_assignment.items()},
        "ibm_qpu":            {str(k): v for k, v in ibm_assignment.items()},
        "task_indices":       IBM_TASK_IDX,
        "variables_matching": matches,
        "total_variables":    n_vars,
        "ibm_job_id":         job_id,
        "ibm_backend_used":   IBM_BACKEND,
    }

    out = os.path.join(results_dir, "ibm_qpu_vs_aer_comparison.json")
    with open(out, "w") as f:
        json.dump(comparison, f, indent=2)
    logger.info(f"Saved: {out} | Match: {matches}/{n_vars}")
    return comparison
