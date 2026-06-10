"""
Comprehensive edge-case unit tests for all classical schedulers.

Tests cover:
- All tasks fit in DRAM
- No tasks fit in DRAM (all go to CXL)
- Tasks with identical sensitivity scores
- Exact capacity boundaries
- Single task scenarios
- Zero sensitivity tasks
- Cost computation edge cases

Maintained by: Smarth (P3 — Classical Scheduler + Simulation)
"""

import pytest
from src.scheduler.task_model import Task
from src.scheduler.fcfs_scheduler import FCFSScheduler
from src.scheduler.round_robin_scheduler import RoundRobinScheduler
from src.scheduler.greedy_scheduler import GreedyScheduler
from src.scheduler.greedy_priority_scheduler import GreedyPriorityScheduler


# Test constants
DRAM_CAPACITY_MB = 3072.0  # 3 GB
CXL_CAPACITY_MB = 5120.0   # 5 GB
TOTAL_CAPACITY_MB = DRAM_CAPACITY_MB + CXL_CAPACITY_MB


class TestAllTasksFitInDRAM:
    """Test scenarios where all tasks can fit in DRAM."""

    def test_fcfs_all_dram(self):
        """FCFS: When total memory < DRAM capacity, all tasks go to DRAM."""
        tasks = [
            Task(task_id=0, memory_requirement_mb=500.0, priority=3, memory_sensitivity=0.8),
            Task(task_id=1, memory_requirement_mb=600.0, priority=2, memory_sensitivity=0.5),
            Task(task_id=2, memory_requirement_mb=400.0, priority=1, memory_sensitivity=0.3),
        ]
        # Total: 1500 MB < 3072 MB DRAM
        
        scheduler = FCFSScheduler(DRAM_CAPACITY_MB, CXL_CAPACITY_MB)
        assignment = scheduler.schedule(tasks)
        
        assert all(tier == "DRAM" for tier in assignment.values())
        assert len(assignment) == 3
        cost = scheduler.compute_total_cost(tasks, assignment)
        assert cost == 0.0  # All in DRAM → zero cost

    def test_greedy_all_dram(self):
        """Greedy: All tasks in DRAM when total < DRAM capacity."""
        tasks = [
            Task(task_id=0, memory_requirement_mb=1000.0, priority=1, memory_sensitivity=0.2),
            Task(task_id=1, memory_requirement_mb=1000.0, priority=2, memory_sensitivity=0.9),
        ]
        # Total: 2000 MB < 3072 MB DRAM
        
        scheduler = GreedyScheduler(DRAM_CAPACITY_MB, CXL_CAPACITY_MB)
        assignment = scheduler.schedule(tasks)
        
        assert all(tier == "DRAM" for tier in assignment.values())
        cost = scheduler.compute_total_cost(tasks, assignment)
        assert cost == 0.0


class TestNoTasksFitInDRAM:
    """Test scenarios where no tasks can fit in DRAM."""

    def test_fcfs_all_cxl(self):
        """FCFS: Tiny DRAM → all tasks overflow to CXL."""
        tiny_dram_mb = 100.0
        large_cxl_mb = 10000.0
        
        tasks = [
            Task(task_id=0, memory_requirement_mb=500.0, priority=1, memory_sensitivity=0.5),
            Task(task_id=1, memory_requirement_mb=600.0, priority=2, memory_sensitivity=0.7),
        ]
        
        scheduler = FCFSScheduler(tiny_dram_mb, large_cxl_mb)
        assignment = scheduler.schedule(tasks)
        
        assert all(tier == "CXL" for tier in assignment.values())
        cost = scheduler.compute_total_cost(tasks, assignment)
        assert cost > 0  # CXL tasks have cost

    def test_round_robin_minimal_dram(self):
        """Round Robin: With tiny DRAM, most tasks go to CXL."""
        tiny_dram_mb = 50.0
        
        tasks = [
            Task(task_id=0, memory_requirement_mb=200.0, priority=1, memory_sensitivity=0.4),
            Task(task_id=1, memory_requirement_mb=200.0, priority=2, memory_sensitivity=0.6),
            Task(task_id=2, memory_requirement_mb=200.0, priority=3, memory_sensitivity=0.8),
        ]
        
        scheduler = RoundRobinScheduler(tiny_dram_mb, CXL_CAPACITY_MB)
        assignment = scheduler.schedule(tasks)
        
        # All 200 MB tasks can't fit in 50 MB DRAM
        cxl_count = sum(1 for tier in assignment.values() if tier == "CXL")
        assert cxl_count >= 2  # At least 2 must be in CXL


