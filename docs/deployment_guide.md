# Deployment Guide

This guide explains how to set up the execution environment for the Quantum-Assisted CXL-Aware Scheduler, configure NUMA binding, and run the pipeline end-to-end.

## 1. Prerequisites

The execution engine uses `numactl` to bind tasks to physical memory nodes (DRAM vs. CXL).

- **OS**: Linux (Ubuntu 22.04/24.04 recommended) or macOS (for development only).
- **Python**: 3.10 is **strictly required** (OpenQAOA compatibility).
- **System Packages** (Linux only): `sudo apt-get install numactl`

> **Note on macOS / Windows**: If `numactl` is not available, the executor gracefully falls back to unbounded execution. Latency simulation will still work correctly because it is handled via software sleeps in `task_runner.py`.

## 2. Environment Setup

Clone the repository and initialize the virtual environment using the setup script. This script enforces Python 3.10 and installs all required dependencies.

```bash
git clone <repository_url>
cd quantum_scheduler

# Make the setup script executable and run it
chmod +x setup_env.sh
./setup_env.sh
```

If you prefer manual setup:
```bash
python3.10 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 3. IBM Quantum Token (Optional but Recommended)

To run the RQAOA optimization on real hardware (or advanced simulators), you need an IBM Quantum API token.

1. Sign up at [quantum.ibm.com](https://quantum.ibm.com).
2. Copy your API token from your account dashboard.
3. Save it to a `.env` file in the project root:

```bash
echo "IBM_QUANTUM_TOKEN=your_token_here" > .env
```

## 4. NUMA Configuration (Linux Only)

If you are running on a bare-metal server with real CXL memory attached, no further configuration is needed.

If you are running on a standard cloud VM (like AWS EC2) and want to **emulate** NUMA nodes for testing, you can split your physical RAM into "fake" NUMA nodes using the GRUB bootloader.

1. Edit `/etc/default/grub`.
2. Append `numa=fake=2` to the `GRUB_CMDLINE_LINUX_DEFAULT` line.
   *(Example: `GRUB_CMDLINE_LINUX_DEFAULT="console=tty1 console=ttyS0 numa=fake=2"`)*
3. Run `sudo update-grub` and reboot.
4. Verify with `numactl --hardware`. You should see `node 0` and `node 1`.

> **Important**: `numa=fake=2` requires the kernel to be compiled with `CONFIG_NUMA_EMU=y`. Standard Ubuntu kernels often do not include this. If `numactl --hardware` still shows only 1 node, rely on the software latency simulation built into `task_runner.py`. (See `docs/numa_verification.md` for details).

## 5. Running the Pipeline

The full pipeline (QUBO Build → Schedule → Execute → Evaluate → Plot) is driven by `main.py`.

Activate your environment:
```bash
source .venv/bin/activate
```

Run a specific classical scheduler:
```bash
python main.py --scheduler fcfs
python main.py --scheduler greedy
python main.py --scheduler greedy_priority
```

Run the RQAOA scheduler (requires OpenQAOA):
```bash
python main.py --scheduler rqaoa
```

**Run all schedulers and compare them**:
```bash
python main.py --scheduler all
```

**Dry-Run Mode**:
To test the pipeline without actually launching memory-bound subprocesses, use the `--dry-run` flag. This will print the `numactl` commands that *would* be run and generate zeroed metrics.
```bash
python main.py --scheduler all --dry-run
```

## 6. Development & Quality Assurance

All code must pass linting and type checking before being merged.

**Run Unit Tests**:
```bash
python -m pytest tests/ -v
```

**Run Linting (Flake8)**:
```bash
python -m flake8 src/ --max-line-length=100
```

**Run Type Checking (MyPy)**:
```bash
python -m mypy src/
```

## 7. Interpreting Results

After running the pipeline, check the `results/` folder:

- `results/execution_log.csv`: Raw, per-task timing and placement data.
- `results/all_schedulers_summary.csv`: Aggregated metrics (Makespan, Avg Time, Total Cost) for each scheduler.
- `results/plots/*.png`: Visualizations of the scheduler performance.
- `results/qubo_heatmap.png`: Visualization of the underlying QUBO matrix used by RQAOA.
