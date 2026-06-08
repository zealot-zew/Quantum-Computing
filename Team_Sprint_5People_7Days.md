# 🚀 5-Person Aggressive Team Sprint — 7 Days
## Quantum-Assisted Optimization Engine for CXL-Aware Hybrid Scheduling

> **Start Date:** Day 1 | **End Date:** Day 7
> **Goal:** Complete a working, evaluated, and documented system by end of Day 7.
> **Strategy:** Every person owns **two domains**. No silos. Integrate daily.
> **Motto:** Build fast. Cross-train. Ship on Day 7.

---

## 👥 Team Roles — Dual Ownership

Each person is responsible for tasks from **two areas** throughout the week.
This prevents bottlenecks and ensures everyone understands the full system.

| Person | Primary Role | Secondary Role | What They Own Together |
|--------|-------------|----------------|------------------------|
| **Anjana** | Quantum Algorithm Engineer | Systems & Infra | QUBO math, RQAOA, IBM Quantum run + NUMA setup, executor |
| **Hari** | Systems & Infra Engineer | Quantum Algorithm | `numactl` orchestration, task runner + RQAOA config, result parsing |
| **Smarth** | Classical Scheduler Engineer | Simulation & Evaluation | FCFS, RR, Greedy schedulers + CXL latency injection, metrics |
| **Vikas** | Simulation & Evaluation Engineer | Classical Scheduler | Plots, benchmarks, evaluation pipeline + Greedy/Priority scheduler variant |
| **Devandra** | Documentation & Integration Lead | Full-Stack Glue | README, report, `main.py` demo + daily merge reviews, test runner |

> ⚠️ **Daily Sync Rule:** Everyone pushes their branch by **6 PM each day**.
> P5 does a daily integration test every evening. Blockers go in team chat immediately.

---

## 📅 Day 1 — Setup, Scaffold & Domain Onboarding

> **Theme:** Every person gets their full dual-domain environment running. No one waits on anyone else.

---

### 🧑‍💻 P1 (Anjana) — Quantum Algo + Infra

- [ ] Set up Python virtual environment; install quantum + system dependencies:
  ```bash
  pip install qiskit qiskit-aer openqaoa pyqubo numpy psutil networkx
  ```
- [ ] Sign up at quantum.ibm.com — save API token to `.env` file
- [ ] Write and run a Qiskit "Hello World" Bell state circuit on Aer simulator — confirm histogram output
- [x] Configure Linux environment (AWS EC2 / VM): apply `numa=fake=2` GRUB boot parameter, reboot — 🛑 `CONFIG_NUMA_EMU` not supported on Ubuntu 24.04/26.04 kernels; `numa=fake=2` cannot be activated. ✅ **Decision: proceeding with software latency simulation in `task_runner.py`.** See `docs/numa_verification.md`.
- [x] Verify `numactl --hardware` shows 2 NUMA nodes — document output in `docs/numa_verification.md` — ✅ Investigation complete; single-node outcome documented with full explanation and workaround.

---

### 🧑‍💻 P2 (Hari) — Infra + Quantum Algo

- [x] Set up Python virtual environment; install all dependencies:
  ```bash
  pip install numpy psutil networkx matplotlib pandas qiskit qiskit-aer openqaoa
  ```
  ✅ `.venv` created with Python 3.10. `setup_env.sh` added to enforce this constraint for all teammates.
- [x] Create the shared project folder structure on Git and push to `main`:
  ```
  quantum_scheduler/
  ├── qubo/
  ├── rqaoa/
  ├── scheduler/
  ├── executor/
  ├── evaluation/
  ├── results/
  ├── tests/
  └── main.py
  ```
  ✅ `src/rqaoa/`, `src/scheduler/`, `src/executor/`, `src/evaluation/`, `tests/`, `results/` all created.
