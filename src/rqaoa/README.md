# Module: `src/rqaoa/`

**Purpose:** Quantum optimization engine. Builds the QUBO matrix, runs RQAOA via OpenQAOA, and parses the bitstring result into a task assignment.

**Owners:** Anjana (P1) — Primary | Hari (P2) — Secondary

---

## File Status

| File | Status | Description |
|------|--------|-------------|
| `__init__.py` | ✅ Exists | Exports public RQAOA helpers |
| `qubo_builder.py` | ✅ Done Day 2 | `build_qubo_from_tasks(tasks) -> np.ndarray` — builds 8×8 Q matrix |
| `rqaoa_runner.py` | 🔲 TODO Day 3 | `run_rqaoa_optimizer(qubo_matrix) -> list[int]` — runs RQAOA via OpenQAOA/Aer |
| `rqaoa_config.py` | 🔲 TODO Day 3 | Named constants: `RQAOA_LAYERS`, `RECURSIVE_CUTOFF`, `OPTIMIZER` |
| `result_parser.py` | ✅ Done Day 3 | `decode_bitstring(bitstring) -> dict[int, str]` — maps 8-bit result to `{task_id: "DRAM"/"CXL"}` |
| `qubo_converter.py` | ✅ Done Day 2 | Translates `qubo_builder` output to OpenQAOA-compatible QUBO dict format |

---

## QUBO Matrix Construction

The Q matrix is 8×8 (one variable per task). See `docs/math_foundations.md` for full derivation.

**Diagonal** (cost of assigning task $i$ to CXL):
```
Q[i][i] = sensitivity_i × (CXL_LATENCY_NS - DRAM_LATENCY_NS) × memory_mb_i
```

**Off-diagonal** (capacity constraint penalty — expanded from):
```
Penalty = P × (Σ (1 - x_i) × m_i  - DRAM_CAPACITY_MB)²
```

Constants are imported from `src/scheduler/tasks.py`:
- `DRAM_LATENCY_NS = 100.0`
- `CXL_LATENCY_NS = 300.0`
- `DRAM_CAPACITY_MB = 2048.0`

---

## RQAOA Configuration

| Constant | Default | Meaning |
|----------|---------|---------|
| `RQAOA_LAYERS` | `1` | QAOA circuit depth $p$ |
| `RECURSIVE_CUTOFF` | `3` | Switch to classical brute-force at this variable count |
| `OPTIMIZER` | `"COBYLA"` | Classical optimizer for QAOA parameter tuning |

---

## Expected Outputs

- `qubo_builder.py` → 8×8 `np.ndarray` + heatmap saved to `results/qubo_heatmap.png`
- `rqaoa_runner.py` → raw bitstring (e.g. `"10110010"`)
- `result_parser.py` → `{0: "DRAM", 1: "CXL", 2: "CXL", ...}`

---

## Tests

`tests/test_qubo_builder.py` (Day 2):
- Matrix shape is `(8, 8)`
- Diagonal values match formula
- Off-diagonal symmetry holds
- All values are finite floats

`tests/test_result_parser.py` (Day 3):
- Valid 8-bit strings decode correctly
- Malformed bitstrings raise `ValueError`
