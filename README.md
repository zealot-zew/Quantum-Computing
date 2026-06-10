# Quantum-Assisted CXL-Aware Scheduler

A hybrid scheduling simulator that leverages quantum algorithms (RQAOA) to optimally place memory-intensive tasks across heterogeneous memory tiers (local DRAM and CXL-attached memory).

## Overview

This project formulates the NP-hard memory tier placement problem as a Quadratic Unconstrained Binary Optimization (QUBO) model. By minimizing a cost function that considers task-specific memory sensitivities and DRAM capacity constraints, the system optimizes task execution times. It features a complete pipeline from QUBO building to OS-level NUMA execution binding (`numactl`) and evaluation metric parsing.

The optimization is run using OpenQAOA via Qiskit Aer (local simulator) and supports real IBM Quantum hardware execution.

## Requirements

- Linux environment strongly recommended (for `numactl` binding). macOS is supported via fallback non-bound execution.
- Python 3.10 exactly (required by `openqaoa`).

## Installation

1. Clone this repository.
2. Run the environment setup script to create a `.venv` with Python 3.10 and install all dependencies:
   ```bash
   ./setup_env.sh
   source .venv/bin/activate
   ```
3. *(Optional)* To run on actual IBM Quantum hardware, create a `.env` file in the root with your API token:
   ```
   IBM_QUANTUM_TOKEN=your_token_here
   ```

## Usage

The primary entry point is `main.py`. This script builds the models, evaluates the selected schedulers, executes the tasks, and produces CSV summaries and graphical plots in the `results/` directory.

```bash
# Run the complete pipeline with all 5 schedulers (FCFS, Round Robin, Greedy, Priority Greedy, RQAOA)
python main.py --scheduler all

# Run only a specific scheduler
python main.py --scheduler rqaoa

# Run a quick simulated dry-run (scales task sizes down to speed up sleep commands)
python main.py --scheduler all --scale-factor 0.1
```

## Outputs

All outputs are generated inside the `results/` folder:
- `all_schedulers_summary.csv`: Aggregated latency, makespan, and utilization metrics.
- `execution_log.csv`: Detailed task-by-task execution times.
- `plots/`: Bar charts comparing average completion time, total latency costs, and memory distribution.

### Evaluation Plots
![Average Completion Time](results/plots/avg_completion_time.png)
![Total Latency Cost](results/plots/latency_cost.png)
![Memory Distribution](results/plots/memory_distribution.png)

## Documentation

- `quantum_scheduler/report.md`: The complete research report.
- `docs/math_foundations.md`: Details on the QUBO and RQAOA formulations.
- `src/*/README.md`: Module-specific documentation.