- [ ] Study QUBO/Ising model basics (30 min — "QUBO formulation tutorial" on YouTube)
- [x] Write `task_runner.py` skeleton: accepts `--task-id`, `--memory-mb`, `--node` CLI args; prints args back — just the shell for now ✅ Full skeleton with validation in place.

---

### 🧑‍💻 P3 (Smarth) — Classical Scheduler + Simulation

- [x] Set up Python virtual environment; install dependencies:
  ```bash
  pip install numpy pandas networkx matplotlib
  ```
  ✅ Confirmed in `docs/p3_day1_verification.md`.
- [x] Define the shared `Task` dataclass in `scheduler/task_model.py` and commit:
  ```python
  @dataclass
  class Task:
      task_id: int
      memory_requirement_mb: float
      priority: int
      memory_sensitivity: float  # 0.0 to 1.0
  ```
  ✅ `src/scheduler/task_model.py` exists with validation in `__post_init__`.
- [x] Define the canonical set of 8 tasks with realistic values — commit to `scheduler/tasks.py` ✅ `src/scheduler/tasks.py` created with all 8 tasks.
- [x] Read the CXL simulation section of the project proposal (20 min) ✅ Confirmed in `docs/p3_day1_verification.md`.
- [x] Stub out empty `FCFSScheduler`, `RoundRobinScheduler`, `GreedyScheduler` classes with docstrings ✅ All three files exist in `src/scheduler/`.

---

### 🧑‍💻 P4 (Vikas) — Evaluation + Classical Scheduler

- [ ] Set up Python virtual environment; install dependencies:
  ```bash
  pip install numpy matplotlib pandas psutil
  ```
- [ ] Read the full project proposal and evaluation metrics section (30 min)
- [x] Create the `results/` directory structure with subdirectory `results/plots/` — add `.gitkeep` ✅ `results/` directory exists in the project root.
- [x] Define the metrics schema: design what columns go into `results/execution_log.csv` and `results/all_schedulers_summary.csv` — write schema as a comment block in `evaluation/metrics.py` ✅ Full schema tables and typed, documented function stubs added to `src/evaluation/metrics.py`.
- [x] Stub out `GreedyScheduler` variant (Priority-Weighted) in `scheduler/greedy_priority_scheduler.py` with docstrings ✅ `src/scheduler/greedy_priority_scheduler.py` created with composite score formula, named constants, and full docstrings.

---

### 🧑‍💻 P5 (Devandra) — Docs + Integration

- [ ] Read the full project proposal and the `Agents.md` rules file (30 min)
- [ ] Set up Git repo branch protection: no direct push to `main`; require PR review
- [x] Create `docs/branch_summaries/` directory with `README.md` explaining the branching convention ✅ `quantum_scheduler/docs/branch_summaries/README.md` exists.
- [x] Write the full report skeleton `report.md` with all section headers — empty but structured:
  Abstract, Problem Statement, Methodology (QUBO, RQAOA, NUMA Simulation), Results & Discussion, Limitations, References ✅ `quantum_scheduler/report.md` exists (5896 bytes).
- [x] Write `requirements.txt` template and verify all 5 people confirm their installs by EOD ✅ `requirements.txt` updated with verification checklist for all 5 members.

---

### ✔️ Day 1 End-of-Day Verification
- [ ] All 5 environments running — all imports pass with no errors ⚠️ P4 env not yet confirmed.
- [ ] Git repo exists with correct folder structure; all 5 people pushed their Day 1 branch ⚠️ Pending commits from P2 (Hari) — branch `feature/environment-setup` not yet pushed.
- [x] `numactl --hardware` — documented ✅ Hardware NUMA unavailable on AWS kernel; software simulation strategy confirmed in `docs/numa_verification.md`.
- [x] Shared `Task` dataclass and 8-task definition merged to `main` ✅ `src/scheduler/task_model.py` and `src/scheduler/tasks.py` complete.
- [ ] Qiskit Hello World runs successfully on P1's machine ⚠️ Anjana's task — status unknown.

