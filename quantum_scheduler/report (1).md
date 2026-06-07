# Quantum-Assisted Optimization Engine for CXL-Aware Hybrid Scheduling

**Report Version:** 0.2 (Day 2 Draft)  
**Authors:** Anjana, Hari, Smarth, Vikas, Devandra  
**Institution:** BMS College of Engineering  


---

## Table of Contents

1. [Abstract](#1-abstract)
2. [Problem Statement](#2-problem-statement)
3. [Methodology](#3-methodology)
   - 3.1 [QUBO Formulation](#31-qubo-formulation)
   - 3.2 [RQAOA Algorithm](#32-rqaoa-algorithm)
   - 3.3 [CXL Memory Simulation](#33-cxl-memory-simulation)
   - 3.4 [Classical Schedulers](#34-classical-schedulers)
   - 3.5 [Evaluation Metrics](#35-evaluation-metrics)
4. [Results and Discussion](#4-results-and-discussion)
5. [Limitations](#5-limitations)
6. [References](#6-references)

---

## 1. Abstract

*[To be written on Day 6 after all results are collected — abstract summarises final findings]*

---

## 2. Problem Statement

Modern computing systems are undergoing a fundamental architectural shift. The emergence of Compute Express Link (CXL), a high-speed interconnect standard built on the PCIe physical layer, has made it possible to attach large pools of memory to servers without requiring physical DIMM slots on the host board. This disaggregated memory model introduces a new tier in the memory hierarchy — one that sits between traditional local DRAM and remote network-attached storage — and fundamentally changes the assumptions under which classical scheduling algorithms were designed.

Classical CPU scheduling algorithms such as First-Come-First-Served (FCFS) and Round Robin (RR) were developed for relatively homogeneous systems where all memory accesses could be assumed to carry similar latency penalties. FCFS assigns the CPU to processes in the strict order of their arrival, which is simple and fair in the absence of memory heterogeneity but introduces the well-known convoy effect: short-duration, memory-sensitive tasks are forced to queue behind long-running, memory-intensive processes that occupy DRAM, even when the short tasks would benefit far more from DRAM placement. Round Robin improves CPU fairness through time-sliced preemption, but does so without any awareness of where a task's memory is actually located. Neither algorithm accounts for the fact that two tasks executing simultaneously may experience radically different effective memory latencies depending on whether their working sets are placed in local DRAM or in CXL-attached memory.

The latency gap between these two tiers is not marginal. Local DRAM on a modern server typically delivers access latencies in the range of 80 to 120 nanoseconds. CXL-attached memory, by contrast, introduces serialisation overhead through the PCIe fabric, resulting in effective access latencies of 200 to 400 nanoseconds or more — a penalty of two to four times relative to DRAM. For workloads that perform frequent random memory accesses, such as in-memory databases, graph processing engines, or real-time analytics pipelines, this latency gap translates directly into degraded throughput and increased tail latency at the application level.

Even modern operating systems with NUMA-aware scheduling heuristics handle this poorly. Linux's CFS scheduler is designed to minimise task migration costs across CPU sockets within a single server, but it was not conceived with the notion of a memory tier whose latency is determined by a PCIe switch fabric rather than by DRAM bank and channel topology. When CXL memory is presented to the OS as a remote NUMA node, the scheduler may place a latency-critical task on a CXL-mapped memory region simply because the local DRAM node is near capacity, with no mechanism to weigh the sensitivity of the task against the cost of CXL placement.

This creates a combinatorial optimisation challenge. For a system with N tasks and two memory tiers, the total number of possible task-to-memory assignments is 2^N. As the number of tasks grows, evaluating all possible assignments becomes computationally intractable for classical heuristic schedulers. A system with 8 tasks has 256 possible assignments; a system with 32 tasks has over 4 billion. No greedy or round-robin heuristic can guarantee globally optimal placement under these conditions, because globally optimal placement requires reasoning simultaneously about all task sensitivities, memory capacity constraints, and inter-task interference — a problem structure that maps naturally to combinatorial optimisation.

This project addresses the gap by proposing a Quantum-Assisted Optimisation Engine that uses the Recursive Quantum Approximate Optimisation Algorithm (RQAOA) to compute near-optimal task-to-memory-tier assignments. By formulating the scheduling problem as a Quadratic Unconstrained Binary Optimisation (QUBO) problem and solving it using quantum-classical hybrid methods, the engine aims to produce placement decisions that account for task memory sensitivity, DRAM capacity constraints, and CXL latency penalties in a unified optimisation objective — something that classical schedulers with fixed heuristics cannot do in the general case.

---

## 3. Methodology

### 3.1 QUBO Formulation

The memory placement scheduling problem is modelled as a Quadratic Unconstrained Binary Optimisation (QUBO) problem. QUBO is a class of combinatorial optimisation problems expressible in the form:

```
minimise:  x^T Q x
```

where **x** is a binary vector of decision variables and **Q** is a real-valued square matrix encoding both the objective function and all constraints as penalty terms. The QUBO formulation is the natural input format for quantum annealing hardware and for gate-model quantum algorithms such as QAOA and its recursive variant, RQAOA.

#### Decision Variables

Each task i in the task set is assigned a binary variable x_i, where:

- **x_i = 0** indicates that task i is placed in local DRAM (Node 0, low latency)
- **x_i = 1** indicates that task i is placed in CXL-attached memory (Node 1, higher latency)

For a system with 8 tasks, the decision vector **x** has 8 binary components, yielding a 2^8 = 256-element solution space.

#### Objective: Minimise Total Memory Access Cost

The primary objective is to minimise the total weighted memory access cost across all tasks. Tasks placed in CXL incur a latency penalty proportional to their memory sensitivity and memory footprint. The diagonal terms of the QUBO matrix Q encode this objective:

```
Q[i][i] = sensitivity_i × (CXL_LATENCY - DRAM_LATENCY) × memory_mb_i
```

Where:
- `sensitivity_i` is a normalised score in [0.0, 1.0] representing how much task i's performance degrades under high-latency memory
- `CXL_LATENCY` is the effective CXL access latency (modelled at 300 ns)
- `DRAM_LATENCY` is the baseline DRAM access latency (modelled at 100 ns)
- `memory_mb_i` is the memory footprint of task i in megabytes

A task with high sensitivity and large memory footprint placed on CXL contributes a large positive value to the objective. Since we minimise, the solver is incentivised to place high-sensitivity tasks in DRAM wherever capacity allows.

#### Constraint: DRAM Capacity

Not all tasks can fit in DRAM simultaneously. The total memory assigned to DRAM-placed tasks must not exceed the available DRAM capacity C_DRAM. This constraint is encoded as a quadratic penalty added to the objective:

```
Penalty = P × (Σ_i (1 - x_i) × memory_mb_i  -  C_DRAM)²
```

Where P is a sufficiently large penalty coefficient that discourages DRAM overflow. Expanding this square produces off-diagonal terms Q[i][j] for all pairs of tasks (i ≠ j), which encode the pairwise interaction costs between tasks competing for DRAM space.

#### Combined QUBO Matrix

The full Q matrix is an 8×8 real-valued symmetric matrix. Diagonal entries encode individual task latency costs. Off-diagonal entries encode the capacity constraint coupling between task pairs. The QUBO solver (RQAOA) seeks a binary assignment x* that minimises x^T Q x, subject to no explicit constraints — the constraints are embedded directly into Q as penalty terms.

This QUBO matrix is implemented in `qubo/qubo_builder.py` via the `build_qubo_from_tasks()` function, which accepts the canonical 8-task list and returns an (8, 8) NumPy array. A heatmap visualisation of Q is saved to `results/qubo_heatmap.png` for inspection.

---

### 3.2 RQAOA Algorithm

*[To be written by P1 on Day 3 — covers RQAOA circuit structure, COBYLA optimiser, recursive cutoff strategy, and output decoding]*

---

### 3.3 CXL Memory Simulation

*[To be written by P3 on Day 6 — covers NUMA-based tiering, latency injection via time.sleep(), and bandwidth throttling implementation]*

---

### 3.4 Classical Schedulers

*[To be written by P3 on Day 6 — covers FCFS, Round Robin, Greedy (sensitivity-sorted), and Priority-Weighted Greedy with examples]*

---

### 3.5 Evaluation Metrics

*[To be written by P4 on Day 6 — covers avg latency, makespan, DRAM utilisation, and total weighted cost definitions]*

---

## 4. Results and Discussion

*[To be written on Day 6 after all experiments are run — includes comparison tables, plots, and IBM Quantum hardware results]*

---

## 5. Limitations

*[To be completed on Day 6 — covers QUBO problem size ceiling, offline scheduling only, approximate CXL modelling, and no global optimality guarantee]*

---

## 6. References

*[To be completed on Day 6 — IEEE-style references]*

1. Farhi, E., Goldstone, J., & Gutmann, S. (2014). A quantum approximate optimization algorithm. *arXiv preprint arXiv:1411.4028*.
2. Bravyi, S., Kliesch, A., Koenig, R., & Tang, E. (2020). Obstacles to variational quantum optimization from symmetry protection. *Physical Review Letters*, 125(26).
3. Bravyi, S., et al. (2022). Hybrid quantum-classical algorithms and quantum error mitigation. *Journal of the Physical Society of Japan*, 90(3).
4. OpenQAOA GitHub Repository. https://github.com/entropicalabs/openqaoa
5. PyQUBO GitHub Repository. https://github.com/recruit-communications/pyqubo
6. Qiskit GitHub Repository. https://github.com/Qiskit/qiskit
7. Quantum Job Scheduler Reference. https://github.com/aboev/quantum-job-scheduler
8. CXL Consortium. (2023). *CXL Specification Revision 3.0*. https://www.computeexpresslink.org
9. Linux `numactl` documentation. https://linux.die.net/man/8/numactl

---

