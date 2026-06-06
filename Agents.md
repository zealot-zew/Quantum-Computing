# CLAUDE.md — Project Intelligence File
## Quantum-Assisted Optimization Engine for CXL-Aware Hybrid Scheduling

> This file instructs the AI assistant on how to write code, explain mathematics,
> and manage git contributions for this project. Read this file before every session.

---

## 🌿 Git Workflow Rules (MANDATORY — Never Break These)

These rules apply to **every single change**, no matter how small:

1. **Never commit or push without user permission.**
   You must NEVER run `git commit` or `git push` without obtaining explicit, written permission from the user first.

2. **Never commit directly to `main` or `master`.**
   Always create a new feature branch before making any changes:
   ```bash
   git checkout -b feature/<short-description>
   # Examples:
   # git checkout -b feature/qubo-matrix-builder
   # git checkout -b feature/rqaoa-integration
   # git checkout -b fix/numa-binding-bug
   ```

3. **Work only on the current branch.**
   Verify you are on the correct branch before writing code:
   ```bash
   git branch   # confirm active branch
   ```

4. **Verify before pushing.**
   Before pushing to remote, always run:
   ```bash
   python -m pytest tests/          # run all tests
   python -m flake8 src/            # check for linting errors
   python -m mypy src/              # check type hints
   ```
   Only push if all checks pass.

5. **Push to the feature branch only.**
   ```bash
   git push origin feature/<short-description>
   ```

6. **Never force-push to shared branches.**
   Force-push is allowed only on your own local feature branches before a first push.

7. **Write clear, conventional commit messages.**
   Follow the Conventional Commits format:
   ```
   <type>(<scope>): <short summary>

   [optional body]
   ```
   Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`

   Examples:
   ```
   feat(qubo): add penalty term for DRAM capacity constraint
   fix(executor): handle numactl fallback for non-Linux systems
   docs(readme): add RQAOA algorithm overview
   ```

8. **Maintain a single Progress Summary Document (MANDATORY)**
   Instead of writing separate branch summaries, maintain a single file named `progress_summary.md` in the root of the project. This file serves as the unified status log for the project, enabling seamless collaboration with other AI instances across different chat threads. Update this file whenever tasks are completed or goals change.

---

## 🧼 Clean Code Standards

### Core Philosophy
> "Code is read far more often than it is written." — Guido van Rossum

Every line of code written in this project must be **clear, explicit, and purposeful**.

---

### 1. Naming Conventions

Use **descriptive, self-explaining names**. Never use single-letter variables outside of well-understood mathematical loops.

```python
# ❌ BAD
def calc(t, m, l):
    return t * l * m

# ✅ GOOD
def calculate_memory_access_cost(
    task_count: int,
    memory_requirement_mb: float,
    latency_ns: float
) -> float:
    """Returns the total memory access cost in nanosecond-megabyte units."""
    return task_count * latency_ns * memory_requirement_mb
```

| Context              | Convention         | Example                     |
|----------------------|--------------------|-----------------------------|
| Variables/Functions  | `snake_case`       | `qubo_matrix`, `run_rqaoa`  |
| Classes              | `PascalCase`       | `QuantumScheduler`          |
| Constants            | `SCREAMING_SNAKE`  | `DRAM_LATENCY_NS = 100`     |
| Private methods      | `_leading_underscore` | `_build_hamiltonian()`   |

---

### 2. Functions: Single Responsibility Principle (SRP)

Every function must do **exactly one thing**. If you need the word "and" to describe it, split it.

```python
# ❌ BAD — does too many things
def run_scheduler(tasks):
    qubo = build_qubo(tasks)
    result = run_rqaoa(qubo)
    bind_to_numa(result)
    measure_latency()
    print(result)

# ✅ GOOD — each function is focused
def build_qubo_from_tasks(tasks: list[Task]) -> np.ndarray:
    """Constructs a QUBO matrix from a list of Task objects."""
    ...

def run_rqaoa_optimizer(qubo_matrix: np.ndarray) -> list[int]:
    """Runs the RQAOA algorithm and returns a bitstring assignment."""
    ...

def bind_tasks_to_memory_nodes(assignment: list[int], tasks: list[Task]) -> None:
    """Uses numactl to bind each task to its assigned memory node."""
    ...
```

---

### 3. Type Hints (Mandatory)

Every function signature must include type hints. They serve as built-in documentation and help IDEs catch bugs early.

```python
from dataclasses import dataclass
import numpy as np