---

## 📅 Day 2 — QUBO Build + Executor + Scheduler Foundations

> **Theme:** P1 builds the math core and the executor shell. P3 ships all 3 classical schedulers. P4 builds the simulation. Fast day.

---

### 🧑‍💻 P1 — Quantum Algo + Infra

- [x] Implement `qubo/qubo_builder.py` — `build_qubo_from_tasks()`:
  - Diagonal: `Q[i][i] = sensitivity_i × (CXL_LATENCY - DRAM_LATENCY) × memory_mb_i`
  - Off-diagonal: expand DRAM capacity constraint penalty `P × (Σ(1-x_i)×m_i - C_DRAM)²`
- [x] Generate and save QUBO heatmap to `results/qubo_heatmap.png`
- [x] Implement `executor/numa_executor.py` — `execute_with_numa_binding()`:
  - DRAM: `numactl --cpunodebind=0 --membind=0 python task_runner.py --task-id {id}`
  - CXL: `numactl --cpunodebind=1 --membind=1 python task_runner.py --task-id {id}`
  - Include `FileNotFoundError` fallback for non-Linux environments
- [x] Write unit tests `tests/test_qubo_builder.py` (matrix shape, diagonal values, symmetry)

---

### 🧑‍💻 P2 — Infra + Quantum Algo

- [x] Flesh out `task_runner.py` fully:
  - Allocate memory: `data = np.random.rand(mb * 1024 * 1024 // 8)`
  - Simulate work: iterate over array in chunks
  - Log: task ID, node, start time, end time, duration to stdout (CSV format)
- [x] Implement `executor/task_orchestrator.py` — `run_all_tasks(assignment: dict[int, str])`:
  - Launch each task in a separate subprocess with correct `numactl` binding
  - Wait for all to finish (`subprocess.Popen` + `.wait()`)
- [x] Convert PyQUBO output format — write `rqaoa/qubo_converter.py` that translates `qubo_builder` output into OpenQAOA-compatible QUBO dict format
- [x] Write unit tests `tests/test_numa_executor.py` (mock subprocess calls)

---

### 🧑‍💻 P3 — Classical Scheduler + Simulation

- [x] Implement `scheduler/fcfs_scheduler.py` — `FCFSScheduler`:
  - Assign tasks in arrival order; DRAM until capacity exceeded, then CXL
- [x] Implement `scheduler/round_robin_scheduler.py` — `RoundRobinScheduler`:
  - Alternate assignment between DRAM and CXL
- [x] Implement `scheduler/greedy_scheduler.py` — `GreedyScheduler`:
  - Sort by `memory_sensitivity` descending; fill DRAM first
- [x] Each scheduler outputs `{task_id: "DRAM" | "CXL"}` dict + computes `total_latency_cost`
- [x] Add **latency injection** to `task_runner.py` (coordinate with P2):
  - If `--node 1` (CXL): `time.sleep(LATENCY_PENALTY_S)` per N memory accesses

---

### 🧑‍💻 P4 — Evaluation + Classical Scheduler

- [x] Implement `scheduler/greedy_priority_scheduler.py` — `PriorityWeightedGreedyScheduler`:
  - Sort by `priority × memory_sensitivity` descending; fill DRAM first
- [x] Implement `evaluation/metrics.py`:
  - `compute_avg_latency(results: list[dict]) -> float`
  - `compute_makespan(results: list[dict]) -> float`
  - `compute_dram_utilization(assignment: dict, tasks: list[Task]) -> float`
- [x] Write unit tests `tests/test_metrics.py` with known-input assertions
- [x] Test `task_runner.py` manually on both Node 0 and Node 1 — confirm timing difference

---

### 🧑‍💻 P5 — Docs + Integration

