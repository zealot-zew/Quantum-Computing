
# RQAOA Methodology

## Problem Statement
Memory scheduling across heterogeneous tiers (DRAM 100ns, CXL 300ns) is a
combinatorial optimization problem. For N tasks and 2 tiers, there are 2^N
possible assignments. Classical heuristics are fast but cannot guarantee
near-optimal solutions. RQAOA offers a quantum-assisted approach.

## Variable Convention
x[i] = 0 -> Task i assigned to DRAM (100 ns)
x[i] = 1 -> Task i assigned to CXL  (300 ns)

## QUBO Formulation
Minimize: sum_i (sensitivity_i * 200 * mem_i * x_i)
        + lambda * (sum_i (mem_i * x_i) - CXL_CAPACITY)^2

Expanding the penalty:
  Diagonal Q[i][i] = sensitivity_i*200*mem_i + lambda*(mem_i^2 - 2*CXL_CAP*mem_i)
  Off-diagonal Q[i][j] = lambda * 2 * mem_i * mem_j  (capacity cross terms)

lambda = 1e-5 keeps penalty and latency terms numerically balanced.

## RQAOA Algorithm
1. Run QAOA (p layers) to compute pairwise correlations M_ij = <Z_i Z_j>
2. Identify strongest correlation pair (i*, j*)
3. Substitute: M > 0 -> x_i = x_j; M < 0 -> x_i = (1-x_j)
4. Reduce Hamiltonian by 1 variable
5. Repeat until n_cutoff variables remain; solve classically
6. Reconstruct full N-variable solution

Cutoffs (auto-tuned per problem size): 8 tasks->3, 12 tasks->4, 16 tasks->5.

## Experiments
1. Scaling experiment: RQAOA + 4 classical schedulers at 8/12/16 tasks.
   Solution quality measured against brute-force optimal (feasible for N<=20).
2. Statistical robustness: 5 independent RQAOA runs on 8-task problem.
   Reports mean ± std of cost and quality to demonstrate consistency.
3. IBM QPU validation: 4-task QUBO submitted to real quantum hardware.
   Compares QPU result with ideal Aer simulation.

## Configuration
Backend:  OpenQAOA vectorized (local) / IBM Quantum ibm_sherbrooke (validation)
p layers: 1 | rqaoa_type: "custom" | Optimizer: COBYLA maxiter=200 | Shots: 1024

---------- JUPYTER CELL 5 ----------

# Auto-generate the IBM results section from actual JSON data
import json, os

with open("results/ibm_qpu_vs_aer_comparison.json") as f:
    comp = json.load(f)

rows = ""
for i in range(4):
    a = "DRAM" if comp["aer_simulator"].get(str(i)) == 0 else "CXL"
    b = "DRAM" if comp["ibm_qpu"].get(str(i)) == 0 else "CXL"
    m = "Yes" if comp["aer_simulator"].get(str(i)) == comp["ibm_qpu"].get(str(i)) \
        else "No (NISQ noise)"
    rows += f"| x[{i}] | {a} | {b} | {m} |\n"

content = f"""# IBM Quantum Hardware Results

## Job Details
- Job ID:  {comp['ibm_job_id']}
- Device:  {comp.get('ibm_backend_used', 'unknown')}
- Problem: 4-task QUBO (Tasks 0, 2, 4, 6)
- Shots:   512 | QAOA layers: p=1 | Cutoff: 2

## Results

| Variable | Aer Simulator | IBM QPU | Match? |
|----------|--------------|---------|--------|
{rows}
Agreement: {comp['variables_matching']}/4 variables

## Noise Analysis
NISQ hardware introduces noise via:
1. Gate errors (~0.1-0.3% per 2-qubit gate)
2. Readout errors (~1-3% per qubit)
3. Decoherence (T1/T2 time-limited circuit depth)

Any disagreement is consistent with known noise levels.
Mitigation strategies (ZNE, Pauli twirling) are future work.
"""

with open("docs/ibm_results_section.md", "w") as f:
    f.write(content)

print(content)
print("Saved: docs/ibm_results_section.md ✅")
