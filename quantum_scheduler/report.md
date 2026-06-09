# Quantum-Assisted Optimization Engine for CXL-Aware Hybrid Scheduling

**Report Version:** 0.3 (Day 3 Draft)
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

*To be written on Day 6 after all experimental results are collected. The abstract will summarise the problem, the RQAOA-based approach, key findings from classical vs. quantum scheduler comparison, and the significance of CXL-aware placement.*

---

## 2. Problem Statement

Modern computing systems are undergoing a fundamental architectural shift. The emergence of Compute Express Link (CXL), a high-speed interconnect standard built on the PCIe physical layer, has made it possible to attach large pools of memory to servers without requiring physical DIMM slots on the host board. This disaggregated memory model introduces a new tier in the memory hierarchy — one that sits between traditional local DRAM and remote network-attached storage — and fundamentally changes the assumptions under which classical scheduling algorithms were designed.

Classical CPU scheduling algorithms such as First-Come-First-Served (FCFS) and Round Robin (RR) were developed for relatively homogeneous systems where all memory accesses could be assumed to carry similar latency penalties. FCFS assigns the CPU to processes in strict arrival order, which introduces the well-known convoy effect: short-duration, memory-sensitive tasks are forced to queue behind long-running processes that occupy DRAM, even when the short tasks would benefit far more from DRAM placement. Round Robin improves CPU fairness through time-sliced preemption, but does so without any awareness of where a task's memory is actually located. Neither algorithm accounts for the fact that two tasks executing simultaneously may experience radically different effective memory latencies depending on whether their working sets are placed in local DRAM or in CXL-attached memory.

The latency gap between these two tiers is not marginal. Local DRAM on a modern server typically delivers access latencies in the range of 80 to 120 nanoseconds. CXL-attached memory introduces serialisation overhead through the PCIe fabric, resulting in effective access latencies of 200 to 400 nanoseconds or more — a penalty of two to four times relative to DRAM. For workloads that perform frequent random memory accesses, such as in-memory databases, graph processing engines, or real-time analytics pipelines, this latency gap translates directly into degraded throughput and increased tail latency at the application level.

Even modern operating systems with NUMA-aware scheduling heuristics handle this poorly. Linux's CFS scheduler was not conceived with the notion of a memory tier whose latency is determined by a PCIe switch fabric rather than by DRAM bank and channel topology. When CXL memory is presented to the OS as a remote NUMA node, the scheduler may place a latency-critical task on a CXL-mapped memory region simply because the local DRAM node is near capacity, with no mechanism to weigh the sensitivity of the task against the cost of CXL placement.

This creates a combinatorial optimisation challenge. For a system with N tasks and two memory tiers, the total number of possible task-to-memory assignments is 2^N. A system with 8 tasks has 256 possible assignments; a system with 32 tasks has over 4 billion. No greedy or round-robin heuristic can guarantee globally optimal placement under these conditions, because globally optimal placement requires reasoning simultaneously about all task sensitivities, memory capacity constraints, and inter-task interference — a problem structure that maps naturally to combinatorial optimisation.

This project addresses the gap by proposing a Quantum-Assisted Optimisation Engine that uses the Recursive Quantum Approximate Optimisation Algorithm (RQAOA) to compute near-optimal task-to-memory-tier assignments. By formulating the scheduling problem as a Quadratic Unconstrained Binary Optimisation (QUBO) problem and solving it using quantum-classical hybrid methods, the engine aims to produce placement decisions that account for task memory sensitivity, DRAM capacity constraints, and CXL latency penalties in a unified optimisation objective — something that classical schedulers with fixed heuristics cannot do in the general case.

---

## 3. Methodology

### 3.1 QUBO Formulation

The memory placement scheduling problem is modelled as a Quadratic Unconstrained Binary Optimisation (QUBO) problem expressible in the form:

```
minimise:  x^T Q x
```

where **x** is a binary vector of decision variables and **Q** is a real-valued square matrix encoding both the objective function and all constraints as penalty terms. The QUBO formulation is the natural input format for quantum annealing hardware and for gate-model quantum algorithms such as QAOA and its recursive variant RQAOA.

#### Decision Variables

Each task i is assigned a binary variable x_i:

- **x_i = 0** — task i placed in local DRAM (Node 0, ~100 ns latency)
- **x_i = 1** — task i placed in CXL-attached memory (Node 1, ~300 ns latency)

For a system with 8 tasks, the decision vector x has 8 binary components, yielding a 2^8 = 256-element solution space.

