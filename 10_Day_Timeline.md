# 🚀 10-Day Aggressive Project Timeline
## Quantum-Assisted Optimization Engine for CXL-Aware Hybrid Scheduling

> **Start Date:** Day 1 | **End Date:** Day 10  
> **Goal:** Complete a working, evaluated, and documented system by end of Day 10.  
> **Motto:** Build fast. Verify daily. Don't over-engineer.

---

## 📚 What You Need to Learn (Before or During the Project)

### Core Topics

| Topic | What to Study | Where |
|---|---|---|
| QUBO / Ising Model | What is QUBO, how to encode optimization problems | Search: *"QUBO formulation tutorial"* on YouTube |
| QAOA Basics | Circuit structure, cost Hamiltonian, mixer | Search: *"QAOA explained simply"* – Qiskit YouTube channel |
| RQAOA | How it reduces problem size recursively | OpenQAOA docs + their GitHub README |
| Qiskit Basics | Circuits, Aer simulator, running jobs | Qiskit's official YouTube playlist: *"Qiskit Tutorials"* |
| NUMA Architecture | What NUMA nodes are, numactl commands | Search: *"Linux NUMA memory explained"* |
| PyQUBO | How to define QUBO problems in Python | PyQUBO GitHub README (30 min read) |
| NetworkX | Graph modeling for task representation | Search: *"NetworkX Python tutorial"* |
| OpenQAOA | RQAOA API usage | OpenQAOA GitHub + Jupyter notebooks in their repo |

### Suggested YouTube Videos (Watch in Order)
1. **"Quantum Computing for Computer Scientists"** – Microsoft Research (1hr overview, great foundation)
2. **"QAOA - Quantum Approximate Optimization Algorithm"** – Qiskit YouTube
3. **"QUBO Problems and Quantum Annealing"** – Search on YouTube (any 20-min explainer)
4. **"Qiskit Aer Simulator Tutorial"** – Qiskit YouTube channel
5. **"Linux NUMA and Memory Topology"** – Search: *"numactl tutorial Linux"*

> ⚡ You do NOT need to master all of this before starting. Learn as you build each day.

---

## 📅 Day-by-Day Timeline

---

### ✅ DAY 1 — Environment Setup + Project Scaffold
**Theme:** Get everything installed and working before writing any algorithm code.

#### Tasks
- [ ] Set up Python virtual environment (`python3 -m venv qenv`)
- [ ] Install all dependencies:
  ```
  pip install qiskit qiskit-aer openqaoa pyqubo networkx numpy matplotlib psutil
  ```
- [ ] Verify IBM Quantum account (sign up at quantum.ibm.com, save API token)
- [ ] Create project folder structure:
  ```
  quantum_scheduler/
  ├── qubo/
  ├── rqaoa/
  ├── scheduler/
  ├── executor/
  ├── evaluation/
  ├── results/
  └── main.py
  ```
- [ ] Write a simple Qiskit "Hello World" circuit and run it on Aer simulator
- [ ] Confirm `numactl --hardware` works on your Linux machine (or set up VM)

#### Verification ✔️
- All imports work without errors
- Hello World Qiskit circuit runs and outputs a histogram
- `numactl --hardware` shows at least 2 NUMA nodes (or VM is configured)

---

### ✅ DAY 2 — Task Graph Modeling + QUBO Formulation
**Theme:** Define the problem mathematically before touching quantum code.

#### Tasks
- [ ] Define 8 tasks with attributes: `task_id`, `memory_requirement (MB)`, `priority`, `memory_sensitivity`
- [ ] Model tasks using NetworkX as a weighted graph (edges = task dependencies or conflicts)
- [ ] Define 2 memory tiers:
  - Node 0 (DRAM): capacity = 4096 MB, latency = 100 ns
  - Node 1 (CXL): capacity = 8192 MB, latency = 300 ns
- [ ] Formulate QUBO matrix using PyQUBO:
  - Binary variable: `x[i]` = 0 (DRAM) or 1 (CXL) for task i
  - Objective: minimize total latency cost
  - Constraint: don't exceed DRAM capacity
- [ ] Print and visualize the QUBO matrix as a heatmap

#### Verification ✔️
- QUBO matrix is an 8×8 (or N×N) symmetric matrix
- PyQUBO compiles without errors
- Heatmap saved to `results/qubo_heatmap.png`
- Manually verify one row of the QUBO makes logical sense

