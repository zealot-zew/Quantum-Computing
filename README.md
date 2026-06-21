# Quantum-Assisted Optimization Engine for CXL-Aware Hybrid Scheduling

> A hybrid quantum-classical scheduling simulator that formulates memory-tier task placement as a QUBO problem and solves it using RQAOA — benchmarked against classical baselines (FCFS, Round Robin, Greedy, Priority-Weighted Greedy) on a full OS-level execution pipeline.

**Institution:** BMS College of Engineering  
**Team:** Anjana · Hari · Smarth · Vikas · Devandra

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [AWS EC2 Setup](#aws-ec2-setup)
- [IBM Quantum Setup](#ibm-quantum-setup)
- [Installation](#installation)
- [Running the Pipeline](#running-the-pipeline)
- [CLI Reference](#cli-reference)
- [Outputs](#outputs)
- [Project Structure](#project-structure)
- [Development & Quality Checks](#development--quality-checks)
- [Results Summary](#results-summary)
- [Limitations](#limitations)
- [References](#references)

---

## Overview

Modern data-intensive workloads increasingly exceed local DRAM capacity, requiring placement across heterogeneous memory tiers — local DRAM (~80–120 ns) and CXL-attached memory (~200–400+ ns). Classical schedulers like FCFS and Round Robin are blind to this latency gap, leading to significant performance degradation.

This project formulates the task-to-memory-tier placement problem as a **Quadratic Unconstrained Binary Optimization (QUBO)** model and solves it using **RQAOA (Recursive Quantum Approximate Optimization Algorithm)** via OpenQAOA. The system:

- Builds the QUBO matrix encoding DRAM capacity constraints and per-task memory sensitivities.
- Runs the optimizer locally via **Qiskit Aer** (simulation) or on real **IBM Quantum hardware**.
- Enforces placement decisions at the OS level using **`numactl`** (NUMA memory binding).
- Collects and compares metrics across all schedulers, generating CSV reports and plots.

---

## Architecture

![System Architecture Diagram](architeture%20diagram.png)

**Pipeline flow:**

```
Input Task Set
      │
      ▼
┌─────────────────────┐
│   QUBO Builder      │  ← Encodes latency costs + DRAM capacity constraints
│  (qubo_builder.py)  │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│   RQAOA Optimizer   │  ← OpenQAOA + Qiskit Aer / IBM Quantum hardware
│  (rqaoa_runner.py)  │
└────────┬────────────┘
         │ Bitstring assignment (0=DRAM, 1=CXL)
         ▼
┌─────────────────────────────────────────────────┐
│              Scheduler Layer                    │
│  FCFS | Round Robin | Greedy | Priority Greedy  │  ← Classical baselines
│              RQAOA Scheduler                    │  ← Quantum output interpreter
└────────┬────────────────────────────────────────┘
         │
         ▼
┌─────────────────────┐
│   Execution Layer   │  ← numactl --membind=0 (DRAM) / --membind=1 (CXL)
│  (task_runner.py)   │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  Evaluation Layer   │  ← Makespan, Avg Time, Latency Cost, DRAM Utilization
│  results/ + plots/  │
└─────────────────────┘
```

**Three layers:**
1. **Optimization Layer** — RQAOA computes near-optimal task-to-tier assignments.
2. **Scheduling Layer** — Interprets the bitstring output; also implements 4 classical baselines.
3. **Execution Layer** — Enforces placement via `numactl` subprocess binding with injected CXL latency.

---

## Prerequisites

### System Requirements

| Requirement | Details |
|---|---|
| **Operating System** | Linux (Ubuntu 22.04 / 24.04) strongly recommended; macOS supported for development only |
| **Python** | **3.10 exactly** — required by `openqaoa` (will not work on 3.11+) |
| **numactl** | Linux only — for NUMA memory binding (`sudo apt-get install numactl`) |
| **RAM** | 4 GB minimum recommended |

> **macOS / Windows Note:** `numactl` is not available on macOS or Windows. The executor automatically falls back to unbounded execution. CXL latency is still simulated correctly via software sleeps in `task_runner.py`.

### Python Dependencies

All dependencies are pinned in [`requirements.txt`](requirements.txt):

| Category | Packages |
|---|---|
| **Quantum SDKs** | `qiskit<1.0.0`, `qiskit-aer<1.0.0`, `openqaoa-core>=0.2.0`, `openqaoa-qiskit>=0.2.0` |
| **QUBO / Optimization** | `pyqubo>=1.4.0` |
| **Scientific Computing** | `numpy>=1.26.0`, `scipy>=1.12.0`, `pandas>=2.1.0`, `networkx>=3.2.0` |
| **Visualization** | `matplotlib>=3.8.0` |
| **System Monitoring** | `psutil>=5.9.0` |
| **Testing & QA** | `pytest>=8.0.0`, `pytest-cov>=4.1.0`, `mypy>=1.9.0`, `flake8>=7.0.0` |
| **Config** | `python-dotenv>=1.0.0` |

---

## AWS EC2 Setup

To run the full pipeline with `numactl` NUMA binding, provision your own **AWS EC2** Linux instance. The project is not tied to any specific instance — use the values from your own AWS Console.

### Recommended Instance Configuration

| Property | Recommended Value |
|---|---|
| **Instance Type** | `m7i-flex.large` or any `m6i` / `m7i` general-purpose instance |
| **Region** | Any — use the region closest to you |
| **OS / AMI** | Ubuntu 22.04 LTS (recommended) or Amazon Linux 2023 |
| **Storage** | 20 GB gp3 root volume |
| **Security Group** | Allow inbound SSH (port 22) from your IP only |
| **Key Pair** | Generate a `.pem` key pair in AWS Console and download it |

### Step 1 — Set Key File Permissions

The private key `quantum.pem` is located in the project root. SSH will reject the key if its permissions are too open.

```bash
chmod 400 quantum.pem
```

### Step 2 — Connect via SSH

Replace `<YOUR_EC2_PUBLIC_IP>` with the **Public IPv4** shown in your AWS Console for the running instance.

```bash
# Ubuntu / Debian instances
ssh -i "your-key.pem" ubuntu@<YOUR_EC2_PUBLIC_IP>
```

For Amazon Linux / Red Hat instances:
```bash
ssh -i "your-key.pem" ec2-user@<YOUR_EC2_PUBLIC_IP>
```

### Step 3 — Install System Dependencies (first time only)

Once connected to the instance:

```bash
sudo apt-get update
sudo apt-get install -y numactl python3.10 python3.10-venv git
```

### Step 4 — NUMA Emulation (Optional)

On a cloud VM with a single physical NUMA node, you can emulate two NUMA nodes (to simulate DRAM vs. CXL tiers) via the GRUB bootloader:

1. Edit the GRUB config:
   ```bash
   sudo nano /etc/default/grub
   ```
2. Append `numa=fake=2` to `GRUB_CMDLINE_LINUX_DEFAULT`:
   ```
   GRUB_CMDLINE_LINUX_DEFAULT="console=tty1 console=ttyS0 numa=fake=2"
   ```
3. Apply and reboot:
   ```bash
   sudo update-grub && sudo reboot
   ```
4. Verify after reboot:
   ```bash
   numactl --hardware
   # Should show: available: 2 nodes (0-1)
   ```

> **Note:** `numa=fake=2` requires `CONFIG_NUMA_EMU=y` in the kernel. If only 1 node appears, the pipeline will still work correctly via software latency simulation in `task_runner.py`. See [`docs/numa_verification.md`](docs/numa_verification.md) for details.

### Troubleshooting AWS Connection

| Problem | Solution |
|---|---|
| `Permission denied (publickey)` | Run `chmod 400 quantum.pem`; ensure you're in the directory containing the key |
| Connection timeout | Verify the instance is **Running** in AWS Console; check Security Group allows port 22 inbound |
| IP changed | If the instance was stopped and restarted, the public IP may have changed — check the AWS Console |

---

## IBM Quantum Setup

To run RQAOA optimization on **real IBM Quantum hardware** (instead of the local Qiskit Aer simulator):

### Step 1 — Create an IBM Quantum Account

Sign up at [quantum.ibm.com](https://quantum.ibm.com) (free tier available).

### Step 2 — Get Your API Token

1. Log in to your IBM Quantum account.
2. Navigate to **My Account → API Token**.
3. Copy the token.

### Step 3 — Configure the `.env` File

Create a `.env` file in the project root:

```bash
echo "IBM_QUANTUM_TOKEN=your_token_here" > .env
```

Or manually create `.env`:
```
IBM_QUANTUM_TOKEN=paste_your_token_here
```

> **Security:** The `.env` file is listed in `.gitignore` and must **never** be committed to the repository.

### Step 4 — Run with IBM Hardware

```bash
python main.py --scheduler rqaoa --use-ibm
```

> **Warning:** Real hardware runs consume IBM Quantum credits and may take significantly longer than simulation. The pipeline includes an automatic fallback to the Classical Priority-Weighted Greedy scheduler if the quantum hardware bitstring fails validation (e.g., due to NISQ noise). See [`docs/noise_effects.md`](docs/noise_effects.md) for details.

---

## Installation

### Option A — Automated Setup (Recommended)

The setup script enforces Python 3.10 and creates an isolated virtual environment:

```bash
git clone <repository_url>
cd "Quantum Computing"

chmod +x setup_env.sh
./setup_env.sh

source .venv/bin/activate
```

### Option B — Manual Setup

```bash
git clone <repository_url>
cd "Quantum Computing"

python3.10 -m venv .venv
source .venv/bin/activate       # On Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

### Verify Installation

```bash
python -c "import qiskit, openqaoa, pyqubo, numpy, pandas, networkx, matplotlib, psutil; print('All dependencies OK')"
```

---

## Running the Pipeline

The full pipeline (QUBO Build → Schedule → Execute → Evaluate → Plot) is driven by [`main.py`](main.py).

Ensure your virtual environment is active:

```bash
source .venv/bin/activate
```

### Run All Schedulers (Full Benchmark)

```bash
python main.py --scheduler all
```

This runs FCFS → Round Robin → Greedy → Priority-Weighted Greedy → RQAOA sequentially and generates comparison plots.

### Run a Specific Scheduler

```bash
# Classical schedulers
python main.py --scheduler fcfs
python main.py --scheduler rr
python main.py --scheduler greedy
python main.py --scheduler greedy_priority

# Quantum scheduler (Qiskit Aer simulator)
python main.py --scheduler rqaoa

# Quantum scheduler on real IBM hardware
python main.py --scheduler rqaoa --use-ibm
```

### Quick Simulation (Scaled-Down)

Scale task memory sizes down by 10× to speed up execution significantly:

```bash
python main.py --scheduler all --scale-factor 0.1
```

### Dry Run (No Subprocess Execution)

Test the pipeline logic without launching any memory-bound subprocesses:

```bash
python main.py --scheduler all --dry-run
```

This prints the `numactl` commands that *would* run and generates zeroed metrics — useful for CI and debugging.

---

## CLI Reference

```
usage: main.py [-h] --scheduler {fcfs,rr,greedy,greedy_priority,rqaoa,all}
               [--dry-run] [--scale-factor SCALE_FACTOR] [--use-ibm]

options:
  --scheduler       Scheduler to run: fcfs | rr | greedy | greedy_priority | rqaoa | all
  --dry-run         Skip subprocess execution; print numactl commands only
  --scale-factor    Float multiplier for task memory sizes (default: 1.0; use 0.1 for quick runs)
  --use-ibm         Run RQAOA on IBM Quantum hardware (requires IBM_QUANTUM_TOKEN in .env)
```

---

## Outputs

All outputs are written to the `results/` directory:

| File | Description |
|---|---|
| `results/execution_log.csv` | Raw per-task timing, placement tier, and latency data |
| `results/all_schedulers_summary.csv` | Aggregated metrics (Makespan, Avg Completion Time, Latency Cost, DRAM Utilization) per scheduler |
| `results/qubo_heatmap.png` | Visualization of the QUBO matrix used by RQAOA |
| `results/plots/avg_completion_time.png` | Bar chart: average completion time per scheduler |
| `results/plots/latency_cost.png` | Bar chart: total weighted latency cost per scheduler |
| `results/plots/memory_distribution.png` | Bar chart: DRAM vs. CXL task distribution |
| `results/plots/scheduling_overhead.png` | Bar chart: scheduling algorithm overhead |

### Evaluation Metrics

| Metric | Definition |
|---|---|
| **Average Completion Time** | Mean task duration (launch → completion) across all tasks |
| **Makespan** | Wall-clock time from first task start to last task end |
| **Total Weighted Latency Cost** | `Σ sensitivity_i × memory_mb_i × latency_penalty` (0 for DRAM, 200ns for CXL) |
| **DRAM Utilization** | Percentage of available DRAM capacity consumed |

---

## Project Structure

```
Quantum Computing/
│
├── main.py                          # CLI entry point — full pipeline runner
├── run_benchmarks.py                # Orchestrates all scheduler benchmark runs
├── task_runner.py                   # OS-level subprocess worker with CXL latency injection
├── requirements.txt                 # All pinned Python dependencies
├── setup_env.sh                     # Automated Python 3.10 venv setup script
├── aws_connect.md                   # AWS EC2 connection guide
│
├── src/
│   ├── rqaoa/                       # Quantum optimization module
│   │   ├── qubo_builder.py          # Builds QUBO matrix from task set
│   │   ├── rqaoa_runner.py          # Runs RQAOA via OpenQAOA
│   │   ├── rqaoa_config.py          # RQAOA hyperparameter configuration
│   │   ├── result_parser.py         # Parses RQAOA bitstring output
│   │   ├── ibm_quantum_prep.py      # IBM Quantum backend preparation
│   │   ├── ibm_quantum_submit.py    # IBM Quantum job submission
│   │   ├── scaling_experiment.py    # RQAOA scaling tests
│   │   └── statistical_robustness.py # Robustness analysis across runs
│   │
│   ├── scheduler/                   # Classical scheduler implementations
│   │   ├── task_model.py            # Task dataclass with validation
│   │   ├── tasks.py                 # 8 canonical benchmark tasks + constants
│   │   ├── fcfs_scheduler.py        # First-Come-First-Served
│   │   ├── greedy_scheduler.py      # Sensitivity-sorted Greedy
│   │   ├── greedy_priority_scheduler.py  # Priority × Sensitivity composite score
│   │   ├── round_robin_scheduler.py # Round Robin (DRAM/CXL alternating)
│   │   └── scheduler_interface.py   # Abstract base class for all schedulers
│   │
│   ├── executor/                    # OS-level execution engine
│   │   └── __init__.py              # numactl binding and fallback logic
│   │
│   └── evaluation/                  # Metrics collection and plotting
│       ├── metrics.py               # CSV schema definitions and metric computation
│       └── graphs.py                # Matplotlib plot generation
│
├── docs/
│   ├── math_foundations.md          # Full QUBO / RQAOA mathematical derivation
│   ├── deployment_guide.md          # Detailed setup and deployment instructions
│   ├── numa_verification.md         # NUMA hardware investigation & simulation decision
│   ├── noise_effects.md             # IBM Quantum NISQ noise analysis
│   └── rqaoa_methodology_section.md # RQAOA algorithm methodology write-up
│
├── quantum_scheduler/
│   └── report.md                    # Full research report
│
├── tests/                           # Unit test suite (pytest)
├── results/                         # Generated CSVs and plots (git-ignored)
└── .env                             # IBM Quantum token (git-ignored — do NOT commit)
```

---

## Development & Quality Checks

All code must pass the following checks before merging:

### Run Unit Tests

```bash
python -m pytest tests/ -v
```

### Lint (Flake8)

```bash
python -m flake8 src/ --max-line-length=100
```

### Type Checking (MyPy)

```bash
python -m mypy src/
```

### Run All Checks (Pre-commit)

```bash
python -m pytest tests/ && \
python -m flake8 src/ --max-line-length=100 && \
python -m mypy src/
```

### Branch Strategy

```bash
# Never commit directly to main. Always use a feature branch:
git checkout -b feature/<short-description>

# Examples:
git checkout -b feature/qubo-matrix-builder
git checkout -b fix/numa-binding-fallback
```

Commit messages follow **Conventional Commits**:
```
feat(qubo): add penalty term for DRAM capacity constraint
fix(executor): handle numactl fallback for non-Linux systems
docs(readme): add RQAOA algorithm overview
```

---

## Results Summary

Benchmarked on a canonical workload of **8 tasks** (12.8 MB – 102.4 MB), with DRAM capacity constrained to 50% of total task memory:

| Scheduler | DRAM Tasks | CXL Tasks | Avg Time (s) | Makespan (s) | DRAM Util (%) | Latency Cost (ns·MB) |
|---|---|---|---|---|---|---|
| FCFS | 4 | 4 | 1.9778 | 5.8121 | 93.75 | 592,000 |
| Round Robin | 2 | 6 | 2.2189 | 5.5507 | 75.00 | 638,080 |
| Greedy | 4 | 4 | 1.8364 | 5.7634 | 100.00 | 553,600 |
| Greedy Priority | 4 | 4 | 1.8296 | 5.6254 | 100.00 | 553,600 |
| **RQAOA (p=1)** | 3 | 5 | 2.1119 | 5.6939 | 56.25 | 768,640 |

> **Key Insight:** At shallow circuit depth (p=1), RQAOA correctly formulates the QUBO and respects DRAM capacity, but falls into a local minimum, underperforming exact Classical Greedy solvers. Deeper circuits and error-mitigated hardware are required to demonstrate quantum advantage on this problem class.

---

## Limitations

- **Problem size:** Constrained to 8 tasks due to current quantum hardware qubit limits.
- **Offline scheduling:** Batch mode only — no real-time or dynamic rescheduling.
- **Approximate CXL modeling:** Latency is injected via `time.sleep()`; physical CXL protocol behavior is not modeled.
- **No optimality guarantee:** RQAOA is a heuristic — it provides near-optimal, not globally optimal, solutions.
- **NISQ noise:** IBM Quantum hardware results are affected by gate and measurement errors; no error mitigation is currently applied.

---

## References

1. Farhi, E., Goldstone, J., & Gutmann, S. (2014). *A Quantum Approximate Optimization Algorithm.* [arXiv:1411.4028](https://arxiv.org/abs/1411.4028)
2. Bravyi, S., et al. (2020). *Obstacles to Variational Quantum Optimization from Symmetry Protection.* Physical Review Letters.
3. [OpenQAOA](https://github.com/entropicalabs/openqaoa) — Core RQAOA engine.
4. [PyQUBO](https://github.com/recruit-communications/pyqubo) — QUBO model construction.
5. [Qiskit](https://github.com/Qiskit/qiskit) — Quantum circuit execution and QPU access.
6. [CXL Consortium — CXL 3.0 Specification](https://www.computeexpresslink.org)
7. Linux `numactl` — [man page](https://linux.die.net/man/8/numactl)
8. Reference Scheduler: [aboev/quantum-job-scheduler](https://github.com/aboev/quantum-job-scheduler)

---

## Team

| Person | Role | Owns |
|---|---|---|
| **Anjana** | Quantum Algorithm + Infra | `src/rqaoa/`, QUBO math, IBM Quantum integration |
| **Hari** | Infra + Quantum Algorithm | `task_runner.py`, `src/executor/`, RQAOA config |
| **Smarth** | Classical Scheduler + Simulation | `src/scheduler/`, latency injection |
| **Vikas** | Evaluation + Classical Scheduler | `src/evaluation/`, plots, `greedy_priority_scheduler.py` |
| **Devandra** | Docs + Integration Lead | `main.py`, `README.md`, daily merges |

---

*For the full research report, see [`quantum_scheduler/report.md`](quantum_scheduler/report.md).*  
*For QUBO / RQAOA mathematical foundations, see [`docs/math_foundations.md`](docs/math_foundations.md).*