- [x] Write the **Problem Statement** section of `report.md` (full text, not bullets — 300+ words)
- [x] Write the **Methodology — QUBO Formulation** subsection of `report.md`
- [x] Review and merge P1's `qubo_builder.py` and P3's scheduler PRs — check naming conventions vs `Agents.md`
- [x] Update `requirements.txt` with all packages used today
- [x] Write `scheduler/scheduler_interface.py`: base class `BaseScheduler` with `schedule(tasks) -> dict` abstract method

---

### ✔️ Day 2 End-of-Day Verification
- [x] `build_qubo_from_tasks()` returns an 8×8 matrix — all unit tests pass
- [x] All 3 classical schedulers run and produce valid assignments — no DRAM overflow
- [x] `task_runner.py` executes on both NUMA nodes and logs timing to stdout
- [x] `numa_executor.py` tests pass with mocked subprocess
- [x] 2 report sections written and committed

---

## 📅 Day 3 — RQAOA Integration + Full Execution Pipeline

> **Theme:** Connect quantum output to real OS execution. End of Day 3 = first full pipeline running.

---

### 🧑‍💻 P1 — Quantum Algo + Infra

- [ ] Implement `rqaoa/rqaoa_runner.py` — `run_rqaoa_optimizer()`:
  - Backend: Qiskit Aer (shot-based simulation)
  - Optimizer: COBYLA, layers p=1, recursive cutoff at 3 variables
- [ ] Run RQAOA on the full 8-task QUBO — extract output bitstring
- [ ] Write `rqaoa/rqaoa_config.py` with all tunable constants (`RQAOA_LAYERS`, `RECURSIVE_CUTOFF`, `OPTIMIZER`)
- [ ] Wire executor to run all 8 tasks using RQAOA assignment — test end-to-end on VM
- [ ] Log RQAOA total cost vs all 3 classical baselines to console

---

### 🧑‍💻 P2 — Infra + Quantum Algo

- [x] Implement `rqaoa/result_parser.py` — `decode_bitstring()`:
  - Maps 8-bit string → `{task_id: "DRAM" | "CXL"}` dict
  - Validates that all 8 tasks are assigned
- [x] Add **bandwidth throttling** to `task_runner.py`:
  - CXL tasks: write data in chunks with small sleeps between chunks
  - Parameterise via `--bandwidth-limit` CLI arg
- [x] Add `--dry-run` flag to `task_orchestrator.py` for testing without actual execution
- [ ] Wire the orchestrator to accept a scheduler result dict and run all 8 tasks concurrently
- [x] Collect per-task return codes — log any subprocess failures

---

### 🧑‍💻 P3 — Classical Scheduler + Simulation

- [ ] Run all 4 classical schedulers (FCFS, RR, Greedy, PriorityWeighted) against the 8-task set
- [ ] For each scheduler, compute and store:
  - Total weighted latency cost (QUBO objective value)
  - Number of tasks in DRAM vs CXL
  - Simulated total completion time
- [ ] Save all results to `results/classical_baselines.csv`
- [ ] Re-run all 4 schedulers with latency + bandwidth simulation active — record updated timing numbers
- [ ] Write unit tests for edge cases: all tasks fit in DRAM; no tasks fit; tasks with identical sensitivity

---

### 🧑‍💻 P4 — Evaluation + Classical Scheduler

- [ ] Re-run CXL-bound vs DRAM-bound tasks — confirm CXL tasks take measurably longer (~2–3×)
- [ ] Implement `compute_total_latency_cost(assignment, tasks, qubo_matrix)` in `evaluation/metrics.py`
- [ ] Start generating evaluation plots:
  - **Bar chart:** average task completion time per scheduler
  - **Bar chart:** total weighted latency cost per scheduler
- [ ] Save both plots to `results/plots/`
- [ ] Run all 4 schedulers through the full execution pipeline — record per-task completion time to `results/execution_log.csv`

---

### 🧑‍💻 P5 — Docs + Integration