#### Objective: Minimise Total Memory Access Cost

The diagonal terms of the QUBO matrix Q encode the per-task latency cost:

```
Q[i][i] = sensitivity_i × (CXL_LATENCY - DRAM_LATENCY) × memory_mb_i
```

Where sensitivity_i is a normalised score in [0.0, 1.0] representing how much task i's performance degrades under high-latency memory. A task with sensitivity = 1.0 is maximally latency-sensitive; a task with sensitivity = 0.0 is largely memory-insensitive. The product of sensitivity, latency delta (200 ns), and memory footprint gives a per-task penalty for CXL placement.

#### Constraint: DRAM Capacity

Total memory assigned to DRAM-placed tasks must not exceed the available DRAM capacity C_DRAM. This constraint is encoded as a quadratic penalty using slack variables:

```
Penalty = P × (Σ_i (1 - x_i) × memory_mb_i  -  C_DRAM)²
```

Expanding this produces off-diagonal terms Q[i][j] encoding pairwise capacity constraint coupling between tasks competing for DRAM space. The project uses a slack variable formulation where `n_slack = ceil(log2(C_DRAM))` additional binary variables are introduced to encode the capacity constraint as an exact equality. For the default 2048 MB DRAM capacity this gives 11 slack bits, making the total QUBO size 8 + 11 = 19 variables.

The full Q matrix is implemented in `src/rqaoa/qubo_builder.py` via `build_qubo_from_tasks()`, which accepts the canonical 8-task list and returns a (19, 19) NumPy array. A heatmap visualisation of the 8×8 task sub-matrix is saved to `results/qubo_heatmap.png`.

---

### 3.2 RQAOA Algorithm

The Recursive Quantum Approximate Optimisation Algorithm (RQAOA) serves as the quantum optimisation engine of this project. It is implemented in `src/rqaoa/rqaoa_runner.py` and orchestrated through the full pipeline in `src/rqaoa/run_rqaoa_pipeline.py`. The algorithm operates on the QUBO matrix produced by `qubo_builder.py` and returns a binary assignment of tasks to memory tiers.

#### Why Standard QAOA Is Insufficient

Fixed-depth QAOA can only capture correlations within a bounded graph distance. For dense 8-task problems with all-to-all coupling in the QUBO matrix, standard QAOA with a small number of layers gets trapped in local optima because it cannot reason about the full combinatorial structure. RQAOA addresses this by iteratively extracting genuine quantum correlation information at each step and using it to permanently reduce the problem size.

#### Algorithm Steps

RQAOA proceeds as follows:

1. **Encode:** The QUBO problem is compiled into a parameterised quantum circuit (QAOA ansatz) using the OpenQAOA library with a Qiskit Aer vectorised simulator as the backend. The circuit depth is controlled by `RQAOA_LAYERS = 3` (defined in `src/rqaoa/rqaoa_config.py`), meaning three alternating layers of cost and mixer unitaries are applied.

2. **Optimise:** A classical COBYLA optimiser iterates over the circuit's variational parameters (gamma and beta angles) to minimise the expected energy of the cost Hamiltonian. A maximum of 200 COBYLA iterations are allowed per recursion step. The backend uses `SHOTS = 1024` measurement samples per circuit evaluation to estimate expectation values.

3. **Identify Correlation:** After each optimisation, the algorithm computes two-qubit expectation values to identify the pair of variables with the strongest quantum correlation:

```
M_ij = <psi(gamma*, beta*) | Z_i Z_j | psi(gamma*, beta*)>
(i*, j*) = argmax_{i<j} |M_ij|
```

4. **Eliminate:** The most strongly correlated variable is fixed relative to its partner and substituted out of the Hamiltonian, reducing the problem by one variable:
   - M_ij > 0 → fix s_i = s_j (same memory tier)
   - M_ij < 0 → fix s_i = -s_j (opposite memory tiers)

5. **Recurse:** Steps 1–4 are repeated on the reduced problem until the number of remaining variables falls to the cutoff threshold. The cutoff is tuned by problem size:

| Total Variables | Tasks | Slack Bits | Cutoff |
|----------------|-------|------------|--------|
| 19 | 8 | 11 | 8 |
| 23 | 12 | 11 | 10 |
| 27 | 16 | 12 | 12 |

6. **Solve Classically:** Once the problem reaches the cutoff size, the remaining reduced problem is solved exactly using classical enumeration. The solution is propagated back through the chain of eliminated variable relationships to reconstruct the full assignment.

#### Output Decoding and Validation

