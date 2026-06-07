"""
Greedy Scheduler.

Assigns tasks to memory tiers based on memory sensitivity.
Most sensitive tasks get DRAM first.
"""

from typing import Dict, List
from src.scheduler.task_model import Task


class GreedyScheduler:
    """
    Greedy scheduler based on memory sensitivity.
    
    This scheduler sorts tasks by memory_sensitivity in descending order
    and assigns the most sensitive tasks to DRAM first, placing remaining
    tasks in CXL memory.
    
    This represents a heuristic that aims to minimize the impact of high
    memory latency by prioritizing latency-sensitive workloads for fast
    memory placement.
    
    Attributes:
        dram_capacity_mb: Maximum DRAM capacity in megabytes
        cxl_capacity_mb: Maximum CXL memory capacity in megabytes
    """
    
    def __init__(self, dram_capacity_mb: float, cxl_capacity_mb: float):
        """
        Initialize Greedy scheduler with memory tier capacities.
        
        Args:
            dram_capacity_mb: DRAM capacity in MB
            cxl_capacity_mb: CXL memory capacity in MB
        """
        self.dram_capacity_mb = dram_capacity_mb
        self.cxl_capacity_mb = cxl_capacity_mb
    
    def schedule(self, tasks: List[Task]) -> Dict[int, str]:
        """
        Schedule tasks using Greedy policy based on memory sensitivity.
        
        Args:
            tasks: List of Task objects to schedule
            
        Returns:
            Dictionary mapping task_id to memory tier ("DRAM" or "CXL")
            
        Raises:
            ValueError: If total memory requirement exceeds total available capacity
        """
        # TODO: Implement Greedy scheduling logic
        # 1. Sort tasks by memory_sensitivity descending
        # 2. Assign high-sensitivity tasks to DRAM until capacity exceeded
        # 3. Assign remaining to CXL
        # 4. Return assignment dictionary
        pass
    
    def compute_total_cost(self, tasks: List[Task], assignment: Dict[int, str]) -> float:
        """
        Compute total latency cost for the given assignment.
        
        Args:
            tasks: List of Task objects
            assignment: Task-to-tier mapping
            
        Returns:
            Total weighted latency cost
        """
        # TODO: Implement cost computation
        pass
