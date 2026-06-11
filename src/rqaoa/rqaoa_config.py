
"""rqaoa_config.py — Tunable constants for RQAOA."""

RQAOA_LAYERS:    int = 1
RECURSIVE_CUTOFF: int = 3
OPTIMIZER:        str = "COBYLA"
SHOTS:            int = 1024

# Fallback Greedy Settings
FALLBACK_CXL_BUDGET_MB: float = 4096.0
DEFAULT_FALLBACK_TASK_SIZE_MB: float = 200.0

# IBM Backend Settings
IBM_DEVICE_NAME: str = "ibm_osaka"