- [ ] Write the **Methodology — RQAOA Algorithm** subsection of `report.md`
- [ ] Write the **Methodology — NUMA Simulation** subsection of `report.md`
- [ ] Do an end-of-day integration test: `QUBO build → RQAOA → decode → orchestrate 8 tasks → log results`
- [ ] File integration bugs as GitHub issues with clear repro steps
- [ ] Update branch summary docs for all merged branches

---

### ✔️ Day 3 End-of-Day Verification
- [ ] RQAOA runs on 8 tasks — returns a valid 8-bit assignment, no crash
- [ ] All 8 tasks execute end-to-end through the orchestrator with correct `numactl` binding
- [ ] CXL tasks measurably take longer than DRAM tasks — ratio logged
- [ ] `results/classical_baselines.csv` exists with all 4 schedulers' data
- [ ] 4 report sections written

---

## 📅 Day 4 — Full Benchmarking + Visualisations

> **Theme:** Run every scheduler through the full pipeline with simulation. Generate all plots. Report 60% done.

---

### 🧑‍💻 P1 — Quantum Algo + Infra

- [ ] Run RQAOA with p=1 vs p=2 — compare result quality, document best setting in comments
- [ ] Try tighter recursive cutoff (2 variables) vs default (3) — compare results
- [ ] Prepare the reduced 4–5 task QUBO for IBM Quantum submission on Day 5
- [ ] Profile total wall-clock time for each scheduler's full 8-task execution run
- [ ] Investigate and fix any subprocess race conditions in the orchestrator

---

### 🧑‍💻 P2 — Infra + Quantum Algo

- [ ] Run all 4 schedulers (FCFS, RR, Greedy, RQAOA) through the full execution pipeline with simulation
- [ ] Record per-task completion time for every scheduler → `results/execution_log.csv`
- [ ] Add logging with `logging.getLogger(__name__)` everywhere — remove all `print()` statements from `executor/`
- [ ] Write unit tests for `result_parser.py` — test valid and malformed bitstrings
- [ ] Verify RQAOA cost is logged vs classical baselines — confirm numbers make sense

---

### 🧑‍💻 P3 — Classical Scheduler + Simulation

- [ ] Aggregate all scheduler results into `results/all_schedulers_summary.csv`:
  - Columns: scheduler, avg_latency_ms, total_latency_cost, dram_tasks, cxl_tasks, makespan_s, dram_utilization_pct
- [ ] Run `pytest tests/` — confirm all scheduler tests pass, fix any failures
- [ ] Write `scheduler/__init__.py` that exports all 4 scheduler classes cleanly
- [ ] Add `flake8` and `mypy` pass on all `scheduler/` files — fix all warnings
- [ ] Help P4 verify that CSV data matches the generated plots

---

### 🧑‍💻 P4 — Evaluation + Classical Scheduler

- [ ] Generate remaining evaluation plots:
  - **Stacked bar:** DRAM vs CXL task count per scheduler
  - **Line/Gantt chart:** task completion timeline across schedulers
  - **Combined summary plot:** all schedulers on all 3 metrics side-by-side
- [ ] Save all plots to `results/plots/` with descriptive filenames
- [ ] Print a formatted comparison summary table to stdout using `tabulate` or manual formatting
- [ ] Run `flake8` and `mypy` on all `evaluation/` files — fix all warnings
- [ ] Write unit tests for `compute_dram_utilization()` with known inputs

---

### 🧑‍💻 P5 — Docs + Integration

- [ ] Write the **Results & Discussion** section of `report.md` — populate with Day 3–4 data and all plots
- [ ] Embed all 5 plots into `README.md` with captions
- [ ] Review all code merged today — check docstrings, type hints, named constants vs `Agents.md`
- [ ] Update all branch summary documents for today's branches
- [ ] Draft the **Limitations & Future Work** section of `report.md`

---