The raw RQAOA output is a dictionary mapping variable index to binary value. The pipeline (`run_rqaoa_pipeline.py`) extracts the task assignment from the first `n_tasks` indices and performs three validation checks:

- **Binary check:** All task variable values must be 0 or 1.
- **Capacity check:** Total DRAM usage must not exceed C_DRAM (2048 MB, with 0.5 MB rounding tolerance).
- **Constraint residual check:** `DRAM_used + slack_value` must approximately equal C_DRAM (within 10 MB tolerance).

If validation passes, the integer assignment is decoded to a human-readable memory map (`{task_id: "DRAM" or "CXL"}`) and saved to `results/rqaoa_assignment_8tasks.csv`.

#### Fallback Mechanism

If OpenQAOA is unavailable or RQAOA fails, the system falls back to a greedy assignment based on diagonal QUBO costs. This fallback is clearly logged as non-quantum and is intended only for development environments.

---

### 3.3 Execution Layer — Task Orchestrator

The execution layer is implemented in `src/executor/task_orchestrator.py` (maintained by P2 — Hari). It receives the scheduler's assignment dict and launches all 8 tasks as concurrent subprocesses using Python's `subprocess.Popen`.

**Concurrency model:** All 8 tasks start at roughly the same wall-clock time using non-blocking Popen. Total wall time equals the slowest task's duration, not the sum of all tasks.

Each task is bound to its assigned NUMA node using `numactl`:

| Tier | numactl command |
|------|----------------|
| DRAM | `numactl --cpunodebind=0 --membind=0` |
| CXL  | `numactl --cpunodebind=1 --membind=1` |

If `numactl` is unavailable (e.g. on Windows), the orchestrator automatically falls back to running without NUMA binding.

Each subprocess runs `task_runner.py`, which:
1. Allocates the requested memory using NumPy (`np.random.rand`) — forces physical page commitment
2. Simulates memory-bound work by iterating over the array in CHUNK_SIZE=1024 chunks
3. Injects CXL latency: `sleep = (3.0 - 1.0) × T_compute` so CXL total = 3× DRAM (matching 300 ns / 100 ns ratio)
4. Enforces MIN_COMPUTE_S=0.05s floor for small arrays
5. Prints CSV result to stdout: `task_id,node,start_time_s,end_time_s,duration_s`

**QUBO Format Converter:** `src/rqaoa/qubo_converter.py` translates PyQUBO string keys (`'x[0]'`) to OpenQAOA integer keys (`(0,0)`) required by the quantum circuit runner. Normalises to upper-triangular form and merges duplicate entries by summing coefficients.

**Typical call chain:**
```
scheduler.schedule(tasks)           → assignment dict
task_orchestrator.run_all_tasks()   → list of result dicts
evaluation.metrics.*                → computed metrics
```

---

### 3.4 NUMA-Based CXL Memory Simulation

Physical CXL hardware was not available for this project. The execution environment is an AWS EC2 instance running Ubuntu 26.04 LTS with a single physical memory node. This section describes the investigation conducted and the software simulation strategy adopted in its place.

#### Hardware NUMA Emulation Investigation

The Linux kernel supports a `numa=fake=N` boot parameter that emulates multiple NUMA nodes on a single-node system. An attempt was made to enable `numa=fake=2` on the EC2 instance by modifying the GRUB configuration. After adding the parameter to `/etc/default/grub.d/50-cloudimg-settings.cfg`, running `sudo update-grub`, and rebooting, the kernel logged:

```
[    0.000000] Malformed early option 'numa'
```

The root cause was identified: both the AWS kernel (`7.0.0-1004-aws`) and the generic Ubuntu kernel on Ubuntu 26.04 LTS were compiled without the `CONFIG_NUMA_EMU` kernel flag. This compile-time flag is a prerequisite for the `numa=fake` parameter. Recompiling the kernel from source was considered out of scope for this project.

#### Software Latency Simulation Strategy

CXL-like latency behaviour is simulated entirely in software within `task_runner.py`. The simulation is based on the measured CXL-to-DRAM latency ratio of 3:1 (300 ns CXL vs. 100 ns DRAM), consistent with the constants defined in `src/scheduler/tasks.py` and used in the QUBO cost matrix.

Each task first performs actual memory-bound computation and precisely times it using `time.perf_counter()`. For CXL tasks (node=1), an additional sleep is injected:

```
extra_sleep_s = compute_duration_s × (MEMORY_LATENCY_RATIO - 1.0)
             = compute_duration_s × 2.0
```

