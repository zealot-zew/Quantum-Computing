# Agents.md — Project Intelligence File
## Quantum-Assisted Optimization Engine for CXL-Aware Hybrid Scheduling

> **Read this file first.** It tells you the rules, the file map, and the current project state.
> Quantum math (Ising, QUBO, QAOA, RQAOA) → `docs/math_foundations.md`.
> Sprint tasks and day-by-day goals → `Team_Sprint_5People_7Days.md`.

---

## 👥 Team & Ownership

| Person | Role | Owns |
|--------|------|------|
| **Anjana** (P1) | Quantum Algo + Infra | `src/rqaoa/`, QUBO math, IBM Quantum |
| **Hari** (P2) | Infra + Quantum Algo | `task_runner.py`, `src/executor/`, RQAOA config |
| **Smarth** (P3) | Classical Scheduler + Simulation | `src/scheduler/` (FCFS, RR, Greedy), latency injection |
| **Vikas** (P4) | Evaluation + Classical Scheduler | `src/evaluation/`, `greedy_priority_scheduler.py`, plots |
| **Devandra** (P5) | Docs + Integration Lead | `main.py`, `README.md`, `report.md`, daily merges |

---

## 📁 Quick File Map

Every file in the project — one line each. Read only what you need.

```
quantum-cxl-scheduler/
│
├── main.py                          # CLI entry point (--scheduler flag). Scaffold — wire Day 5.
├── task_runner.py                   # Subprocess worker: --task-id --memory-mb --node. Expand Day 2–3.
├── requirements.txt                 # All Python dependencies
├── setup_env.sh                     # Enforces Python 3.10 for openqaoa compatibility
├── progress_summary.md              # ⭐ Master status log — update after every session
│
├── src/
│   ├── rqaoa/                       # Quantum optimizer — see src/rqaoa/README.md
│   │   └── __init__.py              # Stub only. Files to add: qubo_builder.py, rqaoa_runner.py, result_parser.py
│   │
│   ├── scheduler/                   # Classical schedulers — see src/scheduler/README.md
│   │   ├── task_model.py            # ✅ Task dataclass with validation
│   │   ├── tasks.py                 # ✅ 8 canonical tasks + DRAM/CXL constants
│   │   ├── fcfs_scheduler.py        # 🔲 Stub — implement Day 2
│   │   ├── greedy_scheduler.py      # 🔲 Stub — implement Day 2
│   │   ├── greedy_priority_scheduler.py  # 🔲 Stub with composite score formula — implement Day 2
│   │   ├── round_robin_scheduler.py # 🔲 Stub — implement Day 2
│   │   └── __init__.py              # ✅ Exports all public symbols
│   │
│   ├── executor/                    # OS-level execution — see src/executor/README.md
│   │   └── __init__.py              # Stub only. Files to add: numa_executor.py, task_orchestrator.py
│   │
│   └── evaluation/                  # Metrics & plots — see src/evaluation/README.md
│       ├── metrics.py               # ✅ CSV schemas defined + function stubs (implement Day 3)
│       ├── graphs.py                # 🔲 Plot function stubs (implement Day 4)
│       └── __init__.py              # Stub only
│
├── tests/                           # Empty — add test files per module starting Day 2
│
├── docs/
│   ├── math_foundations.md          # ⭐ Full Ising/QUBO/QAOA/RQAOA math — read before touching rqaoa/
│   ├── numa_verification.md         # NUMA investigation: hardware NUMA unavailable; using software simulation
│   └── p3_day1_verification.md      # P3 (Smarth) Day 1 environment verification log
│
└── results/                         # Output directory — CSVs and plots go here (created, empty)
```

---

## 🌿 Git Rules (MANDATORY)

1. **Never commit or push without explicit user permission.**
2. **Never commit to `main` or `master`.** Always use a feature branch:
   ```bash
   git checkout -b feature/<short-description>
   # e.g. feature/qubo-matrix-builder, fix/numa-binding-bug
   ```
3. Verify your branch before writing code: `git branch`
4. Before pushing, all checks must pass:
   ```bash
   python -m pytest tests/
   python -m flake8 src/ --max-line-length=100
   python -m mypy src/
   ```
5. Push to your feature branch only: `git push origin feature/<name>`
6. Never force-push to shared branches.
7. Commit messages follow Conventional Commits:
   ```
   feat(qubo): add penalty term for DRAM capacity constraint
   fix(executor): handle numactl fallback for non-Linux systems
   docs(readme): add RQAOA algorithm overview
   ```
8. **Update `progress_summary.md`** after every completed task.

---

## 🧼 Code Standards

### Naming

| Context | Convention | Example |
|---------|-----------|---------|
| Variables / Functions | `snake_case` | `qubo_matrix`, `run_rqaoa` |
| Classes | `PascalCase` | `QuantumScheduler` |
| Constants | `SCREAMING_SNAKE` | `DRAM_LATENCY_NS = 100` |
| Private methods | `_leading_underscore` | `_build_hamiltonian()` |

### Non-Negotiables

- **Type hints on every function signature** — no exceptions.
- **Google-style docstring on every public function and class.**
- **No magic numbers** — use named constants defined at module top.
- **No `print()` in production code** — use `logging.getLogger(__name__)`.
- **Single Responsibility Principle** — if you need "and" to describe a function, split it.
- **Comments explain WHY, not what** — the code explains what.

### Error Handling Pattern

```python
import logging
logger = logging.getLogger(__name__)

try:
    result = subprocess.run(cmd, check=True)
except FileNotFoundError:
    logger.warning("numactl not found. Falling back to unbounded execution.")
except subprocess.CalledProcessError as e:
    logger.error(f"Task failed: {e.stderr}")
    raise
```

---

## ✅ Pre-Commit Checklist

- [ ] On a feature branch (not `main`)
- [ ] All tests pass: `pytest tests/`
- [ ] No linting errors: `flake8 src/ --max-line-length=100`
- [ ] Type hints correct: `mypy src/`
- [ ] No hardcoded secrets or credentials
- [ ] All new functions have docstrings and type hints
- [ ] No magic numbers — constants are named
- [ ] Commit message follows Conventional Commits format
- [ ] `progress_summary.md` updated

---

## 📄 Progress Summary Format

`progress_summary.md` must follow this structure (keep it current):

```markdown
# Project Progress Summary

## 📌 Active Context
- **Current Branch:** `feature/<name>`
- **Latest Update:** YYYY-MM-DD
- **Active Developer/Agent:** <name>

## 🚀 Active Goals & Roadmap
- [ ] Pending goal
- [x] Completed goal

## 📊 Module Status
| Module | Status | Notes |
|--------|--------|-------|
| src/rqaoa/ | 🔲 Stub | ... |

## 📁 Files Created or Modified
- `path/to/file.py`: What changed

## 📝 Recent Activity Log
- **YYYY-MM-DD**: What was done
```

---

## 🔗 Key References

| Document | Purpose |
|----------|---------|
| `docs/math_foundations.md` | Full Ising/QUBO/QAOA/RQAOA math |
| `Team_Sprint_5People_7Days.md` | Day-by-day sprint plan with checkboxes |
| `docs/numa_verification.md` | Why hardware NUMA is unavailable; software simulation decision |
| `progress_summary.md` | Current project state (always up to date) |
| `src/*/README.md` | Per-module file map, status, and owner |