### ✔️ Day 4 End-of-Day Verification
- [ ] `results/all_schedulers_summary.csv` has all 4 schedulers' data
- [ ] 5+ plots generated and saved to `results/plots/`
- [ ] RQAOA result is comparable to or better than Greedy baseline — logged
- [ ] `pytest tests/` passes for all scheduler + metrics tests
- [ ] Report is 60% complete (Problem Statement + full Methodology + Results drafted)

---

## 📅 Day 5 — IBM Quantum Run + Code Cleanup

> **Theme:** Get real quantum hardware validation. Meanwhile, all code becomes production-ready.

---

### 🧑‍💻 P1 — Quantum Algo + Infra

- [ ] Configure OpenQAOA for IBM Quantum backend with stored API token — **submit job first thing in the morning**
- [ ] While waiting: refactor `rqaoa_runner.py` — full docstrings, type hints, no magic numbers
- [ ] Once result returns: extract bitstring, decode assignment for the 4-task version
- [ ] Compare IBM QPU bitstring vs Aer simulation bitstring — log differences and explain noise effects
- [ ] Run `flake8` and `mypy` on all `rqaoa/` and `executor/` files — fix all warnings

---

### 🧑‍💻 P2 — Infra + Quantum Algo

- [ ] Refactor `numa_executor.py` and `task_orchestrator.py` — docstrings, remove debug prints, add type hints
- [ ] Add `--scheduler` CLI flag to the orchestrator: `python main.py --scheduler rqaoa|fcfs|rr|greedy`
- [ ] Final `tests/test_numa_executor.py` — full mock coverage for all execution paths
- [ ] Write `docs/deployment_guide.md`: how to set up the Linux VM, configure fake NUMA, and run the system from scratch
- [ ] Run `flake8` and `mypy` on all `executor/` files — fix all warnings

---

### 🧑‍💻 P3 — Classical Scheduler + Simulation

- [ ] Refactor all 4 scheduler files — full docstrings, type hints, no magic numbers
- [ ] Refactor `task_runner.py` — clean up, add error handling for memory allocation failures
- [ ] Add comprehensive edge-case unit tests: all tasks in DRAM, all tasks in CXL, tasks with identical sensitivity scores
- [ ] Run `flake8` and `mypy` on all `scheduler/` files — fix all warnings
- [ ] Ensure `BaseScheduler` interface is perfectly consistent across all 4 implementations

---

### 🧑‍💻 P4 — Evaluation + Classical Scheduler

- [ ] Refactor `metrics.py` and all plot generation code — docstrings, constants, type hints
- [ ] Final polish on all 5 plots: publication-quality titles, axis labels, legends, consistent colour scheme
- [ ] Generate one extra plot: RQAOA vs brute-force (exhaustive search on 4-task version) to show optimality gap
- [ ] Write `tests/test_metrics.py` — unit test every metric function with known-input assertions
- [ ] Run `flake8` and `mypy` on all `evaluation/` files — fix all warnings

---

### 🧑‍💻 P5 — Docs + Integration

- [ ] Write the full `README.md`:
  - Project overview (2 paragraphs)
  - Team setup instructions
  - How to run each module individually
  - How to run the full pipeline: `python main.py --scheduler rqaoa`
  - Results summary with all 5 embedded plots
- [ ] Run `pip freeze > requirements.txt` — verify all dependencies captured
- [ ] Begin writing `main.py`: full pipeline entry point — QUBO build → choose scheduler → execute → evaluate → plot
- [ ] Test `python main.py --scheduler fcfs` runs end-to-end with no errors

---

### ✔️ Day 5 End-of-Day Verification
- [ ] IBM Quantum job submitted and result received (even if noisy) — comparison logged
- [ ] All files pass `flake8` and `mypy` — zero warnings across entire codebase
- [ ] `README.md` first draft complete — reviewed by at least one other person
- [ ] `requirements.txt` is complete and accurate
- [ ] `main.py --scheduler fcfs` runs end-to-end successfully

---

## 📅 Day 6 — Integration, Demo Pipeline + Report Finalisation