---

### ✅ DAY 3 — Classical Baseline Schedulers
**Theme:** Build the comparison baselines before introducing quantum.

#### Tasks
- [ ] Implement **FCFS Scheduler**: assign tasks to memory in arrival order until DRAM is full, rest goes to CXL
- [ ] Implement **Round Robin Scheduler**: alternate task assignment between DRAM and CXL
- [ ] Implement **Greedy Scheduler**: assign most memory-sensitive tasks to DRAM first
- [ ] For each scheduler, compute:
  - Total weighted latency cost
  - Number of tasks in DRAM vs CXL
  - Simulated completion time
- [ ] Store results in a structured dictionary / CSV

#### Verification ✔️
- All 3 schedulers run and produce valid assignments (all 8 tasks assigned)
- No scheduler exceeds DRAM capacity
- Results saved to `results/classical_baselines.csv`

---

### ✅ DAY 4 — RQAOA Integration (Simulated)
**Theme:** Hook up RQAOA to solve the QUBO problem classically simulated.

#### Tasks
- [ ] Convert PyQUBO output to OpenQAOA-compatible QUBO format
- [ ] Configure RQAOA using OpenQAOA:
  - Optimizer: COBYLA or NELDER-MEAD
  - Backend: Qiskit Aer (shot-based simulation)
  - Layers (p): start with p=1
  - Recursive cutoff: 3–4 variables
- [ ] Run RQAOA on your 8-task QUBO
- [ ] Extract the result bitstring (e.g., `01101001`)
- [ ] Decode bitstring → task-to-memory mapping

#### Verification ✔️
- RQAOA runs without crashing
- Output bitstring has exactly 8 bits (one per task)
- Decoded assignment is a valid mapping (all tasks assigned)
- Compare RQAOA cost vs classical baselines — log the numbers

---

### ✅ DAY 5 — Scheduling Layer + Execution Layer
**Theme:** Take the optimizer's output and actually enforce it.

#### Tasks
- [ ] Build `Scheduler` class:
  - Input: bitstring from RQAOA
  - Output: `{task_id: "DRAM" | "CXL"}` dictionary
- [ ] Build `Executor` class:
  - Constructs `numactl` command per task
  - DRAM task: `numactl --membind=0 python task_runner.py --task {id}`
  - CXL task: `numactl --membind=1 python task_runner.py --task {id}`
- [ ] Create `task_runner.py`: a simple memory-intensive workload script that:
  - Allocates N MB of memory (use numpy arrays)
  - Simulates work with a loop
  - Reports: start time, end time, memory used
- [ ] Run all 8 tasks with RQAOA assignments using `subprocess` + numactl

#### Verification ✔️
- All 8 tasks execute successfully
- Each task logs its memory node binding
- Task completion times are recorded in `results/execution_log.csv`

---

### ✅ DAY 6 — CXL Latency + Bandwidth Simulation
**Theme:** Make the simulation realistic by modeling CXL behavior.

#### Tasks
- [ ] Add **latency injection** to `task_runner.py`:
  - If bound to Node 1 (CXL): `time.sleep(latency_penalty_per_access)`
  - Parameterize: `--latency-penalty 0.0002` (200 µs per 1000 accesses)
- [ ] Add **bandwidth throttling**:
  - CXL tasks: limit memory write rate using chunked writes with sleeps
- [ ] Re-run all schedulers (FCFS, RR, Greedy, RQAOA) with latency + bandwidth simulation
- [ ] Record per-task completion time for each scheduler

#### Verification ✔️
- CXL-bound tasks measurably take longer than DRAM-bound tasks
- Latency difference is in the expected ratio (~2–3x)
- All 4 scheduler results saved with timing data

---

### ✅ DAY 7 — Evaluation + Metrics Dashboard
**Theme:** Turn raw data into insights and visualizations.

#### Tasks
- [ ] Compute final metrics for all 4 schedulers:
  - Average task completion time
  - Total weighted latency cost (from QUBO objective)
  - DRAM utilization %
  - Makespan (time when last task finishes)
- [ ] Generate plots using matplotlib:
  - Bar chart: completion time per scheduler
  - Bar chart: total latency cost per scheduler
  - Stacked bar: DRAM vs CXL task distribution
  - Line chart: task completion timeline (Gantt-style)
- [ ] Save all plots to `results/` folder
- [ ] Print a summary comparison table to console