This ensures the total CXL task time equals exactly `compute_duration_s × 3.0`, matching the 3:1 latency ratio regardless of array size or machine speed. DRAM tasks (node=0) receive no extra sleep.

#### Why This Simulation Is Valid

| Aspect | Real CXL Hardware | This Simulation |
|--------|------------------|-----------------|
| Latency ratio | 3× (hardware) | 3× (time.sleep) |
| numactl binding | Physical node separation | Syntactically correct, same bank |
| QUBO cost constants | Accurate | Accurate (same constants) |
| Reproducibility | Hardware-dependent | Fully reproducible |
| Evaluation metric | Completion time | Completion time |

The `numactl` binding commands are still issued by the executor to maintain architectural correctness — both nodes currently map to the same physical memory bank, but the code structure is identical to how it would execute on real CXL hardware.

---

### 3.5 Classical Schedulers

Four classical schedulers are implemented in `src/scheduler/` as baselines (maintained by P3 — Smarth). All inherit from `BaseScheduler` in `src/scheduler/scheduler_interface.py` (maintained by P5 — Devandra):

#### FCFS — First-Come-First-Served (`fcfs_scheduler.py`)
Assigns tasks in arrival order (task_id order). Fills DRAM first until capacity is exceeded, then overflows remaining tasks to CXL. Introduces the convoy effect: low-sensitivity tasks arriving early consume DRAM that high-sensitivity tasks arriving later need.

#### Round Robin (`round_robin_scheduler.py`)
Alternates between DRAM and CXL by task index parity. Even-indexed tasks try DRAM first; odd-indexed tasks try CXL first. Falls back to the other tier if the preferred tier is full. Does not consider task sensitivity — high-sensitivity tasks may end up in CXL simply due to their index.

#### Greedy (`greedy_scheduler.py`)
Sorts tasks by `memory_sensitivity` descending. Assigns most-sensitive tasks to DRAM first. This heuristic directly minimises the latency cost objective and consistently outperforms FCFS and Round Robin.

#### Priority-Weighted Greedy (`greedy_priority_scheduler.py`)
Sorts tasks by a composite score combining both priority and sensitivity:

```
score = 0.5 × (priority / MAX_PRIORITY) + 0.5 × memory_sensitivity
```

Ensures high-priority but moderately sensitive tasks still receive DRAM placement, which is important for latency-critical production workloads.

#### Performance Comparison (8-Task Set)

| Scheduler | Total Cost | DRAM Tasks | CXL Tasks | DRAM Used |
|-----------|------------|------------|-----------|-----------|
| Greedy | 252,160 | 4 | 4 | 2048 MB (100%) |
| FCFS | 290,560 | 4 | 4 | 1920 MB (94%) |
| Round Robin | 336,640 | 2 | 6 | 1536 MB (75%) |

Key finding: Greedy scheduler achieves 13% lower cost than FCFS and 25% lower cost than Round Robin. RQAOA results will be compared against these baselines in Section 5.

---

### 3.6 Evaluation Metrics

The evaluation module (`src/evaluation/metrics.py`, maintained by P4 — Vikas) defines four primary metrics:

**1. Average Completion Time**
```
avg_completion_time = mean(duration_s) across all tasks
```

**2. Makespan**
```
makespan = max(end_time_s) - min(start_time_s) across all tasks
```

**3. Total Latency Cost**
```
latency_cost_i = memory_sensitivity_i × tier_latency_ns × memory_mb_i
total_latency_cost = sum(latency_cost_i) for all tasks
```
Where tier_latency_ns = 100 for DRAM, 300 for CXL.

**4. DRAM Utilisation**
```
dram_utilization = (dram_used_mb / dram_capacity_mb) × 100%
```

Results are written to two CSV files:
- `results/execution_log.csv` — one row per task execution
- `results/all_schedulers_summary.csv` — one row per scheduler with all 4 metrics

Plots are generated by `src/evaluation/graphs.py` and saved to `results/plots/`.

---

## 4. System Design

### 4.1 Architecture Overview

The system comprises three layers:

1. **Optimization Layer** — RQAOA computes near-optimal task-to-tier assignments via QUBO (19 variables: 8 task bits + 11 slack bits).
2. **Scheduling Layer** — Interprets RQAOA bitstring output; implements 4 classical baselines for comparison.
3. **Execution Layer** — Enforces placement via `numactl` subprocess binding and collects timing metrics.

### 4.2 Execution Flow