class TestIdenticalSensitivity:
    """Test tasks with identical sensitivity scores."""

    def test_greedy_identical_sensitivity(self):
        """Greedy: When sensitivity is identical, assignment is deterministic but arbitrary."""
        tasks = [
            Task(task_id=0, memory_requirement_mb=1000.0, priority=1, memory_sensitivity=0.5),
            Task(task_id=1, memory_requirement_mb=1000.0, priority=2, memory_sensitivity=0.5),
            Task(task_id=2, memory_requirement_mb=1000.0, priority=3, memory_sensitivity=0.5),
            Task(task_id=3, memory_requirement_mb=1000.0, priority=4, memory_sensitivity=0.5),
        ]
        # Total: 4000 MB, DRAM: 3072 MB → 3 tasks in DRAM, 1 in CXL
        
        scheduler = GreedyScheduler(DRAM_CAPACITY_MB, CXL_CAPACITY_MB)
        assignment = scheduler.schedule(tasks)
        
        dram_count = sum(1 for tier in assignment.values() if tier == "DRAM")
        cxl_count = sum(1 for tier in assignment.values() if tier == "CXL")
        
        assert dram_count == 3
        assert cxl_count == 1

    def test_fcfs_identical_sensitivity(self):
        """FCFS: Order by task_id when sensitivity doesn't matter."""
        tasks = [
            Task(task_id=5, memory_requirement_mb=2000.0, priority=1, memory_sensitivity=0.5),
            Task(task_id=2, memory_requirement_mb=2000.0, priority=2, memory_sensitivity=0.5),
        ]
        # Total: 4000 MB, DRAM: 3072 MB → first 2GB in DRAM, rest in CXL
        
        scheduler = FCFSScheduler(DRAM_CAPACITY_MB, CXL_CAPACITY_MB)
        assignment = scheduler.schedule(tasks)
        
        # Task 2 comes first (sorted by task_id)
        assert assignment[2] == "DRAM"
        assert assignment[5] == "CXL"


class TestCapacityExceeded:
    """Test scenarios where total memory exceeds total capacity."""

    def test_exceeds_total_capacity(self):
        """All schedulers should raise ValueError when total exceeds DRAM + CXL."""
        tasks = [
            Task(task_id=0, memory_requirement_mb=5000.0, priority=1, memory_sensitivity=0.5),
            Task(task_id=1, memory_requirement_mb=6000.0, priority=2, memory_sensitivity=0.7),
        ]
        # Total: 11000 MB > 3072 + 5120 = 8192 MB
        
        schedulers = [
            FCFSScheduler(DRAM_CAPACITY_MB, CXL_CAPACITY_MB),
            RoundRobinScheduler(DRAM_CAPACITY_MB, CXL_CAPACITY_MB),
            GreedyScheduler(DRAM_CAPACITY_MB, CXL_CAPACITY_MB),
            GreedyPriorityScheduler(DRAM_CAPACITY_MB, CXL_CAPACITY_MB),
        ]
        
        for scheduler in schedulers:
            with pytest.raises(ValueError, match="exceeds total available capacity"):
                scheduler.schedule(tasks)


class TestEdgeCases:
    """Miscellaneous edge cases."""

    def test_single_task_fits_dram(self):
        """Single task that fits in DRAM."""
        tasks = [
            Task(task_id=0, memory_requirement_mb=1024.0, priority=5, memory_sensitivity=1.0),
        ]
        
        scheduler = GreedyScheduler(DRAM_CAPACITY_MB, CXL_CAPACITY_MB)
        assignment = scheduler.schedule(tasks)
        
        assert assignment[0] == "DRAM"
        cost = scheduler.compute_total_cost(tasks, assignment)
        assert cost == 0.0

    def test_single_large_task_goes_cxl(self):
        """Single task too large for DRAM goes to CXL."""
        tasks = [
            Task(task_id=0, memory_requirement_mb=4000.0, priority=5, memory_sensitivity=0.9),
        ]
        # 4000 MB > 3072 MB DRAM
        
        scheduler = FCFSScheduler(DRAM_CAPACITY_MB, CXL_CAPACITY_MB)
        assignment = scheduler.schedule(tasks)
        
        assert assignment[0] == "CXL"
        cost = scheduler.compute_total_cost(tasks, assignment)
        assert cost > 0

    def test_exact_dram_capacity(self):
        """Tasks that exactly fill DRAM capacity."""
        tasks = [
            Task(task_id=0, memory_requirement_mb=1536.0, priority=1, memory_sensitivity=0.8),
            Task(task_id=1, memory_requirement_mb=1536.0, priority=2, memory_sensitivity=0.6),
        ]
        # Total: exactly 3072 MB = DRAM capacity
        
        scheduler = GreedyScheduler(DRAM_CAPACITY_MB, CXL_CAPACITY_MB)
        assignment = scheduler.schedule(tasks)
        
        assert all(tier == "DRAM" for tier in assignment.values())

    def test_zero_sensitivity_task(self):
        """Task with zero sensitivity has zero cost even in CXL."""
        tasks = [
            Task(task_id=0, memory_requirement_mb=4000.0, priority=1, memory_sensitivity=0.0),
        ]
        
        scheduler = FCFSScheduler(DRAM_CAPACITY_MB, CXL_CAPACITY_MB)
        assignment = scheduler.schedule(tasks)
        
        # Goes to CXL (too big for DRAM)
        assert assignment[0] == "CXL"
        
        # But cost is zero because sensitivity is zero
        cost = scheduler.compute_total_cost(tasks, assignment)
        assert cost == 0.0