@dataclass
class Task:
    task_id: int
    memory_requirement_mb: float
    priority: int
    memory_sensitivity: float   # 0.0 (insensitive) to 1.0 (highly sensitive)

def assign_tasks_to_memory(
    tasks: list[Task],
    qubo_result: list[int],
    dram_node: int = 0,
    cxl_node: int = 1
) -> dict[int, int]:
    """
    Maps each task_id to a NUMA memory node.

    Args:
        tasks: List of Task objects to schedule.
        qubo_result: Bitstring output from RQAOA (0=DRAM, 1=CXL).
        dram_node: The NUMA node ID representing local DRAM.
        cxl_node: The NUMA node ID representing CXL-attached memory.

    Returns:
        A dict mapping task_id -> numa_node_id.
    """
    return {
        task.task_id: (cxl_node if bit == 1 else dram_node)
        for task, bit in zip(tasks, qubo_result)
    }
```

---

### 4. No Magic Numbers — Use Named Constants

```python
# ❌ BAD
if latency > 150:
    assign_to_cxl(task)

# ✅ GOOD
DRAM_LATENCY_NS: int = 100      # Local DRAM baseline latency
CXL_LATENCY_NS: int = 300       # CXL-attached memory latency
LATENCY_TIER_THRESHOLD_NS: int = 150  # Above this → CXL tier

if latency > LATENCY_TIER_THRESHOLD_NS:
    assign_to_cxl(task)
```

---

### 5. Comments Explain WHY, Not WHAT

The code explains *what* it does. Comments explain *why* you made a choice.

```python
# ❌ BAD comment — just restating the code
# multiply tasks by latency
cost = num_tasks * latency_ns

# ✅ GOOD comment — explains the reasoning
# The penalty is quadratic in task count because as more tasks compete for
# the same memory node, contention grows non-linearly (cache thrashing effect).
cost = (num_tasks ** 2) * latency_ns * CONTENTION_SCALING_FACTOR
```

---

### 6. Error Handling and Logging

Never use bare `print()` statements in production code. Use the `logging` module.

```python
import logging
import subprocess

logger = logging.getLogger(__name__)

