# Mathematical Foundations
## Quantum-Assisted Optimization Engine for CXL-Aware Hybrid Scheduling

> **Who should read this:** Anyone writing quantum code (`src/rqaoa/`).
> Classical scheduler contributors can skip this file.
>
> For agent onboarding rules, code standards, and file map → see `Agents.md`.

---

## Part 1: The Ising Model

The **Ising model** is the mathematical language quantum hardware "speaks."
All quantum optimization problems are ultimately expressed in this form.

### Variables

A system of $N$ discrete **spin variables**:
$$s_i \in \{+1, -1\} \quad \text{for } i = 1, 2, \ldots, N$$

$s_i = +1$ → spin-up &nbsp;|&nbsp; $s_i = -1$ → spin-down.

### Energy Function (Hamiltonian)

$$E(\mathbf{s}) = \sum_{i=1}^{N} h_i s_i + \sum_{i < j}^{N} J_{ij} \, s_i s_j$$

| Term | Symbol | Meaning |
|------|--------|---------|
| Linear bias | $h_i$ | External magnetic field on spin $i$ (independent task cost) |
| Quadratic coupler | $J_{ij}$ | Coupling between spins $i$ and $j$ (task interaction cost) |

**Goal:** Find $\mathbf{s}^*$ that **minimises** $E(\mathbf{s})$ — the ground state.

---

## Part 2: The QUBO Formulation

QUBO (Quadratic Unconstrained Binary Optimization) is the Ising model
re-expressed with binary variables.

### Variables

$$x_i \in \{0, 1\} \quad \text{for } i = 1, 2, \ldots, N$$

In this project:
- $x_i = 0$ → **Task $i$ assigned to DRAM (Node 0)**
- $x_i = 1$ → **Task $i$ assigned to CXL memory (Node 1)**

### QUBO Objective Function

$$f(\mathbf{x}) = \sum_{i \leq j} Q_{ij} \, x_i x_j = \mathbf{x}^T Q \mathbf{x}$$

- $Q$ is an upper-triangular $N \times N$ matrix.
- **Diagonal** $Q_{ii}$: individual cost of assigning task $i$ to CXL.
- **Off-diagonal** $Q_{ij}$: penalty when both task $i$ and $j$ go to the same (CXL) node.

**Goal:** Find $\mathbf{x}^* = \arg\min_{\mathbf{x}} f(\mathbf{x})$.

### Ising ↔ QUBO Mapping

$$s_i = 2x_i - 1 \quad \iff \quad x_i = \frac{s_i + 1}{2}$$

### Building the Q Matrix

For 8 tasks with memory requirements $m_i$ (MB):

**Latency Cost Term** (diagonal — assign sensitive tasks to DRAM):
$$Q_{ii} = \lambda_i \cdot (\text{CXL\_LATENCY\_NS} - \text{DRAM\_LATENCY\_NS}) \cdot m_i$$

where $\lambda_i$ is `memory_sensitivity` of task $i$ (0–1).

**Capacity Constraint Penalty** (off-diagonal — DRAM must not overflow):
$$\text{Penalty} = P \cdot \left(\sum_{i} (1 - x_i) \cdot m_i - C_{\text{DRAM}}\right)^2$$

Expanding this polynomial generates $Q_{ij}$ for $i \neq j$, encoding the
constraint that DRAM-assigned tasks must fit within capacity $C_{\text{DRAM}}$.

---

## Part 3: QAOA

QAOA (Quantum Approximate Optimization Algorithm) finds the minimum of the QUBO
by encoding it as a quantum Hamiltonian and using a parameterised quantum circuit.

### The Two Hamiltonians

**Cost Hamiltonian $H_C$** — encodes the QUBO:
$$H_C = \sum_{i \leq j} Q_{ij} \, Z_i Z_j$$
where $Z_i$ is the Pauli-Z operator on qubit $i$.
Ground state of $H_C$ = optimal QUBO solution.

**Mixer Hamiltonian $H_B$** — drives quantum exploration:
$$H_B = \sum_{i=1}^{N} X_i$$
where $X_i$ is the Pauli-X (bit-flip) operator on qubit $i$.

### The QAOA Circuit

With $p$ layers:
$$|\psi(\gamma, \beta)\rangle = \prod_{k=1}^{p} e^{-i\beta_k H_B} \cdot e^{-i\gamma_k H_C} \, |+\rangle^{\otimes N}$$

Parameters $(\gamma, \beta)$ are tuned by a classical optimizer (COBYLA) to minimise:
$$\langle \psi(\gamma, \beta) | H_C | \psi(\gamma, \beta) \rangle$$

The circuit is measured to get a bitstring → QUBO assignment.

### Why Standard QAOA Is Insufficient

Fixed-depth QAOA can only capture correlations within a bounded graph distance.
For dense 8-task problems, it gets trapped in local optima → need RQAOA.

---

## Part 4: RQAOA (Recursive QAOA)

RQAOA fixes the locality problem by iteratively eliminating variables based on
quantum correlations learned at each step.

### Algorithm

**Input:** QUBO with $n$ variables, threshold size $n_{\text{thresh}}$.

**Repeat until** $|\text{remaining variables}| \leq n_{\text{thresh}}$:

1. **Quantum Step:** Run QAOA on current Hamiltonian $H^{(k)}$.
   Measure two-qubit correlations:
   $$M_{ij} = \langle \psi(\gamma^*, \beta^*) | Z_i Z_j | \psi(\gamma^*, \beta^*) \rangle$$

2. **Strongest Correlation:**
   $$(i^*, j^*) = \arg\max_{i < j} |M_{ij}|$$

3. **Eliminate:**
   - $M_{i^*j^*} > 0$ → fix $s_{i^*} = s_{j^*}$ (same memory node)
   - $M_{i^*j^*} < 0$ → fix $s_{i^*} = -s_{j^*}$ (opposite memory nodes)

4. **Substitute:** Replace $s_{j^*}$ in $H^{(k)}$ with $\pm s_{i^*}$, yielding
   $H^{(k+1)}$ with one fewer variable.

**Terminate:** Solve $H^{(n_{\text{thresh}})}$ exactly via classical enumeration.

**Reconstruct:** Walk back through eliminated relationships to get full $n$-variable solution.

### Why It Works

Each step extracts genuine quantum information about variable relationships and uses
it to shrink the search space. The final solution inherits the full quantum-informed
structure, making RQAOA consistently better than fixed-depth QAOA on dense problems.

---

## Key Constants (sync with `src/scheduler/tasks.py`)

| Constant | Value | Meaning |
|----------|-------|---------|
| `DRAM_LATENCY_NS` | 100 ns | Local DRAM baseline latency |
| `CXL_LATENCY_NS` | 300 ns | CXL-attached memory latency |
| `DRAM_CAPACITY_MB` | 2048 MB | Simulated DRAM capacity |
| `CXL_CAPACITY_MB` | 4096 MB | Simulated CXL capacity |
| `RQAOA_LAYERS` (p) | 1 (default) | QAOA circuit depth |
| `RECURSIVE_CUTOFF` | 3 | Variables remaining when switching to classical |
