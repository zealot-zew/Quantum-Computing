# Project Progress Summary

## 📌 Active Context

- **Current Branch:** `feature/environment-setup`
- **Latest Update:** 2026-06-06
- **Sprint Day:** 1 (complete) → Day 2 starting
- **Active Developer/Agent:** Antigravity

---

## 🚀 Active Goals & Roadmap

- [x] Set up Python virtual environment (`.venv`) with all required packages
- [x] Establish project folder structure (`src/rqaoa/`, `src/scheduler/`, `src/executor/`, `src/evaluation/`, `tests/`, `results/`)
- [x] Investigate NUMA setup — Hardware NUMA unavailable; software latency simulation confirmed in `task_runner.py`
- [x] Standardize codebase structure: add per-module READMEs, slim down `Agents.md`, extract math docs
- [ ] Day 2: Implement all 4 classical scheduler bodies + QUBO builder + executor skeleton
- [ ] Day 3: RQAOA runner + result parser + full execution pipeline
- [ ] Day 4: Benchmarking, plots, CSV outputs
- [ ] Day 5: IBM Quantum run + code cleanup / linting pass
- [ ] Day 6: Integration, `main.py` fully wired, report finalised
- [ ] Day 7: Final testing, tag v1.0.0, submit

---

## 📊 Module Status

| Module | Status | What Exists | What's Missing |
|--------|--------|-------------|----------------|
| `src/scheduler/` | ✅ Day 1 done | `task_model.py` ✅, `tasks.py` ✅, `__init__.py` ✅, 4 scheduler stubs 🔲 | Scheduler bodies (Day 2), `scheduler_interface.py` (Day 2) |
| `src/rqaoa/` | 🔲 Stub only | `__init__.py` | `qubo_builder.py`, `rqaoa_runner.py`, `rqaoa_config.py`, `result_parser.py`, `qubo_converter.py` |
| `src/executor/` | 🔲 Stub only | `__init__.py` | `numa_executor.py`, `task_orchestrator.py` |
| `src/evaluation/` | 🔲 Schemas done | `metrics.py` (schemas + stubs), `graphs.py` (stubs) | All function bodies (Day 3–4) |
| `tests/` | 🔲 Empty | — | All test files (Day 2+) |
| `main.py` | 🔲 Scaffold | CLI args parse, logs selected scheduler | Full pipeline wiring (Day 5) |
| `task_runner.py` | 🔲 Scaffold | CLI args parse + logging | Memory allocation, latency injection, CSV output (Day 2–3) |

---

## 📁 Files Created or Modified

### Day 1 (initial setup)
- `requirements.txt`: Core dependencies + Python 3.10 constraint documented
- `setup_env.sh`: Robust init script enforcing Python 3.10 for `openqaoa`
- `src/scheduler/task_model.py`: `Task` dataclass with `__post_init__` validation
- `src/scheduler/tasks.py`: 8 canonical tasks + DRAM/CXL capacity/latency constants
- `src/scheduler/fcfs_scheduler.py`: `FCFSScheduler` stub with docstrings
- `src/scheduler/greedy_scheduler.py`: `GreedyScheduler` stub with docstrings
- `src/scheduler/greedy_priority_scheduler.py`: `GreedyPriorityScheduler` stub with composite score formula
- `src/scheduler/round_robin_scheduler.py`: `RoundRobinScheduler` stub with docstrings
- `src/scheduler/__init__.py`: Module exports
- `src/evaluation/metrics.py`: CSV schemas (comment blocks) + 4 metric function stubs
- `task_runner.py`: CLI skeleton with argument validation
- `main.py`: CLI scaffold with `--scheduler` flag
- `docs/numa_verification.md`: NUMA investigation log — hardware unavailable, software simulation decided

### Day 1 (documentation cleanup)
- `Agents.md`: Slimmed to ~160 lines — git rules, code standards, file map, team table
- `docs/math_foundations.md`: Extracted Ising/QUBO/QAOA/RQAOA math from `Agents.md`
- `src/rqaoa/README.md`: Module status, QUBO formula, config constants, test plan
- `src/scheduler/README.md`: Module status, task table, scheduler interface contract
- `src/executor/README.md`: Module status, NUMA binding details, function contracts
- `src/evaluation/README.md`: Module status, CSV schemas, plot function table, test plan
- `src/evaluation/graphs.py`: Added module docstring + typed, documented function stubs
- `main.py`: Replaced comment header with module docstring; `print()` → `logger`

---

## 📝 Recent Activity Log

- **2026-06-06**: Set up `.venv` under Python 3.10. Installed all core requirements. Created folder structure. Added `task_runner.py`, `main.py`, and all scheduler stubs.
- **2026-06-06**: Investigated NUMA fake node setup on AWS EC2. `CONFIG_NUMA_EMU` not compiled in Ubuntu 24.04/26.04 kernels. Decision: software latency simulation in `task_runner.py`. Details in `docs/numa_verification.md`.
- **2026-06-06**: Added `setup_env.sh` to enforce Python 3.10 requirement.
- **2026-06-06**: Documentation standardisation pass — `Agents.md` slimmed, math extracted, per-module READMEs created, `graphs.py` and `main.py` cleaned up to comply with code standards.