```
Input Tasks (8) → QUBO Builder (19×19 matrix)
     → QUBO Converter (PyQUBO → OpenQAOA format)
     → RQAOA Optimizer (19 vars, cutoff=8, p=3, COBYLA)
     → Bitstring Decoder (task bits 0-7 extracted)
     → Validation (capacity check + residual check)
     → Scheduler Interpreter ({task_id: "DRAM"/"CXL"})
     → Task Orchestrator (8 concurrent subprocesses)
     → task_runner.py × 8 (numactl bound, latency injected)
     → Metric Collector (execution_log.csv)
     → Plot Generator (results/plots/)
     → Report
```

### 4.3 Component Table

| Component | Strategy | Technology | Owner |
|-----------|----------|------------|-------|
| Task Model | 8 tasks, 2 memory tiers | Python dataclass | P3 |
| QUBO Builder | Slack variable formulation | NumPy | P1 |
| QUBO Converter | PyQUBO → OpenQAOA format | Python | P2 |
| RQAOA Engine | p=3, COBYLA, cutoff=8 | OpenQAOA + Qiskit Aer | P1 |
| Result Parser | Bitstring → tier map | Python | P2 |
| Classical Schedulers | FCFS, RR, Greedy, Priority | Python | P3 |
| BaseScheduler Interface | Abstract base class | Python ABC | P5 |
| Task Orchestrator | 8 concurrent subprocesses | subprocess.Popen | P2 |
| Task Runner | Memory alloc + latency inject | NumPy + time.sleep | P2 |
| Metrics | Latency cost, makespan, util | Python | P4 |
| Plots | Bar charts × 3 | matplotlib | P4 |
| Report | Full documentation | Markdown | P5 |

---

## 5. Results and Discussion

*To be written on Day 6 after all experiments are run.*

### 5.1 Classical Scheduler Comparison
*(Insert `results/all_schedulers_summary.csv` table here.)*

### 5.2 RQAOA vs Classical — Task Placement
*(Insert QUBO heatmap and bitstring comparison plots.)*

### 5.3 RQAOA Simulated vs IBM Quantum Hardware
*(Insert comparison of Qiskit Aer simulation result vs IBM QPU result.)*

### 5.4 Memory Tier Impact on Execution Time
*(Insert latency vs tier plots from `results/plots/`.)*

---

## 6. Limitations

- **Problem size:** Limited to 8 tasks (19 QUBO variables) due to current quantum hardware qubit constraints.
- **Offline scheduling only:** No real-time or dynamic rescheduling. All decisions are made before execution begins.
- **Approximate CXL modelling:** Latency injection via `time.sleep()` approximates hardware CXL behaviour. Physical CXL protocol behaviour, cache coherence, and low-level interconnect effects are not modelled.
- **No optimality guarantee:** RQAOA provides near-optimal, not globally optimal, solutions. The classical COBYLA optimiser may converge to local minima in the variational landscape.
- **Hardware noise:** IBM Quantum hardware results are subject to gate errors, decoherence, and readout noise. Error mitigation is not applied in this project.
- **Single-node execution:** The AWS EC2 instance has a single physical NUMA node. Hardware NUMA emulation (`numa=fake=2`) was unavailable due to kernel compilation constraints.

---

## 7. References

1. Farhi, E., Goldstone, J., & Gutmann, S. (2014). A Quantum Approximate Optimization Algorithm. arXiv:1411.4028.
2. Bravyi, S., et al. (2020). Obstacles to Variational Quantum Optimization from Symmetry Protection. Physical Review Letters, 125(26).
3. Bravyi, S., et al. (2022). Hybrid quantum-classical algorithms and quantum error mitigation. Journal of the Physical Society of Japan, 90(3).
4. OpenQAOA GitHub Repository. https://github.com/entropicalabs/openqaoa
5. PyQUBO GitHub Repository. https://github.com/recruit-communications/pyqubo
6. Qiskit GitHub Repository. https://github.com/Qiskit/qiskit
7. Quantum Job Scheduler Reference. https://github.com/aboev/quantum-job-scheduler
8. CXL Consortium. (2023). CXL Specification Revision 3.0. https://www.computeexpresslink.org
9. Linux numactl documentation. https://linux.die.net/man/8/numactl
10. OpenQAOA Documentation. https://openqaoa.entropicalabs.com

---

*Report Version 0.3 — Day 3 Draft*
*Maintained by: Devandra (P5 — Documentation & Integration Lead)*
*Sections 3.2 and 3.4 added Day 3 based on P1 (Anjana) and P2 (Hari) implementations.*
*All section owners listed inline. Merge conflicts resolved by P5.*