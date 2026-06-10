# Quantum-Assisted Optimization Engine for CXL-Aware Hybrid Scheduling

**Report Version:** 0.4 (Day 4 Draft)
**Authors:** Anjana, Hari, Smarth, Vikas, Devandra
**Institution:** BMS College of Engineering

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
6. [Limitations and Future Work](#6-limitations-and-future-work)
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

This project addresses the gap by proposing a Quantum-Assisted Optimisation Engine that uses the Recursive Quantum Approximate Optimisation Algorithm (RQAOA) to compute near-optimal task-to-memory-tier assignments. By formulating the scheduling problem as a Quadratic Unconstrained Binary Optimisation (QUBO) problem and solving it using quantum-classical hybrid methods, the engine aims to produce placement decisions that account for task memory sensitivity, DRAM capacity constraints, and CXL latency penalties in a unified optimisation objective.

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

For a system with 8 tasks, the decision vector x has 8 binary components, yielding a 2^8 = 256-element solution space.

#### Objective: Minimise Total Memory Access Cost

The diagonal terms of the QUBO matrix Q encode the per-task latency cost:

```
Q[i][i] = sensitivity_i × (CXL_LATENCY - DRAM_LATENCY) × memory_mb_i
```

Where sensitivity_i is a normalised score in [0.0, 1.0] representing how much task i's performance degrades under high-latency memory. The product of sensitivity, latency delta (200 ns), and memory footprint gives a per-task penalty for CXL placement.

#### Constraint: DRAM Capacity

Total memory assigned to DRAM-placed tasks must not exceed the available DRAM capacity C_DRAM. This constraint is encoded as a quadratic penalty using slack variables:

```
Penalty = P × (Σ_i (1 - x_i) × memory_mb_i  -  C_DRAM)²
```

The project uses a slack variable formulation where `n_slack = ceil(log2(C_DRAM))` additional binary variables encode the capacity constraint as an exact equality. For the default 2048 MB DRAM capacity this gives 11 slack bits, making the total QUBO size 8 + 11 = 19 variables.

The full Q matrix is implemented in `src/rqaoa/qubo_builder.py` via `build_qubo_from_tasks()`, which returns a (19, 19) NumPy array. A heatmap of the 8×8 task sub-matrix is saved to `results/qubo_heatmap.png`.

---

### 3.2 RQAOA Algorithm

The Recursive Quantum Approximate Optimisation Algorithm (RQAOA) serves as the quantum optimisation engine, implemented in `src/rqaoa/rqaoa_runner.py` and orchestrated through `src/rqaoa/run_rqaoa_pipeline.py`.

#### Why Standard QAOA Is Insufficient

Fixed-depth QAOA can only capture correlations within a bounded graph distance. For dense 8-task problems with all-to-all coupling in the QUBO matrix, standard QAOA gets trapped in local optima. RQAOA addresses this by iteratively extracting quantum correlation information to permanently reduce the problem size.

#### Algorithm Steps

1. **Encode:** Compiled into a parameterised quantum circuit using OpenQAOA with Qiskit Aer vectorised simulator. Circuit depth: `RQAOA_LAYERS = 3`.

2. **Optimise:** COBYLA optimiser iterates over variational parameters (gamma and beta angles) to minimise expected energy. Maximum 200 iterations per step, `SHOTS = 1024` measurements per evaluation.

3. **Identify Correlation:** Computes two-qubit expectation values to find the strongest correlated pair:
```
M_ij = <psi(gamma*, beta*) | Z_i Z_j | psi(gamma*, beta*)>
(i*, j*) = argmax_{i<j} |M_ij|
```

4. **Eliminate:** Most strongly correlated variable fixed and substituted out:
   - M_ij > 0 → same memory tier
   - M_ij < 0 → opposite memory tiers

5. **Recurse:** Repeat until remaining variables reach cutoff:

| Total Variables | Tasks | Slack Bits | Cutoff |
|----------------|-------|------------|--------|
| 19 | 8 | 11 | 8 |
| 23 | 12 | 11 | 10 |
| 27 | 16 | 12 | 12 |

6. **Solve Classically:** Remaining reduced problem solved by classical enumeration. Solution propagated back to reconstruct full assignment.

#### Output Decoding and Validation

Three validation checks after RQAOA:
- **Binary check:** All task variable values must be 0 or 1.
- **Capacity check:** Total DRAM usage ≤ 2048 MB (0.5 MB tolerance).
- **Constraint residual check:** `DRAM_used + slack_value` ≈ C_DRAM (10 MB tolerance).

Valid assignments saved to `results/rqaoa_assignment_8tasks.csv`.

#### Fallback Mechanism

If OpenQAOA is unavailable, system falls back to greedy assignment based on QUBO diagonal costs. Clearly logged as non-quantum.

---

### 3.3 Execution Layer — Task Orchestrator

Implemented in `src/executor/task_orchestrator.py` (P2 — Hari). Launches all 8 tasks as concurrent subprocesses using `subprocess.Popen`. Total wall time equals the slowest task's duration.

Each task bound to NUMA node via `numactl`:

| Tier | numactl command |
|------|----------------|
| DRAM | `numactl --cpunodebind=0 --membind=0` |
| CXL  | `numactl --cpunodebind=1 --membind=1` |

Falls back gracefully if `numactl` unavailable (Windows/macOS).

Each subprocess runs `task_runner.py`:
1. Allocates memory using `np.random.rand`
2. Iterates array in CHUNK_SIZE=1024 chunks
3. Injects CXL latency: `sleep = 2.0 × T_compute` → CXL total = 3× DRAM
4. Enforces MIN_COMPUTE_S=0.05s floor
5. Prints CSV: `task_id,node,start_time_s,end_time_s,duration_s`

---

### 3.4 NUMA-Based CXL Memory Simulation

Physical CXL hardware unavailable. AWS EC2 instance (`i-0aa88607ce0e5f4c9`, Ubuntu 26.04 LTS) has a single physical NUMA node.

#### Hardware Investigation

Attempt to enable `numa=fake=2` failed — AWS kernel compiled without `CONFIG_NUMA_EMU` flag. Kernel logged: `Malformed early option 'numa'`. Recompiling kernel was out of scope.

#### Software Latency Simulation

CXL latency simulated in `task_runner.py` using `time.sleep()`:

```
extra_sleep_s = compute_duration_s × (3.0 - 1.0) = compute_duration_s × 2.0
```

Total CXL time = 3× DRAM time, matching 300 ns / 100 ns = 3:1 ratio.

| Aspect | Real CXL Hardware | This Simulation |
|--------|------------------|-----------------|
| Latency ratio | 3× (hardware) | 3× (time.sleep) |
| numactl binding | Physical node separation | Syntactically correct, same bank |
| QUBO cost constants | Accurate | Accurate |
| Reproducibility | Hardware-dependent | Fully reproducible |

---

### 3.5 Classical Schedulers

Four classical schedulers in `src/scheduler/` (P3 — Smarth), all inheriting from `BaseScheduler` (P5 — Devandra):

**FCFS:** Assigns by task_id order. Fills DRAM first, overflows to CXL. Vulnerable to convoy effect.

**Round Robin:** Alternates DRAM/CXL by index parity. Ignores task sensitivity.

**Greedy:** Sorts by `memory_sensitivity` descending. Most-sensitive tasks get DRAM first. Best latency cost.

**Priority-Weighted Greedy:** Composite score = `0.5 × (priority/MAX_PRIORITY) + 0.5 × sensitivity`. Balances priority and sensitivity.

---

### 3.6 Evaluation Metrics

Implemented in `src/evaluation/metrics.py` (P4 — Vikas):

**Average Completion Time:** `mean(duration_s)` across all tasks.

**Makespan:** `max(end_time_s) - min(start_time_s)` across all tasks.

**Total Latency Cost:** `Σ_i (sensitivity_i × tier_latency_ns × memory_mb_i)` where DRAM=100 ns, CXL=300 ns.

**DRAM Utilisation:** `(dram_used_mb / dram_capacity_mb) × 100%`.

Results written to `results/execution_log.csv` and `results/all_schedulers_summary.csv`. Plots saved to `results/plots/`.

---

## 4. System Design

### 4.1 Architecture Overview

1. **Optimization Layer** — RQAOA computes near-optimal assignments via QUBO (19 variables).
2. **Scheduling Layer** — Interprets RQAOA output; 4 classical baselines for comparison.
3. **Execution Layer** — Enforces placement via `numactl` and collects timing metrics.

### 4.2 Execution Flow

```
Input Tasks (8) → QUBO Builder (19×19 matrix)
     → QUBO Converter (PyQUBO → OpenQAOA format)
     → RQAOA Optimizer (19 vars, cutoff=8, p=3, COBYLA)
     → Bitstring Decoder (task bits 0-7 extracted)
     → Validation (capacity + residual checks)
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

All five schedulers were executed against the canonical 8-task set on the project execution environment. Each scheduler ran the full pipeline: assignment computation, concurrent subprocess execution via `task_orchestrator.py`, software-injected CXL latency via `task_runner.py`, and metric collection. Results are logged to `results/execution_log.csv` and `results/all_schedulers_summary.csv`.

> **Note on RQAOA:** The OpenQAOA library was not available in the local Windows development environment during Day 4 benchmarking. The RQAOA row used the greedy fallback (all tasks assigned to CXL). The true quantum result will be obtained from the AWS EC2 instance on Day 5 and this section updated accordingly.

---

### 5.1 Scheduler Comparison — All Metrics

| Scheduler | DRAM | CXL | Avg Time (s) | Makespan (s) | DRAM Util % | Latency Cost (ns·MB) |
|-----------|------|-----|-------------|-------------|-------------|----------------------|
| FCFS | 4 | 4 | 1.8130 | 6.0590 | 93.8% | 592,000 |
| Round Robin | 2 | 6 | 1.3699 | 3.7446 | 75.0% | 638,080 |
| Greedy | 4 | 4 | 2.2937 | 10.1271 | **100.0%** | **553,600** |
| Priority-Weighted Greedy | 4 | 4 | 2.1696 | 7.5175 | **100.0%** | **553,600** |
| RQAOA (fallback) | 0 | 8 | 2.2310 | 9.0605 | 0.0% | 904,320 |

**Key finding: Greedy and Priority-Weighted Greedy achieved the lowest latency cost of 553,600 ns·MB** — 6.5% better than FCFS, 13.2% better than Round Robin, and 38.8% better than the RQAOA fallback.

---

### 5.2 Latency Cost Analysis

The latency cost metric measures total weighted memory access penalty:

```
latency_cost = Σ_i (sensitivity_i × tier_latency_ns × memory_mb_i)
```

Greedy and Priority-Weighted Greedy produced identical assignments, both achieving 553,600 ns·MB:

| Task | Tier | Memory (MB) | Sensitivity | Latency Cost |
|------|------|-------------|-------------|--------------|
| T4 | DRAM | 768 | 0.95 | 72,960 |
| T0 | DRAM | 512 | 0.90 | 46,080 |
| T6 | DRAM | 640 | 0.80 | 51,200 |
| T3 | DRAM | 128 | 0.40 | 5,120 |
| T2 | CXL | 1024 | 0.85 | 261,120 |
| T1 | CXL | 256 | 0.70 | 53,760 |
| T7 | CXL | 192 | 0.50 | 28,800 |
| T5 | CXL | 384 | 0.30 | 34,560 |

This assignment correctly places the four most sensitive tasks (T4, T0, T6, T3) in DRAM while sending the large but moderately-sensitive T2 to CXL — a sound decision given the 2048 MB DRAM capacity constraint.

FCFS (592,000 ns·MB) performed worse because it assigned by arrival order, placing high-sensitivity T4 (0.95) in CXL while filling DRAM with T0–T3 regardless of sensitivity.

Round Robin (638,080 ns·MB) placed 6 tasks in CXL including several high-sensitivity ones, achieving only 75% DRAM utilisation.

---

### 5.3 Execution Time Analysis

Individual task execution times from the benchmark run confirm the 3× CXL latency simulation is working correctly. From the Greedy scheduler run:

| Task | Tier | Memory (MB) | Duration (s) | CXL Ratio |
|------|------|-------------|-------------|-----------|
| T4 | DRAM | 768 | 1.7200 | 1.0× (baseline) |
| T0 | DRAM | 512 | 0.8822 | 1.0× (baseline) |
| T6 | DRAM | 640 | 1.7352 | 1.0× (baseline) |
| T3 | DRAM | 128 | 0.3381 | 1.0× (baseline) |
| T2 | CXL | 1024 | 8.3029 | ~3.0× ✅ |
| T1 | CXL | 256 | 1.9151 | ~3.0× ✅ |
| T7 | CXL | 192 | 1.5481 | ~3.0× ✅ |
| T5 | CXL | 384 | 1.9077 | ~3.0× ✅ |

CXL tasks consistently ran approximately 3× longer than comparable DRAM tasks, confirming the software latency injection is working correctly.

Round Robin achieved the fastest makespan (3.74 s) because it placed only 2 tasks in DRAM — but this comes at the cost of 638,080 ns·MB latency cost, the worst among classical schedulers. Under real CXL hardware conditions, Round Robin's execution time would increase significantly.

---

### 5.4 DRAM Utilisation

Greedy and Priority-Weighted Greedy both achieved 100% DRAM utilisation (2048/2048 MB), meaning every available megabyte of fast memory was used. This is optimal.

FCFS achieved 93.8% (1920/2048 MB) — Tasks 0–3 filled 1920 MB, leaving 128 MB unused despite Task 4 (768 MB, sensitivity 0.95) being available to fill it.

Round Robin achieved only 75% (1536/2048 MB) — the alternating pattern left 512 MB of DRAM unused.

---

### 5.5 RQAOA Results — Day 5 Update

*(To be updated on Day 5 after AWS EC2 quantum run)*

The local Windows run used a greedy fallback (all 8 tasks assigned to CXL, latency cost 904,320 ns·MB) due to missing OpenQAOA installation. This is expected behaviour — the fallback is clearly logged. On Day 5 the true RQAOA result from the AWS EC2 instance will be inserted here. Expected findings:
- RQAOA should produce an assignment close to or equal to the Greedy baseline (553,600 ns·MB)
- IBM QPU result will be compared against Qiskit Aer simulation result
- Noise effects from IBM hardware will be quantified and documented

---

### 5.6 Summary

The benchmarking results demonstrate that sensitivity-aware scheduling (Greedy and Priority-Weighted Greedy) consistently outperforms both arrival-order (FCFS) and distribution-based (Round Robin) strategies on the latency cost metric. The 13.2% improvement over Round Robin and 6.5% improvement over FCFS validate the core hypothesis: explicitly accounting for task memory sensitivity in scheduling decisions produces measurably better memory placement outcomes. The RQAOA results pending from Day 5 will determine whether quantum-assisted optimisation can match or exceed the Greedy baseline.

---

## 6. Limitations and Future Work

### 6.1 Problem Size Ceiling

The current implementation supports a maximum of 16 tasks (27 QUBO variables including slack bits). This limit is imposed by the qubit count and coherence time constraints of current NISQ hardware. The IBM Quantum devices used in this project have 127 qubits, but effective circuit depth for RQAOA is limited by gate error rates. Scaling to real production workloads with hundreds or thousands of tasks would require fault-tolerant quantum hardware or a hybrid decomposition strategy that breaks the problem into overlapping sub-problems.

### 6.2 Offline Scheduling Only

All placement decisions are made before execution begins and do not change during execution. This offline model suits batch workloads with known characteristics but cannot respond to runtime events such as actual memory footprints exceeding estimates, DRAM pressure from competing processes, or dynamic workload changes. A production CXL-aware scheduler would need integration with the OS memory manager for online reassignment.

### 6.3 Approximate CXL Modelling

The `time.sleep()` latency simulation captures the 3:1 latency ratio but does not model PCIe fabric contention under concurrent access, bandwidth limitations of the CXL link (32–64 GB/s vs DRAM's 50–100 GB/s per channel), cache coherence protocol overhead, or NUMA distance effects on CPU prefetching. The simulation is sufficient for validating scheduling algorithm decision quality but would need real hardware measurements for production validation.

### 6.4 No Optimality Guarantee

RQAOA is a heuristic — it produces near-optimal solutions but cannot guarantee global optimality. The COBYLA optimiser may converge to local minima, particularly for dense QUBO problems with many similarly-scored tasks. The recursive cutoff introduces a classical approximation at the final stage. For the 8-task problem studied here, brute-force enumeration (256 assignments) could find the true optimum — RQAOA's advantage would become more significant at larger problem sizes.

### 6.5 Hardware Noise

IBM Quantum hardware results are affected by gate errors (~0.1–1% per two-qubit gate), readout errors (~1–5% per qubit), and decoherence during circuit execution. This project does not apply error mitigation techniques (zero-noise extrapolation, probabilistic error cancellation, or measurement error mitigation). The comparison between Qiskit Aer simulation and IBM QPU results in Section 5.5 will quantify the practical impact of hardware noise.

### 6.6 Single-Node Execution Environment

The AWS EC2 instance has a single physical NUMA node. `numactl` commands are syntactically correct but both Node 0 and Node 1 map to the same physical memory. The CXL latency difference is produced entirely by software injection. On Windows, `numactl` is unavailable and all tasks run without NUMA binding.

### 6.7 Future Work

- **Real CXL hardware validation** — run on a server with physical CXL-attached memory to validate simulation assumptions against hardware measurements.
- **Larger problem sizes** — extend QUBO formulation to 32–64 tasks using problem decomposition or hybrid methods.
- **Online dynamic scheduling** — integrate RQAOA as an advisory layer to the Linux memory manager, triggering re-optimisation when DRAM pressure exceeds a threshold.
- **Error mitigation** — apply zero-noise extrapolation or measurement error mitigation to improve IBM QPU result quality.
- **Multi-tier memory** — extend the binary DRAM/CXL model to three or more tiers using a higher-order QUBO formulation.

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

*Report Version 0.4 — Day 4 Draft*
*Maintained by: Devandra (P5 — Documentation & Integration Lead)*
*Section 5 (Results) added Day 4 with real benchmark data from run_benchmarks.py.*
*Section 6 (Limitations and Future Work) completed Day 4.*
*RQAOA quantum results pending Day 5 AWS EC2 run.*