#### Verification ✔️
- 4+ plots generated and saved
- RQAOA result is comparable to (or better than) greedy baseline
- Summary table is readable and accurate

---

### ✅ DAY 8 — IBM Quantum Validation Run
**Theme:** Run one small version on real quantum hardware for credibility.

#### Tasks
- [ ] Reduce problem to 4–5 tasks (to fit within qubit budget)
- [ ] Configure OpenQAOA to use IBM Quantum backend with your API token
- [ ] Submit job and wait (may take hours — submit early in the day)
- [ ] Once result returns: extract bitstring, decode assignment
- [ ] Compare IBM QPU result vs Aer simulation result for the same 4-task problem
- [ ] Document noise effects (results may differ — that's expected and worth noting)

#### Verification ✔️
- IBM job submitted and completes (even if result is noisy)
- Bitstring from QPU vs Aer simulator comparison is logged
- Any discrepancy is documented with an explanation

---

### ✅ DAY 9 — Code Cleanup + README + Report Writing
**Theme:** Make the project presentable and reproducible.

#### Tasks
- [ ] Refactor code: clean up all scripts, add docstrings, remove debug prints
- [ ] Write `README.md` with:
  - Project overview (2 paragraphs)
  - Setup instructions
  - How to run each module
  - Results summary with embedded plots
- [ ] Write project report sections:
  - Abstract
  - Problem Statement
  - Methodology (QUBO, RQAOA, NUMA simulation)
  - Results & Discussion
  - Limitations & Future Work
  - References
- [ ] Add requirements.txt (`pip freeze > requirements.txt`)
- [ ] Test full pipeline from scratch on a clean environment

#### Verification ✔️
- Someone else could clone and run the project using only the README
- Report is at least 4–5 pages
- All results plots are embedded in the README

---

### ✅ DAY 10 — Final Testing + Buffer + Submission Polish
**Theme:** End-to-end validation, fix bugs, finalize everything.

#### Tasks
- [ ] Run the full pipeline end-to-end one final time
- [ ] Fix any last bugs or inconsistencies in results
- [ ] Verify all result files are present in `results/`
- [ ] Create a final `demo.py` that runs the entire pipeline with one command
- [ ] Record a short screen recording of the system running (optional but impressive)
- [ ] Final review of report and README
- [ ] Submit / Push to GitHub

#### Verification ✔️
- `python demo.py` runs the full pipeline without errors
- All 4 schedulers compared in final output
- Project is on GitHub with a clean commit history

---

## 📦 Deliverables Checklist

- [ ] `quantum_scheduler/` — full working codebase
- [ ] `results/` — all plots and CSVs
- [ ] `README.md` — setup + run instructions
- [ ] `requirements.txt` — reproducible environment
- [ ] `report.pdf` — written project report
- [ ] IBM Quantum job ID (proof of hardware run)
- [ ] (Optional) GitHub repo link

---

## ⚠️ Risk Mitigation

| Risk | Mitigation |
|---|---|
| OpenQAOA API breaks / incompatibility | Pin version: `pip install openqaoa==0.2.x`, check GitHub issues |
| IBM Quantum queue is too long | Submit on Day 8 morning; use ibm_nairobi or smallest available device |
| numactl not available (macOS) | Use a Linux VM (VirtualBox) or a free Linux cloud instance (e.g., Oracle Cloud Free Tier) |
| RQAOA gives random/wrong results | Expected on small problems — document it, compare with brute force |
| Running out of time | Days 8–9–10 have buffer — IBM run + writing can overlap |

---

## 🧠 Daily Learning Focus (Parallel to Building)

| Day | Learn While You Build |
|---|---|
| Day 1 | Watch: *"Quantum Computing for Computer Scientists"* (Microsoft Research) |
| Day 2 | Read: PyQUBO README + QUBO formulation blog post |
| Day 3 | No new learning — coding day |
| Day 4 | Read: OpenQAOA RQAOA notebook in their GitHub examples |
| Day 5 | Read: `numactl` man page + Linux NUMA docs |
| Day 6 | No new learning — coding day |
| Day 7 | Watch: *"How to present research results"* (any short video) |
| Day 8 | Read: IBM Quantum docs on submitting jobs |
| Day 9–10 | Focus 100% on writing and polish |

---

*Generated for: Quantum-Assisted Optimization Engine for CXL-Aware Hybrid Scheduling*  
*Timeline: 10 Days Aggressive Sprint*
