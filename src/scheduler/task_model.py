"""
Task data model for the quantum scheduler.

This module defines the core Task dataclass used throughout the system.
"""

from dataclasses import dataclass


@dataclass
class Task:
    """
    Represents a computational task with memory requirements.
    
    Attributes:
        task_id: Unique identifier for the task
        memory_requirement_mb: Memory required by the task in megabytes
        priority: Task priority (higher = more important)
        memory_sensitivity: Sensitivity to memory latency (0.0 to 1.0)
                           1.0 = highly sensitive, should prefer DRAM
                           0.0 = insensitive, can tolerate CXL latency
    """
    task_id: int
    memory_requirement_mb: float
    priority: int
    memory_sensitivity: float  # 0.0 to 1.0
    
    def __post_init__(self):
        """Validate task attributes."""
        if self.memory_requirement_mb <= 0:
            raise ValueError(f"memory_requirement_mb must be positive, got {self.memory_requirement_mb}")
        if not 0.0 <= self.memory_sensitivity <= 1.0:
            raise ValueError(f"memory_sensitivity must be between 0.0 and 1.0, got {self.memory_sensitivity}")
        if self.priority < 0:
            raise ValueError(f"priority must be non-negative, got {self.priority}")
