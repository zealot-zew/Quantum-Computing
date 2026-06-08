"""
Unit tests for scheduler edge cases - Day 3.

Tests edge cases like:
- All tasks fit in DRAM
- No tasks fit in DRAM
- Tasks with identical sensitivity
- Empty task list
- Single task
"""

import pytest
from src.scheduler.task_model import Task
from src.scheduler.fcfs_scheduler import FCFSScheduler
from src.scheduler.round_robin_scheduler import RoundRobinScheduler
from src.scheduler.greedy_scheduler import GreedyScheduler


# Test constants
DRAM_CAP = 2048.0
CXL_CAP = 4096.0


class TestAllTasksFitInDRAM:
    """Test when all tasks can fit in DRAM."""
    
    def test_fcfs_all_dram(self):
        """FCFS should assign all tasks to DRAM when they fit."""
        tasks = [
            Task(0, 512.0, 3, 0.9),
            Task(1, 512.0, 3, 0.8),
            Task(2, 512.0, 3, 0.7),
        ]
        # Total: 1536 MB < 2048 MB DRAM
        
        scheduler = FCFSScheduler(DRAM_CAP, CXL_CAP)
        assignment = scheduler.schedule(tasks)
        
        assert all(tier == "DRAM" for tier in assignment.values())
        assert len(assignment) == 3
    
    def test_greedy_all_dram(self):
        """Greedy should assign all tasks to DRAM when they fit."""
        tasks = [
            Task(0, 1000.0, 3, 0.5),
            Task(1, 500.0, 3, 0.9),
            Task(2, 400.0, 3, 0.3),
        ]
        # Total: 1900 MB < 2048 MB DRAM
        
        scheduler = GreedyScheduler(DRAM_CAP, CXL_CAP)
        assignment = scheduler.schedule(tasks)
        
        assert all(tier == "DRAM" for tier in assignment.values())
        assert len(assignment) == 3


class TestNoTasksFitInDRAM:
    """Test when DRAM capacity is too small."""
    
    def test_fcfs_all_cxl(self):
        """FCFS with tiny DRAM should use CXL."""
        tasks = [
            Task(0, 512.0, 3, 0.9),
            Task(1, 512.0, 3, 0.8),
        ]
        
        scheduler = FCFSScheduler(100.0, CXL_CAP)  # Only 100 MB DRAM
        assignment = scheduler.schedule(tasks)
        
        assert all(tier == "CXL" for tier in assignment.values())
        assert len(assignment) == 2
    
    def test_round_robin_minimal_dram(self):
        """Round Robin with minimal DRAM."""
        tasks = [
            Task(0, 512.0, 3, 0.9),
            Task(1, 256.0, 3, 0.8),
        ]
        
        scheduler = RoundRobinScheduler(50.0, CXL_CAP)  # Only 50 MB DRAM
        assignment = scheduler.schedule(tasks)
        
        # Should fallback to CXL for both
        assert sum(1 for t in assignment.values() if t == "CXL") >= 1


class TestIdenticalSensitivity:
    """Test tasks with identical sensitivity scores."""
    
    def test_greedy_identical_sensitivity(self):
        """Greedy with all tasks having same sensitivity."""
        tasks = [
            Task(0, 512.0, 3, 0.7),
            Task(1, 512.0, 3, 0.7),
            Task(2, 512.0, 3, 0.7),
            Task(3, 512.0, 3, 0.7),
            Task(4, 512.0, 3, 0.7),  # Total: 2560 MB
        ]
        
        scheduler = GreedyScheduler(DRAM_CAP, CXL_CAP)
        assignment = scheduler.schedule(tasks)
        
        # Should assign 4 to DRAM (2048 MB) and 1 to CXL
        dram_count = sum(1 for t in assignment.values() if t == "DRAM")
        cxl_count = sum(1 for t in assignment.values() if t == "CXL")
        
        assert dram_count == 4
        assert cxl_count == 1
        assert len(assignment) == 5
    
    def test_fcfs_identical_sensitivity(self):
        """FCFS with identical sensitivity - should use arrival order."""
        tasks = [
            Task(0, 1024.0, 3, 0.5),
            Task(1, 1024.0, 3, 0.5),
            Task(2, 1024.0, 3, 0.5),
        ]
        
        scheduler = FCFSScheduler(DRAM_CAP, CXL_CAP)
        assignment = scheduler.schedule(tasks)
        
        # Task 0 and 1 should be in DRAM, Task 2 in CXL
        assert assignment[0] == "DRAM"
        assert assignment[1] == "DRAM"
        assert assignment[2] == "CXL"


