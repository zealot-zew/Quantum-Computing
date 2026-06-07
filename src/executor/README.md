# Module: `src/executor/`

**Purpose:** OS-level task execution layer. Binds tasks to NUMA memory nodes using `numactl` and orchestrates concurrent subprocess execution.

**Owners:** Hari (P2) — Primary | Anjana (P1) — Secondary

---

## File Status

| File | Status | Description |
|------|--------|-------------|
| `__init__.py` | ✅ Exists (stub) | Empty module marker |
| `numa_executor.py` | 🔲 TODO Day 2 | `execute_with_numa_binding(task_cmd, numa_node)` — run single task via numactl |
| `task_orchestrator.py` | 🔲 TODO Day 2 | `run_all_tasks(assignment: dict[int, str])` — run all 8 tasks concurrently |

---

## NUMA Node Mapping

| Node ID | Tier | numactl flags |
|---------|------|---------------|
| `0` | DRAM | `--cpunodebind=0 --membind=0` |
| `1` | CXL | `--cpunodebind=1 --membind=1` |

> **⚠️ Hardware NUMA not available on AWS EC2** (Ubuntu kernel lacks `CONFIG_NUMA_EMU`).
> See `docs/numa_verification.md`. Software latency simulation in `task_runner.py` is the approved workaround.

---

## `numa_executor.py` Contract (Day 2)

```python
def execute_with_numa_binding(task_cmd: str, numa_node: int) -> int:
    """
    Run a shell command bound to a NUMA memory node.

    Falls back to unbounded execution if numactl is not found (macOS / non-NUMA Linux).

    Returns: subprocess return code
    """
```

Command template:
```bash
numactl --cpunodebind={node} --membind={node} -- python task_runner.py --task-id {id} --memory-mb {mb} --node {node}
```

Required error handling:
- `FileNotFoundError` → log warning, run without numactl
- `subprocess.CalledProcessError` → log error, re-raise

---

## `task_orchestrator.py` Contract (Day 2–3)

```python
def run_all_tasks(
    assignment: dict[int, str],
    tasks: list[Task],
    dry_run: bool = False,
) -> list[dict]:
    """
    Launch all 8 tasks as concurrent subprocesses with correct NUMA binding.

    Returns: list of per-task result dicts with keys:
        task_id, assigned_tier, start_time_s, end_time_s, duration_s, return_code
    """
```

- Use `subprocess.Popen` + `.wait()` for concurrency.
- Add `--dry-run` flag: print commands but don't execute.
- Collect per-task return codes and log any failures.

---

## Tests

`tests/test_numa_executor.py` (Day 2):
- Mock `subprocess.run` — verify correct numactl args for node 0 and node 1
- Verify `FileNotFoundError` fallback runs without numactl
- Verify failed subprocess logs and re-raises

`tests/test_task_orchestrator.py` (Day 3):
- `--dry-run` mode produces no subprocesses
- All 8 tasks launched and waited on
