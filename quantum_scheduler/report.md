# Quantum-Assisted Optimization Engine for CXL-Aware Hybrid Scheduling

**Team:** Anjana, Hari, Smarth, Vikas, Devandra  

**Institution:** BMS College of Engineering

---

## Abstract

*(To be written on Day 6 after results are available.)*

---

## 1. Problem Statement

### 1.1 Limitations of Classical Scheduling

Traditional CPU scheduling algorithms such as First-Come-First-Served (FCFS) and Round Robin (RR) were designed for homogeneous memory systems. With the emergence of heterogeneous memory architectures — particularly CXL-enabled tiered memory — these schedulers exhibit critical gaps:

- **Memory Tier Unawareness:** Classical schedulers do not distinguish between local DRAM (~80–120 ns) and CXL-attached memory (~200–400+ ns).
- **Sequential Bottlenecks:** FCFS suffers from the convoy effect, delaying short tasks behind long-running ones.
- **Combinatorial Complexity:** Optimal task-to-memory-tier mapping is an NP-hard combinatorial problem that scales exponentially with task count.

### 1.2 Motivation

*(Expand: why quantum-assisted optimization is a promising approach here.)*

---

## 2. Methodology

### 2.1 QUBO Formulation

The scheduling problem is modeled as a Quadratic Unconstrained Binary Optimization (QUBO) problem.

- Each binary variable $x_i \in \{0, 1\}$ represents whether task $i$ is assigned to CXL ($x_i = 1$) or DRAM ($x_i = 0$).
- **Diagonal terms:** Encode latency cost per task based on memory sensitivity and tier difference.
- **Off-diagonal terms:** Encode DRAM capacity constraint as a penalty.

$$Q_{ii} = \text{sensitivity}_i \times (\text{CXL\_latency} - \text{DRAM\_latency}) \times \text{memory\_mb}_i$$

*(Full matrix derivation to be added by P1 on Day 2.)*

### 2.2 RQAOA Algorithm

The Recursive Quantum Approximate Optimization Algorithm (RQAOA) is used as the optimization engine.

**Key steps:**
1. Encode QUBO as a parameterized quantum circuit (QAOA ansatz).
2. Optimize circuit parameters using a classical optimizer.
3. Identify the strongest correlation between variables using expectation values.
4. Fix that variable and reduce the problem size by one.
5. Repeat recursively until the problem is small enough for classical exact solving.

**Implementation:** OpenQAOA library with Qiskit Aer backend for simulation; IBM Quantum for hardware validation.

*(Detailed circuit description and recursion depth to be added by P1 on Day 3.)*

### 2.3 NUMA-Based CXL Simulation

Physical CXL hardware is unavailable, so CXL-like behavior is simulated using Linux NUMA:

| Memory Tier | NUMA Node | Simulated Latency |
|-------------|-----------|-------------------|
| Local DRAM  | Node 0    | Baseline (~80–120 ns) |
| CXL Memory  | Node 1    | +200–400 ns penalty injected via `time.sleep()` |

Workloads are bound using `numactl`:
- DRAM tasks: `numactl --membind=0`
- CXL tasks: `numactl --membind=1`

**Assumptions:**
- Memory treated as logically shared across tiers.
- Cache coherence and protocol-level behavior are not modeled.
- Bandwidth throttling approximated by access rate constraints.

*(Full simulation parameters to be added by P3/P4 on Day 2–3.)*

---

## 3. System Design

### 3.1 Architecture Overview

The system comprises three layers:

1. **Optimization Layer** — RQAOA computes near-optimal task-to-tier assignments.
2. **Scheduling Layer** — Interprets the RQAOA bitstring output; also implements classical baselines (FCFS, RR, Greedy, Priority-Weighted Greedy).
3. **Execution Layer** — Enforces placement via `numactl` subprocess binding.

### 3.2 Execution Flow

```
Input Tasks → QUBO Builder → RQAOA Optimizer → Bitstring Assignment
     → Scheduler Interpreter → numactl Executor → Metric Collector → Report
```

### 3.3 Classical Schedulers (Baselines)

- **FCFS:** Assigns in arrival order; fills DRAM first, then overflows to CXL.
- **Round Robin:** Alternates assignments between DRAM and CXL.
- **Greedy:** Sorts by memory sensitivity descending; fills DRAM first.
- **Priority-Weighted Greedy:** Sorts by `priority × sensitivity`; fills DRAM first.

---

## 4. Results & Discussion

*(To be completed on Day 5–6 after all experiments are run.)*

### 4.1 Classical Scheduler Comparison

*(Insert `results/all_schedulers_summary.csv` table here.)*

### 4.2 RQAOA vs Classical — Task Placement

*(Insert QUBO heatmap and bitstring comparison plots.)*

### 4.3 RQAOA Simulated vs IBM Quantum Hardware

*(Insert comparison of Qiskit Aer simulation result vs IBM QPU result.)*

### 4.4 Memory Tier Impact on Execution Time

*(Insert latency vs tier plots from `results/plots/`.)*

---

## 5. Limitations

- **Problem size:** Limited to 8 tasks due to current quantum hardware qubit constraints.
- **Offline scheduling only:** No real-time or dynamic rescheduling.
- **Approximate CXL modeling:** Latency injection and bandwidth throttling are approximations; physical CXL protocol behavior is not modeled.
- **No optimality guarantee:** RQAOA provides near-optimal, not globally optimal, solutions.
- **Noise:** IBM Quantum hardware results are noisy; error mitigation is not applied.

---

## 6. References

1. Farhi, E., Goldstone, J., & Gutmann, S. (2014). *A Quantum Approximate Optimization Algorithm.* arXiv:1411.4028.
2. Bravyi, S., et al. (2020). *Obstacles to Variational Quantum Optimization from Symmetry Protection.* Physical Review Letters.
3. OpenQAOA Documentation. https://github.com/entropicalabs/openqaoa
4. PyQUBO. https://github.com/recruit-communications/pyqubo
5. Qiskit. https://github.com/Qiskit/qiskit
6. CXL Consortium. *CXL 3.0 Specification.* https://www.computeexpresslink.org
7. Linux `numactl` man page. https://linux.die.net/man/8/numactl
8. Reference Scheduler: https://github.com/aboev/quantum-job-scheduler

---

*Report maintained by: Devandra (P5 — Documentation & Integration Lead)*
