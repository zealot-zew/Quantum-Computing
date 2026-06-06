# How to Configure Fake NUMA Nodes in Linux

This guide explains how to configure **Fake NUMA nodes** in Linux using the kernel boot parameter `numa=fake`. This is useful for simulating tiered memory architectures (like local DRAM + CXL-attached memory) on standard single-socket systems, local virtual machines, or cheap cloud instances (e.g., AWS EC2, DigitalOcean).

---

## 📋 Prerequisites
1. A Linux system (Ubuntu, Debian, CentOS, or RHEL) running with root privileges.
2. The `numactl` package installed.
   * **Ubuntu/Debian:** `sudo apt-get update && sudo apt-get install -y numactl`
   * **CentOS/RHEL:** `sudo yum install -y numactl`

---

## 🛠️ Step-by-Step Configuration (Ubuntu & Debian)

Most cloud instances and VMs use the **GRUB** bootloader. Follow these steps to configure fake NUMA nodes:

### Step 1: Open the GRUB Configuration File
Open `/etc/default/grub` in a text editor (e.g., `nano`):
```bash
sudo nano /etc/default/grub
```

### Step 2: Modify the Kernel Parameters
Locate the line beginning with `GRUB_CMDLINE_LINUX_DEFAULT`. It typically looks like:
```bash
GRUB_CMDLINE_LINUX_DEFAULT="maybe-some-options quiet splash"
```

Add `numa=fake=<value>` to the end of the parameters inside the quotes.

* **Option A: Equal division by count**
  To split your RAM and CPUs equally into a specific number of nodes:
  ```bash
  GRUB_CMDLINE_LINUX_DEFAULT="quiet splash numa=fake=2"
  ```
  *(e.g., on a 2GB RAM system with 2 CPUs, this creates 2 nodes, each with 1 CPU and ~1GB RAM)*.

* **Option B: Division by memory size**
  To specify the exact amount of RAM for each node:
  ```bash
  GRUB_CMDLINE_LINUX_DEFAULT="quiet splash numa=fake=1G,1G"
  ```
  *(Creates 2 nodes of 1 GB each. The remaining memory, if any, will be assigned to Node 0)*.

Save and exit (`Ctrl+O`, `Enter`, then `Ctrl+X`).

### Step 3: Update the Bootloader
Generate the updated bootloader configuration so the kernel recognizes the changes:
```bash
sudo update-grub
```

### Step 4: Reboot the System
```bash
sudo reboot
```

---

## 🛠️ Step-by-Step Configuration (CentOS / RHEL / Amazon Linux)

For RedHat-based distributions:

1. Open `/etc/default/grub` and append `numa=fake=2` to `GRUB_CMDLINE_LINUX`.
2. Rebuild the GRUB configuration:
   * **BIOS-based systems:**
     ```bash
     sudo grub2-mkconfig -o /boot/grub2/grub.cfg
     ```
   * **UEFI-based systems:**
     ```bash
     sudo grub2-mkconfig -o /boot/efi/EFI/redhat/grub.cfg
     ```
3. Reboot:
   ```bash
   sudo reboot
   ```

---

## 🔍 Verification

Once the system reboots, SSH back in and verify that the virtual NUMA nodes have been created:

### Command:
```bash
numactl --hardware
```

### Expected Output (Example for `numa=fake=2` on a 2GB, 2 CPU VM):
```text
available: 2 nodes (0-1)
node 0 cpus: 0
node 0 size: 980 MB
node 0 free: 750 MB
node 1 cpus: 1
node 1 size: 996 MB
node 1 free: 820 MB
node distances:
node   0   1 
  0:  10  20 
  1:  20  10 
```

---

## ↩️ Reverting Changes

If you need to restore your system back to its original state:

1. Open `/etc/default/grub` again:
   ```bash
   sudo nano /etc/default/grub
   ```
2. Remove the `numa=fake=...` parameter from `GRUB_CMDLINE_LINUX_DEFAULT`.
3. Update grub:
   ```bash
   sudo update-grub
   ```
4. Reboot the machine:
   ```bash
   sudo reboot
   ```

---

## 💡 Quick Cheat Sheet: Testing with `numactl`

Once your nodes are active, use these commands to test binding:

* **Bind memory and CPU execution to Node 0 (DRAM simulation):**
  ```bash
  numactl --cpunodebind=0 --membind=0 python3 workload.py
  ```
* **Bind memory and CPU execution to Node 1 (CXL simulation):**
  ```bash
  numactl --cpunodebind=1 --membind=1 python3 workload.py
  ```
* **Check memory allocation policy of a running process:**
  ```bash
  numastat -p <PID>
  ```
