# Module: `src/evaluation/`

**Purpose:** Compute scheduling quality metrics, define canonical CSV output schemas, and generate comparison plots for all scheduler results.

**Owner:** Vikas (P4)

---

## File Status

| File | Status | Description |
|------|--------|-------------|
| `__init__.py` | ✅ Exists (stub) | Empty module marker |
| `metrics.py` | 🔲 Schemas done; functions TODO Day 3 | CSV schemas defined; 4 metric functions stubbed |
| `graphs.py` | 🔲 TODO Day 4 | 3 plot function stubs — implement with matplotlib |

---

## `metrics.py` — Function Stubs

All functions have full docstrings and type hints. Implement on Day 3.

| Function | Signature | TODO Day |
|----------|-----------|----------|
| `calculate_avg_completion_time` | `(durations_s: List[float]) -> float` | 3 |
| `calculate_makespan` | `(start_times_s, end_times_s: List[float]) -> float` | 3 |
| `calculate_latency_cost` | `(memory_mb, sensitivity, tier: str) -> float` | 3 |
| `calculate_dram_utilization` | `(dram_usage_mb, dram_capacity_mb: float) -> float` | 3 |

**Latency cost formula** (consistent across all schedulers):
```
cost_i = memory_sensitivity_i × tier_latency_ns × memory_requirement_mb_i
```

Constants in `metrics.py` (must stay in sync with `src/scheduler/tasks.py`):
```python
DRAM_LATENCY_NS: float = 100.0
CXL_LATENCY_NS:  float = 300.0
```

---

## CSV Schemas

### `results/execution_log.csv` — One row per task execution

| Column | Type | Description |
|--------|------|-------------|
| `scheduler_name` | str | e.g. `"fcfs"`, `"rqaoa"` |
| `task_id` | int | 0–7 |
| `memory_requirement_mb` | float | MB allocated |
| `priority` | int | Task priority |
| `memory_sensitivity` | float | 0.0–1.0 |
| `assigned_node` | int | 0=DRAM, 1=CXL |
| `assigned_tier` | str | `"DRAM"` or `"CXL"` |
| `start_time_s` | float | Epoch timestamp |
| `end_time_s` | float | Epoch timestamp |
| `duration_s` | float | `end_time_s - start_time_s` |
| `latency_cost_ns` | float | `sensitivity × tier_latency × memory_mb` |

### `results/all_schedulers_summary.csv` — One row per scheduler

| Column | Type | Description |
|--------|------|-------------|
| `scheduler_name` | str | Scheduler identifier |
| `num_tasks` | int | Always 8 |
| `dram_tasks` | int | Count in DRAM |
| `cxl_tasks` | int | Count in CXL |
| `dram_usage_mb` | float | Total MB in DRAM |
| `cxl_usage_mb` | float | Total MB in CXL |
| `dram_utilization_pct` | float | `dram_usage_mb / 2048 × 100` |
| `avg_completion_time_s` | float | Mean task duration |
| `makespan_s` | float | `max(end) - min(start)` |
| `total_latency_cost_ns` | float | Sum across all tasks |
| `avg_latency_cost_ns` | float | Mean per task |

---

## `graphs.py` — Plot Functions (Day 4)

| Function | Plot Type | Output File |
|----------|-----------|-------------|
| `plot_latency_comparison(results)` | Bar chart — total latency cost per scheduler | `results/plots/latency_comparison.png` |
| `plot_makespan_comparison(results)` | Bar chart — makespan per scheduler | `results/plots/makespan_comparison.png` |
| `plot_utilization(results)` | Stacked bar — DRAM vs CXL tasks per scheduler | `results/plots/utilization.png` |

Additional plots (Day 4–5):
- Gantt-style task completion timeline
- Combined summary: all 4 schedulers × all 3 metrics

All plots saved to `results/plots/` with descriptive filenames, publication-quality
titles, axis labels, and legends. Use a consistent colour scheme across all plots.

---

## Tests

`tests/test_metrics.py` (Day 2–4):
- `calculate_latency_cost("DRAM")` returns sensitivity × 100 × memory_mb
- `calculate_latency_cost("CXL")` returns sensitivity × 300 × memory_mb
- Invalid tier raises `ValueError`
- `calculate_dram_utilization` with zero capacity raises `ValueError`
- `calculate_makespan` returns 0.0 for empty inputs