> **Theme:** Merge everything, finish `main.py`, complete the report.

---

### 🧑‍💻 P1 — Quantum Algo + Infra

- [ ] Write IBM Quantum hardware results into **Results & Discussion** section of `report.md` — compare to simulated results
- [ ] Add a **Noise Effects** subsection: why QPU results differ from simulation, what this means
- [ ] Final review of RQAOA section of `report.md` — verify all math formulas are correct
- [ ] Write `docs/branch_summaries/` documents for all your branches
- [ ] Integration test: clone the repo fresh, follow README, run `main.py --scheduler rqaoa` — confirm zero errors

---

### 🧑‍💻 P2 — Infra + Quantum Algo

- [ ] Final integration test on Linux VM: clone from scratch, follow README, run full pipeline — fix any env-specific bugs
- [ ] Verify `numactl` binding is working correctly in the final run — spot-check task logs
- [ ] Help P5 finish `main.py` — integrate orchestrator and executor into the pipeline
- [ ] Write `docs/branch_summaries/` documents for all your branches
- [ ] Add a `--scheduler all` mode to `main.py` that runs all 4 schedulers sequentially and prints comparison

---

### 🧑‍💻 P3 — Classical Scheduler + Simulation

- [ ] Write the **Classical Schedulers** subsection of `report.md` — explain FCFS, RR, Greedy, Priority-Weighted with examples
- [ ] Write the **CXL Simulation** subsection of `report.md` — explain latency injection and bandwidth throttling
- [ ] Final `pytest tests/` run — ensure 100% pass rate; paste output into branch summary docs
- [ ] Final review of all scheduler code for `Agents.md` clean code compliance
- [ ] Write `docs/branch_summaries/` documents for all your branches

---

### 🧑‍💻 P4 — Evaluation + Classical Scheduler

- [ ] Final plots review — ensure all 5 plots have correct titles, axis labels, legends
- [ ] Generate the final combined summary plot: all 4 schedulers × all 3 metrics in one figure
- [ ] Ensure all CSVs and plots are present in `results/` with correct filenames
- [ ] Write the **Evaluation Metrics** subsection of `report.md`
- [ ] Write `docs/branch_summaries/` documents for all your branches

---

### 🧑‍💻 P5 — Docs + Integration

- [ ] Finish `main.py` — full pipeline in one file with `--scheduler` flag: QUBO build → schedule → execute → evaluate → plot
- [ ] Test `python main.py --scheduler all` runs end-to-end without errors from a fresh clone
- [ ] Finalise `report.md` — write Abstract and References, review all sections for consistency
- [ ] Final grammar + formatting pass on `README.md` and `report.md`
- [ ] Ensure all branch summary docs are committed for every branch across all 5 people

---

### ✔️ Day 6 End-of-Day Verification
- [ ] `python main.py --scheduler all` runs the full pipeline end-to-end — zero errors
- [ ] `report.md` is complete — all 6 sections written (Abstract, Problem Statement, Methodology ×3, Results, Limitations, References)
- [ ] All 5 branch summary docs committed across all people
- [ ] Final plots are publication-quality and embedded in `README.md`

---

## 📅 Day 7 — Final Testing, Polish + Submission

> **Theme:** Lock it down. Test everything from scratch. Tag and ship.

---

### 🧑‍💻 P1 — Quantum Algo + Infra

- [ ] Final end-to-end test of RQAOA pipeline on a fresh virtual environment — document result
- [ ] Verify IBM Quantum job ID is recorded in `report.md` as proof of hardware run
- [ ] Review all quantum-related content in the report for mathematical accuracy
- [ ] Confirm all `rqaoa/` and `executor/` tests still pass after final merges

---

### 🧑‍💻 P2 — Infra + Quantum Algo

