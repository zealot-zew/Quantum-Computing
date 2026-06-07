# Quantum-Assisted Optimization Engine for CXL-Aware Hybrid Scheduling

**Report Version:** 0.2 (Day 2 Draft)
**Authors:** Anjana, Hari, Smarth, Vikas, Devandra
**Institution:** BMS College of Engineering
**Department:** Information Science and Engineering
**Date:** 2025

---

## Table of Contents

1. [Abstract](#1-abstract)
2. [Problem Statement](#2-problem-statement)
3. [Methodology](#3-methodology)
   - 3.1 [QUBO Formulation](#31-qubo-formulation)
   - 3.2 [RQAOA Algorithm](#32-rqaoa-algorithm)
   - 3.3 [Execution Layer — Task Orchestrator](#33-execution-layer--task-orchestrator)
   - 3.4 [NUMA-Based CXL Simulation](#34-numa-based-cxl-simulation)
   - 3.5 [Classical Schedulers](#35-classical-schedulers)
   - 3.6 [Evaluation Metrics](#36-evaluation-metrics)
4. [System Design](#4-system-design)
5. [Results and Discussion](#5-results-and-discussion)
6. [Limitations](#6-limitations)
7. [References](#7-references)

---

## 1. Abstract

*To be written on Day 6 after all experimental results are collected.*

---

## 2. Problem Statement

Modern computing systems are undergoing a fundamental architectural shift. The emergence of Compute Express Link (CXL), a high-speed interconnect standard built on the PCIe physical layer, has made it possible to attach large pools of memory to servers without requiring physical DIMM slots on the host board. This disaggregated memory model introduces a new tier in the memory hierarchy and fundamentally changes the assumptions under which classical scheduling algorithms were designed.

Classical CPU scheduling algorithms such as First-Come-First-Served (FCFS) and Round Robin (RR) were developed for relatively homogeneous systems where all memory accesses could be assumed to carry similar latency penalties. FCFS assigns the CPU to processes in strict arrival order, which introduces the well-known convoy effect: short-duration, memory-sensitive tasks are forced to queue behind long-running processes that occupy DRAM, even when the short tasks would benefit far more from DRAM placement. Round Robin improves CPU fairness through time-sliced preemption, but does so without any awareness of where a task's memory is actually located.

The latency gap between these two tiers is not marginal. Local DRAM on a modern server typically delivers access latencies in the range of 80 to 120 nanoseconds. CXL-attached memory introduces serialisation overhead through the PCIe fabric, resulting in effective access latencies of 200 to 400 nanoseconds or more — a penalty of two to four times relative to DRAM. For workloads that perform frequent random memory accesses, such as in-memory databases, graph processing engines, or real-time analytics pipelines, this latency gap translates directly into degraded throughput and increased tail latency at the application level.

Even modern operating systems with NUMA-aware scheduling heuristics handle this poorly. Linux's CFS scheduler was not conceived with the notion of a memory tier whose latency is determined by a PCIe switch fabric. When CXL memory is presented to the OS as a remote NUMA node, the scheduler may place a latency-critical task on a CXL-mapped memory region simply because the local DRAM node is near capacity, with no mechanism to weigh the sensitivity of the task against the cost of CXL placement.

This creates a combinatorial optimisation challenge. For a system with N tasks and two memory tiers, the total number of possible task-to-memory assignments is 2^N. A system with 8 tasks has 256 possible assignments; a system with 32 tasks has over 4 billion. No greedy or round-robin heuristic can guarantee globally optimal placement, because globally optimal placement requires reasoning simultaneously about all task sensitivities, memory capacity constraints, and inter-task interference.

This project proposes a Quantum-Assisted Optimisation Engine that uses the Recursive Quantum Approximate Optimisation Algorithm (RQAOA) to compute near-optimal task-to-memory-tier assignments by formulating the scheduling problem as a QUBO problem and solving it using quantum-classical hybrid methods.

---

## 3. Methodology

### 3.1 QUBO Formulation

The memory placement scheduling problem is modelled as a Quadratic Unconstrained Binary Optimisation (QUBO) problem expressible in the form:

```
minimise:  x^T Q x
```

where **x** is a binary vector of decision variables and **Q** is a real-valued square matrix encoding both the objective function and all constraints as penalty terms.

#### Decision Variables

Each task i is assigned a binary variable x_i:

- **x_i = 0** — task i placed in local DRAM (Node 0, ~100 ns latency)
- **x_i = 1** — task i placed in CXL-attached memory (Node 1, ~300 ns latency)

#### Objective: Minimise Total Memory Access Cost

The diagonal terms of Q encode the per-task latency cost:

```
Q[i][i] = sensitivity_i × (CXL_LATENCY - DRAM_LATENCY) × memory_mb_i
```

#### Constraint: DRAM Capacity

Total memory assigned to DRAM must not exceed capacity C_DRAM. Encoded as:

```
Penalty = P × (Σ_i (1 - x_i) × memory_mb_i  -  C_DRAM)²
```

Expanding this produces off-diagonal terms Q[i][j] encoding pairwise capacity coupling between tasks competing for DRAM. The full Q is an 8×8 symmetric matrix implemented in `qubo/qubo_builder.py`.

---

### 3.2 RQAOA Algorithm

The Recursive Quantum Approximate Optimisation Algorithm (RQAOA) is used as the optimisation engine.

**Key steps:**
1. Encode QUBO as a parameterised quantum circuit (QAOA ansatz).
2. Optimise circuit parameters using COBYLA classical optimiser.
3. Identify the strongest correlation between variables using expectation values.
4. Fix that variable and reduce the problem size by one.
5. Repeat recursively until the problem is small enough for classical exact solving.

**Implementation:** OpenQAOA library with Qiskit Aer backend for local simulation; IBM Quantum for hardware validation.

*Detailed circuit description and recursion depth to be added by P1 (Anjana) on Day 3.*

---

### 3.3 Execution Layer — Task Orchestrator

The execution layer is implemented in `src/executor/task_orchestrator.py` (maintained by P2 — Hari). It receives the scheduler's assignment dict and launches all 8 tasks as concurrent subprocesses using Python's `subprocess.Popen`.

**Concurrency model:** All 8 tasks start at roughly the same wall-clock time. Total wall time equals the slowest task's duration, not the sum of all tasks.

Each task is bound to its assigned NUMA node using `numactl`:

| Tier | numactl command |
|------|----------------|
| DRAM | `numactl --cpunodebind=0 --membind=0` |
| CXL  | `numactl --cpunodebind=1 --membind=1` |

If `numactl` is unavailable, the orchestrator automatically falls back to running without NUMA binding.

Each subprocess runs `task_runner.py`, which:
1. Allocates the requested memory using NumPy (`np.random.rand`)
2. Simulates memory-bound work by iterating over the array in chunks
3. Injects CXL latency: `sleep = (3.0 - 1.0) × T_compute` so CXL total = 3× DRAM (matching 300 ns / 100 ns ratio)
4. Prints CSV result to stdout: `task_id,node,start_time_s,end_time_s,duration_s`

**QUBO Format Converter:** `src/rqaoa/qubo_converter.py` translates PyQUBO string keys (`'x[0]'`) to OpenQAOA integer keys (`(0,0)`) required by the quantum circuit runner. Normalises to upper-triangular form and merges duplicate entries.

**Typical call chain:**
```
scheduler.schedule(tasks)           → assignment dict
task_orchestrator.run_all_tasks()   → list of result dicts
evaluation.metrics.*                → computed metrics
```

---

### 3.4 NUMA-Based CXL Simulation

Physical CXL hardware is unavailable. CXL-like behaviour is simulated using Linux NUMA:

| Memory Tier | NUMA Node | Simulated Latency |
|-------------|-----------|-------------------|
| Local DRAM  | Node 0    | Baseline (~80–120 ns) |
| CXL Memory  | Node 1    | 3× penalty injected via `time.sleep()` |

**Assumptions:** Memory treated as logically shared. Cache coherence not modelled. Bandwidth throttling approximated by access rate constraints.

*Full simulation parameters to be added by P3 (Smarth) on Day 3.*

---

### 3.5 Classical Schedulers

Four classical schedulers are implemented in `src/scheduler/` as baselines (maintained by P3 — Smarth). All inherit from `BaseScheduler` in `src/scheduler/scheduler_interface.py` (maintained by P5 — Devandra):

- **FCFS:** Assigns in arrival order; fills DRAM first, overflows to CXL.
- **Round Robin:** Alternates between DRAM and CXL by index parity; falls back if preferred tier is full.
- **Greedy:** Sorts by `memory_sensitivity` descending; most-sensitive tasks get DRAM first.
- **Priority-Weighted Greedy:** Sorts by `priority × sensitivity` descending; fills DRAM first.

*Worked examples with the 8-task set to be added by P3 on Day 6.*

---

### 3.6 Evaluation Metrics

*To be written by P4 (Vikas) on Day 6 — defines average latency, makespan, DRAM utilisation rate, and total QUBO weighted cost.*

---

## 4. System Design

### 4.1 Architecture Overview

The system comprises three layers:

1. **Optimization Layer** — RQAOA computes near-optimal task-to-tier assignments via QUBO.
2. **Scheduling Layer** — Interprets RQAOA bitstring output; implements classical baselines.
3. **Execution Layer** — Enforces placement via `numactl` and collects timing metrics.

### 4.2 Execution Flow

```
Input Tasks → QUBO Builder → RQAOA Optimizer → Bitstring Assignment
     → Scheduler Interpreter → numactl Executor → Metric Collector → Report
```

### 4.3 Component Table

| Component | Strategy | Technology |
|-----------|----------|------------|
| Data Center Model | 8 tasks, 2 memory tiers | Python (NetworkX) |
| Optimization Engine | RQAOA | OpenQAOA |
| Local Testing | Classical simulation | Qiskit Aer |
| Quantum Validation | Small-scale execution | IBM Quantum |
| Execution Layer | NUMA binding | numactl |

---

## 5. Results and Discussion

*To be written on Day 6 after all experiments are run.*

- *(a) Comparison table of all schedulers across 3 metrics*
- *(b) Bar charts from `results/plots/`*
- *(c) IBM Quantum hardware run results and noise comparison*
- *(d) Discussion of RQAOA scheduling quality vs greedy baselines*

---

## 6. Limitations

- **Problem size:** Limited to 8 tasks due to current quantum hardware qubit constraints.
- **Offline scheduling only:** No real-time or dynamic rescheduling.
- **Approximate CXL modelling:** Latency injection is an approximation; physical CXL protocol behaviour is not modelled.
- **No optimality guarantee:** RQAOA provides near-optimal, not globally optimal, solutions.
- **Noise:** IBM Quantum hardware results are noisy; error mitigation is not applied.

---

## 7. References

1. Farhi, E., Goldstone, J., & Gutmann, S. (2014). A Quantum Approximate Optimization Algorithm. arXiv:1411.4028.
2. Bravyi, S., et al. (2020). Obstacles to Variational Quantum Optimization from Symmetry Protection. Physical Review Letters, 125(26).
3. OpenQAOA GitHub Repository. https://github.com/entropicalabs/openqaoa
4. PyQUBO GitHub Repository. https://github.com/recruit-communications/pyqubo
5. Qiskit GitHub Repository. https://github.com/Qiskit/qiskit
6. Quantum Job Scheduler Reference. https://github.com/aboev/quantum-job-scheduler
7. CXL Consortium. (2023). CXL Specification Revision 3.0. https://www.computeexpresslink.org
8. Linux numactl documentation. https://linux.die.net/man/8/numactl

---
