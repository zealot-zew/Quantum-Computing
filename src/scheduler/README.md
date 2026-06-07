# Module: `src/scheduler/`

**Purpose:** Task data model and all classical scheduling algorithms that assign tasks to DRAM or CXL memory tiers.

**Owners:** Smarth (P3) — Primary | Vikas (P4) — Secondary

---

## File Status

| File | Status | Description |
|------|--------|-------------|
| `task_model.py` | ✅ Complete | `Task` dataclass with `__post_init__` validation |
| `tasks.py` | ✅ Complete | 8 canonical tasks + memory/latency constants |
| `__init__.py` | ✅ Complete | Exports all public symbols from the module |
| `fcfs_scheduler.py` | 🔲 TODO Day 2 | `FCFSScheduler` — assign in task_id order, DRAM first |
| `greedy_scheduler.py` | 🔲 TODO Day 2 | `GreedyScheduler` — sort by `memory_sensitivity` desc, DRAM first |
| `greedy_priority_scheduler.py` | 🔲 TODO Day 2 | `GreedyPriorityScheduler` — composite score: 0.5×priority + 0.5×sensitivity |
| `round_robin_scheduler.py` | 🔲 TODO Day 2 | `RoundRobinScheduler` — alternate DRAM/CXL assignment |
| `scheduler_interface.py` | 🔲 TODO Day 2 | `BaseScheduler` abstract base class (P5 task) |

---

## Task Data Model (`task_model.py`)

```python
@dataclass
class Task:
    task_id: int                  # Unique identifier (0–7)
    memory_requirement_mb: float  # Memory footprint in MB (must be > 0)
    priority: int                 # Higher = more urgent (must be >= 0)
    memory_sensitivity: float     # Latency sensitivity 0.0–1.0 (validated)
```

Validation in `__post_init__`: raises `ValueError` for invalid inputs.

---

## Canonical Task Set (`tasks.py`)

| task_id | memory_mb | priority | sensitivity | Notes |
|---------|-----------|----------|-------------|-------|
| 0 | 512 | 5 | 0.90 | High-priority, latency-critical |
| 1 | 256 | 3 | 0.70 | Medium |
| 2 | 1024 | 4 | 0.85 | Large footprint, sensitive |
| 3 | 128 | 2 | 0.40 | Small, tolerates CXL |
| 4 | 768 | 5 | 0.95 | Most latency-sensitive |
| 5 | 384 | 1 | 0.30 | Low priority, CXL-friendly |
| 6 | 640 | 4 | 0.80 | Large, sensitive |
| 7 | 192 | 3 | 0.50 | Medium |

**Total memory:** 3904 MB | **DRAM capacity:** 2048 MB | **CXL capacity:** 4096 MB

Key constants (import from `src.scheduler.tasks`):
```python
DRAM_CAPACITY_MB = 2048.0   # Simulated DRAM size
CXL_CAPACITY_MB  = 4096.0   # Simulated CXL size
DRAM_LATENCY_NS  = 100.0    # ~80–120 ns typical
CXL_LATENCY_NS   = 300.0    # ~200–400+ ns typical
```

---

## Scheduler Interface (Day 2)

All schedulers must implement:

```python
def schedule(self, tasks: List[Task]) -> Dict[int, str]:
    """Returns {task_id: "DRAM" | "CXL"} assignment."""

def compute_total_cost(self, tasks: List[Task], assignment: Dict[int, str]) -> float:
    """Returns total weighted latency cost (ns·MB)."""
```

Cost formula (consistent with `evaluation/metrics.py`):
```
cost_i = memory_sensitivity_i × tier_latency_ns × memory_requirement_mb_i
```

---

## Greedy Priority Scheduler Constants (`greedy_priority_scheduler.py`)

```python
PRIORITY_WEIGHT: float = 0.5     # Weight for normalized priority score
SENSITIVITY_WEIGHT: float = 0.5  # Weight for memory_sensitivity
MAX_PRIORITY: int = 5            # Used to normalize priority to [0, 1]

# Composite score:
score = PRIORITY_WEIGHT * (task.priority / MAX_PRIORITY) + SENSITIVITY_WEIGHT * task.memory_sensitivity
```

---

## Tests

`tests/test_schedulers.py` (Day 2–3):
- All 4 schedulers return assignments for all 8 tasks
- No DRAM overflow (sum of DRAM tasks ≤ 2048 MB)
- Edge cases: all tasks fit in DRAM; no tasks fit; identical sensitivity scores
