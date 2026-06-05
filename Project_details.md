# **Project Proposal**

## **Quantum-Assisted Optimization Engine for CXL-Aware Hybrid Scheduling**

This proposal outlines the development of a quantum-assisted optimization engine to address memory placement challenges in next-generation heterogeneous systems with tiered memory architectures (DRAM and CXL-like memory).

# **Problem Statement: Limitations of Classical Scheduling**

Traditional CPU scheduling algorithms such as First-Come-First-Served (FCFS) and Round Robin (RR) were originally designed for relatively homogeneous systems. While modern operating systems include NUMA-aware optimizations, they have limited awareness of heterogeneous memory tiers introduced by emerging architectures such as CXL-like systems.

This results in the following challenges:

### **Memory Tier Unawareness**

Schedulers typically do not explicitly account for differences between:

* Local DRAM (\~80–120 ns latency)  
* Disaggregated or CXL-like memory (\~200–400+ ns latency)

This can lead to suboptimal placement of memory-sensitive workloads, increasing memory access latency and degrading performance.

### **Sequential Bottlenecks**

FCFS suffers from the convoy effect, where short-duration tasks are delayed by long-running processes, reducing overall system efficiency.

### **Combinatorial Complexity**

Mapping tasks to memory tiers (e.g., DRAM vs remote memory) creates a combinatorial optimization problem. As the number of tasks increases, the number of possible placements grows exponentially, making it difficult for heuristic-based schedulers to identify globally optimal solutions.

# **Proposed Solution: Quantum-Assisted Optimization using RQAOA**

To address these challenges, the project proposes a Quantum-Assisted Optimization Engine based on the Recursive Quantum Approximate Optimization Algorithm (RQAOA).

## **Key Idea**

The system uses RQAOA as an optimization layer to compute near-optimal task-to-memory mappings, complementing classical scheduling approaches.

## **Recursive Problem Reduction**

RQAOA reduces problem complexity iteratively:

* Identifies correlations between decision variables  
* Fixes strongly correlated variables  
* Reduces the problem size step-by-step  
* Solves the remaining reduced problem using classical methods

This enables solving combinatorial optimization problems within the constraints of current quantum hardware.

## **QUBO Formulation**

The scheduling problem is modeled as a Quadratic Unconstrained Binary Optimization (QUBO) problem:

* Variables represent task-to-memory assignments  
* Constraints encode memory capacity and placement rules  
* Costs represent latency penalties and access overhead

The objective is to minimize total memory access cost across all tasks.

## **Positioning**

This work explores the feasibility of quantum-assisted optimization for scheduling and does not assume or claim superiority over classical optimization methods.

**System Design and Execution Model**

## **Architecture Overview**

The system is composed of three main layers:

### **1\. Optimization Layer**

* Implements RQAOA-based optimization  
* Generates optimal or near-optimal task placement decisions  
* Built using OpenQAOA and Qiskit

### **2\. Scheduling Layer**

* Interprets optimization output (bitstring representation)  
* Maps tasks to specific memory tiers

### **3\. Execution Layer**

* Enforces placement decisions using numactl  
* Binds processes to designated memory nodes

## **Execution Flow**

1. Input: Task set with memory requirements  
2. Optimization: RQAOA computes placement decisions  
3. Scheduling: Tasks mapped to memory tiers  
4. Execution: Tasks run with enforced memory binding  
5. Evaluation: Performance metrics are collected

# **CXL Simulation Methodology**

Due to the lack of access to physical CXL-enabled hardware, the system models CXL-like memory behavior using a combination of NUMA-based memory tiering and high-level performance modeling.

## **NUMA-Based Memory Tiering**

The system leverages the Linux NUMA architecture to represent heterogeneous memory tiers:

* **Local NUMA node (Node 0\)** represents high-speed DRAM  
* **Remote NUMA node (Node 1\)** represents CXL-attached memory

Processes are explicitly bound to these memory nodes using numactl, enabling controlled placement of workloads across memory tiers.

##  **Latency Modeling**

To reflect the higher access latency of CXL-like  memory, additional delay is introduced for memory operations associated with the remote NUMA node.

* Local DRAM accesses are treated as baseline latency  
* Remote accesses incur an additional latency penalty

##  **Bandwidth Modeling**

CXL-like memory is further characterized by reduced effective bandwidth compared to DRAM. This is approximated by introducing constraints on the rate of memory access for workloads assigned to the remote memory tier.

**Execution Integration**

Workloads are executed with NUMA-aware binding:

* Tasks assigned to DRAM → bound to Node 0  
* Tasks assigned to CXL → bound to Node 1

## **Assumptions**

* Memory is treated as logically shared across tiers  
* Cache coherence and low-level protocol behavior are not explicitly modeled  
* The focus is on performance characteristics relevant to scheduling

**Scoped Simulation & Testing Plan**

## **System Configuration**

| Component | Strategy | Technology |
| ----- | ----- | ----- |
| Data Center Model | 8 tasks, 2 memory tiers | Python (NetworkX) |
| Optimization Engine | RQAOA | OpenQAOA |
| Local Testing | Classical simulation | Qiskit Aer |
| Quantum Validation | Small-scale execution | IBM Quantum |
| Execution Layer | NUMA binding | numactl |

## 

## 

## 

## 

## 

## **Execution Strategy**

* Majority of experiments conducted locally  
* Limited runs on real quantum hardware for validation

## **Evaluation Metrics**

* Task completion time  
* Memory access latency  
* Overall scheduling efficiency  
* Impact of memory tier placement

**Feasibility and Constraints**

**Feasibility**

The project is implementable due to:

* Availability of high-level quantum SDKs  
* Built-in NUMA support in modern Linux systems  
* Ability to model memory tier behavior without specialized hardware

## **Constraints**

* Limited problem size due to quantum hardware constraints  
* Offline or batch scheduling focus (not real-time scheduling)  
* Approximate modeling of CXL behavior  
* No guarantee of globally optimal solutions

# **Key Contributions**

* Design of a CXL-aware memory scheduling framework  
* Integration of quantum-assisted optimization (RQAOA) into scheduling  
* Implementation of realistic memory-tier simulation using NUMA and performance modeling  
* Evaluation of scheduling strategies under heterogeneous memory conditions

**Resources**

* **Algorithm SDK:** [OpenQAOA GitHub](https://github.com/entropicalabs/openqaoa) (Core engine for RQAOA).  
* **QUBO Tools:**([https://github.com/recruit-communications/pyqubo](https://github.com/recruit-communications/pyqubo)) (To map data center costs).  
* **Quantum Backend:**([https://github.com/Qiskit/qiskit](https://github.com/Qiskit/qiskit)) (For circuit execution and QPU access).  
* **Reference Code:**([https://github.com/aboev/quantum-job-scheduler](https://github.com/aboev/quantum-job-scheduler)) (A template for sequencing jobs).


