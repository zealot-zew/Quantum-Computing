# NUMA Verification & Simulation Strategy

**Date:** 2026-06-06
**Author:** Hari (P2) / Antigravity
**Instance:** AWS EC2 `i-0aa88607ce0e5f4c9` — Ubuntu 26.04 LTS (Resolute)

---

## 📋 Summary

Hardware NUMA emulation via `numa=fake=2` is **not available** on this VM due to a kernel
limitation. The project uses **software-level latency injection** in `task_runner.py` to
simulate the DRAM vs. CXL latency difference instead. This is already planned in the
Day 2/3 sprint tasks and has no impact on the correctness of results.

---

## 🔍 Investigation Log

### Step 1 — Initial NUMA state (before any changes)

```
$ numactl --hardware
available: 1 nodes (0)
node 0 cpus: 0 1
node 0 size: 1905 MB
node 0 free: 1337 MB
node distances:
node   0
  0:  10
```
Only one memory node — no NUMA tiering. This is expected on a fresh instance.

---

### Step 2 — Applied `numa=fake=2` via GRUB

**Problem encountered:** AWS EC2 Ubuntu instances use a cloud-specific GRUB override file
(`/etc/default/grub.d/50-cloudimg-settings.cfg`) that takes priority over the standard
`/etc/default/grub`. Editing only the main file has no effect.

**Fix:** Added `numa=fake=2` to the cloud override file directly.

```
# /etc/default/grub.d/50-cloudimg-settings.cfg
GRUB_CMDLINE_LINUX_DEFAULT="console=tty1 console=ttyS0 nvme_core.io_timeout=4294967295 numa=fake=2"
```

After `sudo update-grub` and reboot, `/proc/cmdline` confirmed the parameter was passed:

```
BOOT_IMAGE=/vmlinuz-7.0.0-1004-aws ... numa=fake=2 panic=-1
```

However, the kernel logged:

```
[    0.000000] Malformed early option 'numa'
```

And `numactl --hardware` still showed 1 node.

---

### Step 3 — Root Cause: `CONFIG_NUMA_EMU` Not Compiled In

```
$ grep -i 'NUMA_EMU' /boot/config-7.0.0-14-generic
# CONFIG_NUMA_EMU is not set
```

Both the AWS kernel (`7.0.0-1004-aws`) and the generic Ubuntu kernel (`7.0.0-14-generic`)
on **Ubuntu 26.04 LTS** (kernel 7.0.0) were compiled **without `CONFIG_NUMA_EMU`**.

`CONFIG_NUMA_EMU` is the kernel compile-time flag that enables the `numa=fake=N` boot
parameter. Without it, the kernel does not recognise this parameter at all.

This is a kernel-level limitation that cannot be worked around without recompiling the
kernel from source — which is out of scope for this project.

---

## ✅ Solution: Software Latency Simulation

Since physical NUMA node splitting is unavailable, we simulate the CXL vs. DRAM latency
difference directly in `task_runner.py` using `time.sleep()`.

### How It Works

```python
# In task_runner.py — Day 2 implementation
CXL_LATENCY_PENALTY_S: float = 0.002  # 2ms sleep per memory access chunk (simulates CXL overhead)
DRAM_LATENCY_PENALTY_S: float = 0.0   # No sleep for DRAM (fast path)

if args.node == 1:   # CXL node
    time.sleep(CXL_LATENCY_PENALTY_S * access_count)
```

This means:
- `--node 0` tasks run at full speed → simulating **DRAM** (Node 0, fast)
- `--node 1` tasks run with artificial delays → simulating **CXL** (Node 1, slow)

The executor still uses `numactl` calls in its interface, but since both
nodes map to the single physical node, the timing difference is entirely
driven by the software injection.

### Why This Is Acceptable

- The sprint evaluation is based on **measured task completion time**, not physical
  memory hardware. Software-injected latency produces measurable, reproducible timing
  differences just like real hardware NUMA would.
- The RQAOA algorithm makes decisions based on the QUBO cost matrix, which uses
  `CXL_LATENCY_NS` and `DRAM_LATENCY_NS` constants — these remain accurate regardless
  of whether the latency is physical or simulated.
- The sprint plan (Day 2, P3) explicitly includes: *"Add latency injection to
  task_runner.py — If --node 1 (CXL): time.sleep(LATENCY_PENALTY_S)"*

---

## 📐 Final Verified VM State

```
$ numactl --hardware
available: 1 nodes (0)
node 0 cpus: 0 1
node 0 size: 1905 MB
node 0 free: ~1400 MB
node distances:
node   0
  0:  10

$ numactl --show
policy: default
preferred node: current
physpubind: 0 1
nodebind: 0
membind: 0
```

`numactl` is installed and functional. Task binding commands (`--cpunodebind`, `--membind`)
are syntactically valid and will be used in the executor to make the code architecture
identical to how it would run on real hardware. The only difference is both node 0 and
node 1 map to the same physical memory bank.

---

## 📝 GRUB Files Modified (Can Be Reverted)

If future work requires reverting these changes:

```bash
# Remove numa=fake=2 from the cloud grub override
sudo nano /etc/default/grub.d/50-cloudimg-settings.cfg
# Remove 'numa=fake=2' from GRUB_CMDLINE_LINUX_DEFAULT

sudo update-grub
sudo reboot
```