class TestCostComputation:
    """Test cost computation correctness."""

    def test_all_dram_zero_cost(self):
        """All tasks in DRAM should have zero total cost."""
        tasks = [
            Task(task_id=0, memory_requirement_mb=500.0, priority=1, memory_sensitivity=0.9),
            Task(task_id=1, memory_requirement_mb=500.0, priority=2, memory_sensitivity=1.0),
        ]
        
        scheduler = GreedyScheduler(DRAM_CAPACITY_MB, CXL_CAPACITY_MB)
        assignment = scheduler.schedule(tasks)
        
        # Both fit in DRAM
        assert all(tier == "DRAM" for tier in assignment.values())
        
        cost = scheduler.compute_total_cost(tasks, assignment)
        assert cost == 0.0

    def test_cost_increases_with_cxl(self):
        """CXL placement increases cost proportionally to sensitivity."""
        tasks = [
            Task(task_id=0, memory_requirement_mb=1000.0, priority=1, memory_sensitivity=0.5),
            Task(task_id=1, memory_requirement_mb=4000.0, priority=2, memory_sensitivity=0.8),
        ]
        # Task 1 goes to CXL (too big for remaining DRAM)
        
        scheduler = FCFSScheduler(DRAM_CAPACITY_MB, CXL_CAPACITY_MB)
        assignment = scheduler.schedule(tasks)
        
        cost = scheduler.compute_total_cost(tasks, assignment)
        
        # Cost should be > 0 because task 1 is in CXL with sensitivity 0.8
        assert cost > 0
        
        # Task 1's contribution: 0.8 × (300-100) × 4000 = 640,000
        expected_cost_task1 = 0.8 * 200 * 4000
        assert abs(cost - expected_cost_task1) < 1.0  # Within 1 due to floating point


class TestBaseSchedulerConsistency:
    """Verify all schedulers implement BaseScheduler interface consistently."""

    def test_all_schedulers_have_schedule_method(self):
        """All schedulers must have schedule() method."""
        schedulers = [
            FCFSScheduler(DRAM_CAPACITY_MB, CXL_CAPACITY_MB),
            RoundRobinScheduler(DRAM_CAPACITY_MB, CXL_CAPACITY_MB),
            GreedyScheduler(DRAM_CAPACITY_MB, CXL_CAPACITY_MB),
            GreedyPriorityScheduler(DRAM_CAPACITY_MB, CXL_CAPACITY_MB),
        ]
        
        for scheduler in schedulers:
            assert hasattr(scheduler, 'schedule')
            assert callable(scheduler.schedule)

    def test_all_schedulers_have_compute_total_cost_method(self):
        """All schedulers must have compute_total_cost() method."""
        schedulers = [
            FCFSScheduler(DRAM_CAPACITY_MB, CXL_CAPACITY_MB),
            RoundRobinScheduler(DRAM_CAPACITY_MB, CXL_CAPACITY_MB),
            GreedyScheduler(DRAM_CAPACITY_MB, CXL_CAPACITY_MB),
            GreedyPriorityScheduler(DRAM_CAPACITY_MB, CXL_CAPACITY_MB),
        ]
        
        for scheduler in schedulers:
            assert hasattr(scheduler, 'compute_total_cost')
            assert callable(scheduler.compute_total_cost)

    def test_schedule_returns_dict(self):
        """schedule() must return Dict[int, str]."""
        tasks = [
            Task(task_id=0, memory_requirement_mb=1000.0, priority=1, memory_sensitivity=0.5),
        ]
        
        schedulers = [
            FCFSScheduler(DRAM_CAPACITY_MB, CXL_CAPACITY_MB),
            RoundRobinScheduler(DRAM_CAPACITY_MB, CXL_CAPACITY_MB),
            GreedyScheduler(DRAM_CAPACITY_MB, CXL_CAPACITY_MB),
            GreedyPriorityScheduler(DRAM_CAPACITY_MB, CXL_CAPACITY_MB),
        ]
        
        for scheduler in schedulers:
            assignment = scheduler.schedule(tasks)
            assert isinstance(assignment, dict)
            assert all(isinstance(k, int) for k in assignment.keys())
            assert all(v in ("DRAM", "CXL") for v in assignment.values())

    def test_compute_total_cost_returns_float(self):
        """compute_total_cost() must return float."""
        tasks = [
            Task(task_id=0, memory_requirement_mb=1000.0, priority=1, memory_sensitivity=0.5),
        ]
        
        schedulers = [
            FCFSScheduler(DRAM_CAPACITY_MB, CXL_CAPACITY_MB),
            RoundRobinScheduler(DRAM_CAPACITY_MB, CXL_CAPACITY_MB),
            GreedyScheduler(DRAM_CAPACITY_MB, CXL_CAPACITY_MB),
            GreedyPriorityScheduler(DRAM_CAPACITY_MB, CXL_CAPACITY_MB),
        ]
        
        for scheduler in schedulers:
            assignment = scheduler.schedule(tasks)
            cost = scheduler.compute_total_cost(tasks, assignment)
            assert isinstance(cost, float)
            assert cost >= 0.0  # Cost cannot be negative
