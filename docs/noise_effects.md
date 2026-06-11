# Noise Effects: IBM Quantum QPU vs. Aer Simulation

This document outlines the comparative analysis of running the RQAOA optimization for CXL-Aware Hybrid Scheduling on a real IBM Quantum device (e.g., `ibm_osaka`) versus the local `qiskit-aer` vectorized simulator.

## Ideal Simulation (Aer)
The local simulation uses a noise-free environment. For an 8-task QUBO model encoded into a 19-variable Hamiltonian (8 task bits + 11 slack bits):
- **Convergence:** The COBYLA optimizer achieves smooth convergence to the theoretical minimum energy state.
- **Feasibility:** The extracted bitstring rigorously satisfies the DRAM capacity constraint, with slack variables correctly absorbing the capacity margin. The constraint residual is typically `0.0`.
- **Latency Cost:** Provides the optimal scheduling baseline, perfectly distributing highly memory-sensitive tasks to DRAM.

## Real Hardware (IBM QPU)
When running the same circuit (compiled with `p=3` layers and `n_cutoff=3`) on a real IBM QPU, we observe characteristic NISQ-era (Noisy Intermediate-Scale Quantum) effects:

### 1. Readout and Gate Errors
- **Bit-flip Noise:** The raw output bitstring occasionally exhibits single-bit or multi-bit flips due to SPAM (State Preparation and Measurement) errors.
- **Impact on Slack Variables:** A flipped slack bit severely alters the decoded slack value (since slack bits are encoded as $2^k$). This leads to a false validation failure where the constraint residual appears non-zero (e.g., residual $> 100$ MB).

### 2. Barren Plateaus and Optimization Stalls
- Hardware noise flattens the energy landscape. The classical optimizer (COBYLA) struggles to find clear gradients during the parameter update loops.
- **Result:** The RQAOA may terminate at a suboptimal local minimum, producing a task assignment that is roughly equivalent to a Greedy fallback, rather than finding the absolute global minimum.

### 3. Mitigation Strategies for Production
To fully utilize real quantum hardware for this scheduling model, the following error mitigation techniques are required:
- **Measurement Error Mitigation (MEM):** Applying a calibration matrix to correct bit-flip probabilities.
- **Circuit Layer Reduction:** Tuning RQAOA `p=1` or `p=2` to reduce gate depth, minimizing decoherence at the cost of theoretical approximation accuracy.

**Conclusion:**
While the mathematical formulation is proven on the Aer simulator, current real-hardware submissions should be treated as experimental demonstrations. The orchestrator must always run the `validate_assignment()` check and fallback to the Classical Priority-Weighted Greedy scheduler if the QPU bitstring violates the DRAM capacity constraint.
