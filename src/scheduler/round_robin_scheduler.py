"""
Round Robin (RR) Scheduler.

Alternates task assignment between DRAM and CXL memory tiers.
"""

from typing import Dict, List
from src.scheduler.task_model import Task


class RoundRobinScheduler:
    """
    Round Robin scheduler.
    
    This scheduler alternates assignment between DRAM and CXL memory tiers,
    providing a simple load-balancing approach without considering task
    characteristics.
    
    Attributes:
        dram_capacity_mb: Maximum DRAM capacity in megabytes
        cxl_capacity_mb: Maximum CXL memory capacity in megabytes
    """
    
    def __init__(self, dram_capacity_mb: float, cxl_capacity_mb: float):
        """
        Initialize Round Robin scheduler with memory tier capacities.
        
        Args:
            dram_capacity_mb: DRAM capacity in MB
            cxl_capacity_mb: CXL memory capacity in MB
        """
        self.dram_capacity_mb = dram_capacity_mb
        self.cxl_capacity_mb = cxl_capacity_mb
    
    def schedule(self, tasks: List[Task]) -> Dict[int, str]:
        """
        Schedule tasks using Round Robin policy.
        
        Args:
            tasks: List of Task objects to schedule
            
        Returns:
            Dictionary mapping task_id to memory tier ("DRAM" or "CXL")
            
        Raises:
            ValueError: If total memory requirement exceeds total available capacity
        """
        # TODO: Implement Round Robin scheduling logic
        # 1. Alternate between DRAM and CXL
        # 2. Check capacity constraints
        # 3. Return assignment dictionary
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