class TestCapacityExceeded:
    """Test when total memory exceeds available capacity."""
    
    def test_exceeds_total_capacity(self):
        """Should raise ValueError when total > DRAM + CXL."""
        tasks = [
            Task(0, 3000.0, 3, 0.9),
            Task(1, 4000.0, 3, 0.8),  # Total: 7000 MB > 2048 + 4096
        ]
        
        scheduler = FCFSScheduler(DRAM_CAP, CXL_CAP)
        
        with pytest.raises(ValueError, match="exceeds total available capacity"):
            scheduler.schedule(tasks)


class TestEdgeCases:
    """Test other edge cases."""
    
    def test_single_task_fits_dram(self):
        """Single task that fits in DRAM."""
        tasks = [Task(0, 1024.0, 3, 0.9)]
        
        scheduler = GreedyScheduler(DRAM_CAP, CXL_CAP)
        assignment = scheduler.schedule(tasks)
        
        assert assignment[0] == "DRAM"
    
    def test_single_large_task_goes_cxl(self):
        """Single task too large for DRAM goes to CXL."""
        tasks = [Task(0, 3000.0, 3, 0.9)]
        
        scheduler = FCFSScheduler(DRAM_CAP, CXL_CAP)
        assignment = scheduler.schedule(tasks)
        
        assert assignment[0] == "CXL"
    
    def test_exact_dram_capacity(self):
        """Tasks that exactly fill DRAM."""
        tasks = [
            Task(0, 1024.0, 3, 0.9),
            Task(1, 1024.0, 3, 0.8),  # Exactly 2048 MB
        ]
        
        scheduler = FCFSScheduler(DRAM_CAP, CXL_CAP)
        assignment = scheduler.schedule(tasks)
        
        assert all(tier == "DRAM" for tier in assignment.values())
    
    def test_zero_sensitivity_task(self):
        """Task with zero sensitivity should work."""
        tasks = [
            Task(0, 512.0, 3, 0.0),  # Zero sensitivity
            Task(1, 512.0, 3, 0.9),
        ]
        
        scheduler = GreedyScheduler(DRAM_CAP, CXL_CAP)
        assignment = scheduler.schedule(tasks)
        
        # Task 1 (high sensitivity) should get DRAM
        assert assignment[1] == "DRAM"
        assert len(assignment) == 2


class TestCostComputation:
    """Test cost computation edge cases."""
    
    def test_all_dram_zero_cost(self):
        """All tasks in DRAM should have zero additional cost."""
        tasks = [
            Task(0, 512.0, 3, 0.9),
            Task(1, 512.0, 3, 0.8),
        ]
        
        scheduler = FCFSScheduler(DRAM_CAP, CXL_CAP)
        assignment = {0: "DRAM", 1: "DRAM"}
        cost = scheduler.compute_total_cost(tasks, assignment)
        
        assert cost == 0.0
    
    def test_cost_increases_with_cxl(self):
        """CXL tasks should increase cost."""
        tasks = [Task(0, 1000.0, 3, 0.8)]
        
        scheduler = FCFSScheduler(DRAM_CAP, CXL_CAP)
        
        dram_cost = scheduler.compute_total_cost(tasks, {0: "DRAM"})
        cxl_cost = scheduler.compute_total_cost(tasks, {0: "CXL"})
        
        assert cxl_cost > dram_cost
        assert dram_cost == 0.0