- [ ] Final clone-from-scratch test on Linux VM: follow README, run `main.py --scheduler all` — confirm zero errors
- [ ] Verify `numactl` binding in final run — spot-check at least 2 task logs to confirm correct node binding
- [ ] Fix any last environment-specific or path issues found during final test
- [ ] Confirm `docs/deployment_guide.md` is accurate and complete

---

### 🧑‍💻 P3 — Classical Scheduler + Simulation

- [ ] Run `pytest tests/ -v` — confirm 100% pass rate; paste final output into all branch summary docs
- [ ] Review `results/all_schedulers_summary.csv` — confirm every number is accurate
- [ ] Final `flake8` pass on all `scheduler/` files — zero warnings
- [ ] Read report and verify Classical Scheduler and CXL Simulation sections are accurate

---

### 🧑‍💻 P4 — Evaluation + Classical Scheduler

- [ ] Final review of all 5+ plots — correct any visual or labelling issues
- [ ] Ensure all files are present: `results/plots/*.png`, `results/*.csv`
- [ ] Optional: record a 2–3 min screen recording of `python main.py --scheduler all` running
- [ ] Final `mypy` pass on all `evaluation/` files — zero errors

---

### 🧑‍💻 P5 — Docs + Integration

- [ ] Final review of `README.md` — clone → run flow must work perfectly end-to-end
- [ ] Convert `report.md` to PDF (`pandoc report.md -o report.pdf`) or export from editor
- [ ] Final push to `main` — clean commit history, no stale feature branches left open
- [ ] Tag the release: `git tag v1.0.0 && git push origin v1.0.0`
- [ ] Submit / share the GitHub repo link with the team and stakeholders

---

### ✔️ Day 7 Final Submission Checklist (Everyone Signs Off)
- [ ] `python main.py --scheduler all` — zero errors from fresh clone
- [ ] `pytest tests/ -v` — 100% pass rate
- [ ] `flake8 src/` — zero linting errors
- [ ] `mypy src/` — zero type errors
- [ ] `results/` folder: all CSVs and 5+ plots present
- [ ] `README.md` complete with embedded plots
- [ ] `report.pdf` finalised — minimum 4–5 pages
- [ ] IBM Quantum job ID documented in report
- [ ] All branch summary docs committed — one per branch, per person
- [ ] GitHub repo public with clean commit history and `v1.0.0` tag

---

## 📦 Final Deliverables

| Deliverable | Owner |
|-------------|-------|
| `quantum_scheduler/` — full working codebase | All |
| `results/*.csv` — classical_baselines, execution_log, all_schedulers_summary | P3, P4 |
| `results/plots/*.png` — 5+ plots | P4 |
| `README.md` — setup + run instructions with embedded plots | P5 |
| `requirements.txt` — reproducible environment | P5 |
| `report.pdf` — written report (4–5 pages minimum) | P5 (all contribute sections) |
| `docs/deployment_guide.md` — Linux VM + NUMA setup | P2 |
| `docs/branch_summaries/` — one doc per branch per person | All |
| IBM Quantum job ID — proof of hardware run | P1 |
| GitHub repo with `v1.0.0` tag | P5 |

---

## ⚠️ Risk Mitigation

| Risk | Owner | Mitigation |
|------|-------|------------|
| RQAOA breaks or gives wrong results | P1 | Test p=1 first; compare with brute-force on 4-task version |
| IBM Quantum queue is too long | P1 | Submit **Day 5 morning**; use smallest available device |
| `numactl` not available | P2 | VM is set up on Day 1 as top priority; fallback mode in executor |
| Integration fails on merge | P5 | Daily integration test every evening; block merges that break pipeline |
| One person falls behind | All | Each module is loosely coupled — others proceed independently |
| Code doesn't pass `flake8`/`mypy` | All | Run linting at end of each day, not just before push |

---

*Generated for: Quantum-Assisted Optimization Engine for CXL-Aware Hybrid Scheduling*
*Format: 5-Person Dual-Role Team Sprint — 7 Days Aggressive*