def execute_with_numa_binding(task_cmd: str, numa_node: int) -> int:
    """Executes a task command bound to a specific NUMA node."""
    try:
        cmd = ["numactl", f"--membind={numa_node}", "--", *task_cmd.split()]
        logger.info(f"Binding task to NUMA node {numa_node}: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        logger.debug(f"Task stdout: {result.stdout}")
        return result.returncode
    except FileNotFoundError:
        logger.warning("numactl not found. Falling back to unbounded execution.")
        result = subprocess.run(task_cmd.split(), capture_output=True, text=True)
        return result.returncode
    except subprocess.CalledProcessError as e:
        logger.error(f"Task execution failed: {e.stderr}")
        raise
```

---

### 7. Project Structure

Maintain the following structure. Every module must have a clear, single purpose:

```
quantum-cxl-scheduler/
├── src/
│   ├── rqaoa/          # Quantum optimization engine
│   │   ├── __init__.py
│   │   ├── qubo_builder.py     # Converts tasks → QUBO matrix
│   │   ├── rqaoa_runner.py     # Runs RQAOA via OpenQAOA
│   │   └── result_parser.py   # Parses bitstring output
│   ├── scheduler/      # Interprets RQAOA output
│   │   ├── __init__.py
│   │   └── task_mapper.py     # Maps tasks to memory tiers
│   ├── executor/       # OS-level execution layer
│   │   ├── __init__.py
│   │   └── numa_executor.py   # Runs tasks via numactl
│   └── evaluation/     # Metrics collection
│       ├── __init__.py
│       └── metrics.py         # Latency/throughput measurement
├── tests/
│   ├── test_qubo_builder.py
│   ├── test_task_mapper.py
│   └── test_numa_executor.py
├── results/            # Output CSVs, plots, logs
├── notebooks/          # Jupyter notebooks for exploration
├── main.py
├── requirements.txt
└── CLAUDE.md           # This file
```

---

## 📐 The Deep Mathematics

This section contains the complete mathematical foundations of the project.
Study this before writing any quantum code.

---

### Part 1: The Ising Model

The **Ising model** is a model from statistical physics used to study ferromagnetism.
It is the mathematical language that quantum hardware "speaks," and all quantum
optimization problems are ultimately expressed in this form.

#### Variables
A system of $N$ discrete **spin variables**:
$$s_i \in \{+1, -1\} \quad \text{for } i = 1, 2, \ldots, N$$

Think of $s_i = +1$ as spin-up and $s_i = -1$ as spin-down.

#### The Energy Function (Hamiltonian)
The total energy of a spin configuration is:
$$E(\mathbf{s}) = \sum_{i=1}^{N} h_i s_i + \sum_{i < j}^{N} J_{ij} \, s_i s_j$$

| Term | Symbol | Meaning |
|------|--------|---------|
| Linear bias | $h_i$ | External magnetic field on spin $i$ (independent influence on each task) |
| Quadratic coupler | $J_{ij}$ | Coupling strength between spins $i$ and $j$ (how much tasks influence each other) |

**Goal:** Find the spin configuration $\mathbf{s}^*$ that **minimizes** $E(\mathbf{s})$.
This lowest-energy state is called the **ground state**.

---

### Part 2: The QUBO Formulation

QUBO (Quadratic Unconstrained Binary Optimization) is the same problem as the Ising
model, but rewritten using binary variables instead of spin variables.

#### Variables
Instead of $s_i \in \{+1, -1\}$, QUBO uses:
$$x_i \in \{0, 1\} \quad \text{for } i = 1, 2, \ldots, N$$

In this project:
- $x_i = 0$ means **Task $i$ is assigned to DRAM (Node 0)**
- $x_i = 1$ means **Task $i$ is assigned to CXL memory (Node 1)**

#### The QUBO Objective Function
$$f(\mathbf{x}) = \sum_{i \leq j} Q_{ij} \, x_i x_j = \mathbf{x}^T Q \mathbf{x}$$

- $Q$ is an upper-triangular $N \times N$ matrix.
- **Diagonal elements** $Q_{ii}$: the individual "cost" of assigning task $i$ to CXL.
- **Off-diagonal elements** $Q_{ij}$: the "interaction penalty" when both task $i$ and task $j$ are assigned to the same (often CXL) node simultaneously.

**Goal:** Find the binary vector $\mathbf{x}^* = \arg\min_{\mathbf{x}} f(\mathbf{x})$.

#### The Mapping Between Ising and QUBO
The two models are mathematically equivalent via a linear substitution:
$$s_i = 2x_i - 1 \quad \iff \quad x_i = \frac{s_i + 1}{2}$$

This means any QUBO problem can be solved on quantum hardware that understands the
Ising model, and vice versa.

#### Building the Q Matrix for This Project

For 8 tasks with memory requirements $m_i$ (MB), the objective is to minimize total
latency cost while keeping DRAM capacity within its limit.

**Latency Cost Term:** Assign high-sensitivity tasks to DRAM (low latency):
$$Q_{ii} = \lambda_i \cdot (\text{CXL\_LATENCY\_NS} - \text{DRAM\_LATENCY\_NS}) \cdot m_i$$

where $\lambda_i$ is the memory sensitivity of task $i$ (0 to 1).

**Capacity Constraint Penalty:** If total DRAM usage exceeds capacity $C_{DRAM}$,
add a large penalty term $P$:
$$\text{Penalty} = P \cdot \left(\sum_{i} (1 - x_i) \cdot m_i - C_{DRAM}\right)^2$$

Expanding this polynomial generates additional $Q_{ij}$ terms for $i \neq j$,
which encode the constraint that tasks sharing DRAM must fit within capacity.

---

### Part 3: QAOA (Quantum Approximate Optimization Algorithm)

QAOA is the quantum algorithm that finds the minimum of the QUBO function by
encoding it as a quantum Hamiltonian and using a parameterized quantum circuit.

#### The Two Hamiltonians

**1. The Cost Hamiltonian $H_C$**
Encodes the QUBO objective. For each pair $(i, j)$ in the QUBO matrix:
$$H_C = \sum_{i \leq j} Q_{ij} \, Z_i Z_j$$
where $Z_i$ is the Pauli-Z operator acting on qubit $i$.
The ground state of $H_C$ corresponds to the optimal QUBO solution.

**2. The Mixer Hamiltonian $H_B$**
Drives quantum exploration across solutions:
$$H_B = \sum_{i=1}^{N} X_i$$
where $X_i$ is the Pauli-X (bit-flip) operator on qubit $i$.

#### The QAOA Circuit
The parameterized quantum state is prepared with $p$ layers:
$$|\psi(\gamma, \beta)\rangle = \prod_{k=1}^{p} e^{-i\beta_k H_B} \cdot e^{-i\gamma_k H_C} \, |+\rangle^{\otimes N}$$

The parameters $\gamma = (\gamma_1, \ldots, \gamma_p)$ and $\beta = (\beta_1, \ldots, \beta_p)$
are tuned by a classical optimizer to minimize:
$$\langle \psi(\gamma, \beta) | H_C | \psi(\gamma, \beta) \rangle$$

The circuit is then measured to get a bitstring, which corresponds to a QUBO assignment.

#### The Limitation of QAOA (Why We Need RQAOA)
Standard QAOA with a fixed depth $p$ can only "see" correlations between qubits
within a certain graph distance. For dense, highly interconnected problems (like
scheduling 8 tasks with many dependencies), it gets stuck in local optima.

---

### Part 4: RQAOA (Recursive QAOA)

RQAOA fixes the locality problem of QAOA by iteratively eliminating variables
based on the quantum correlations the circuit reveals at each step.

#### The Algorithm (Step-by-Step)

**Input:** A QUBO problem with $n$ variables, a threshold size $n_{thresh}$.

**Loop until** $|\text{remaining variables}| \leq n_{thresh}$:

1. **Quantum Step:** Run QAOA on the current Hamiltonian $H^{(k)}$ with $n^{(k)}$ variables.
   Measure the expectation values of all two-qubit correlations:
   $$M_{ij} = \langle \psi(\gamma^*, \beta^*) | Z_i Z_j | \psi(\gamma^*, \beta^*) \rangle$$

2. **Identify Strongest Correlation:**
   Find the pair $(i^*, j^*)$ with the largest $|M_{i^*j^*}|$:
   $$( i^*, j^* ) = \arg\max_{i < j} |M_{ij}|$$

3. **Elimination:**
   - If $M_{i^*j^*} > 0$ (positive correlation): fix $s_{i^*} = s_{j^*}$.
     These two tasks "want to be" on the same memory node.
   - If $M_{i^*j^*} < 0$ (anti-correlation): fix $s_{i^*} = -s_{j^*}$.
     These two tasks "want to be" on opposite memory nodes.

4. **Substitution:**
   Replace all occurrences of $s_{j^*}$ in $H^{(k)}$ with $\pm s_{i^*}$,
   yielding a new, reduced Hamiltonian $H^{(k+1)}$ with $n^{(k+1)} = n^{(k)} - 1$ variables.

**Termination:** Solve $H^{(n_{thresh})}$ exactly using classical enumeration.

**Reconstruction:** Walk back through all eliminated variable relationships to
reconstruct the full $n$-variable solution.

#### Why It Works
Each recursive step "learns" something from the quantum hardware about how variables
are related. It uses this quantum information to reduce the search space intelligently,
eventually reaching a problem size small enough for a classical computer to solve
perfectly. The final solution inherits all the quantum-informed structure.

---

## 🛠️ Tooling and Environment Setup

```bash
# 1. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate       # macOS/Linux
# .venv\Scripts\activate        # Windows

# 2. Install all dependencies
pip install -r requirements.txt

# 3. Check code style before committing
python -m flake8 src/ --max-line-length=100
python -m mypy src/

# 4. Run tests
python -m pytest tests/ -v
```

### `requirements.txt`
```
openqaoa
qiskit
qiskit-aer
pyqubo
networkx
numpy
matplotlib
scipy
pytest
flake8
mypy
black
```

---

## ✅ Pre-Commit Checklist

Before every `git push`, verify all of the following:

- [ ] All tests pass: `pytest tests/`
- [ ] No linting errors: `flake8 src/`
- [ ] Type hints are correct: `mypy src/`
- [ ] No hardcoded secrets or credentials in the code
- [ ] Constants are named and documented
- [ ] All new functions have docstrings
- [ ] Commit message follows Conventional Commits format
- [ ] You are on a feature branch, **not** `main` or `master`
- [ ] Progress summary file `progress_summary.md` has been updated in the root directory

---

## 📄 Progress Summary Document

To enable collaboration with AI assistants in multiple chats/sessions, the project maintains a single `progress_summary.md` file in the root directory. This acts as the shared state and audit log for all work done.

### 📋 Required Template

The `progress_summary.md` file must follow this structure:

```markdown
# Project Progress Summary

## 📌 Active Context
- **Current Branch:** `feature/<branch-name>`
- **Latest Update:** YYYY-MM-DD
- **Active Developer/Agent:** <name>

## 🚀 Active Goals & Roadmap
- [ ] Active Task / Goal 1
- [x] Completed Task / Goal 2

## 📁 Files Created or Modified
- `path/to/file.py`: Description of changes

## 📝 Recent Activity Log
- **YYYY-MM-DD**: Brief description of what was completed.
```
