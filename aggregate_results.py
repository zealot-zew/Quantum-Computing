"""
Day 4 - Aggregate all scheduler results into all_schedulers_summary.csv

Generates comprehensive summary with:
- scheduler name
- avg_latency_ms (simulated)
- total_latency_cost
- dram_tasks
- cxl_tasks
- makespan_s (total execution time)
- dram_utilization_pct
"""

import csv
import os
from src.scheduler import get_canonical_tasks, DRAM_CAPACITY_MB, CXL_CAPACITY_MB
from src.scheduler.fcfs_scheduler import FCFSScheduler
from src.scheduler.round_robin_scheduler import RoundRobinScheduler
from src.scheduler.greedy_scheduler import GreedyScheduler
from src.scheduler.greedy_priority_scheduler import GreedyPriorityScheduler


def aggregate_scheduler_results():
    """
    Run all schedulers and aggregate comprehensive results.
    
    Returns:
        List of result dictionaries with all metrics
    """
    tasks = get_canonical_tasks()
    
    schedulers = [
        ("FCFS", FCFSScheduler(DRAM_CAPACITY_MB, CXL_CAPACITY_MB)),
        ("RoundRobin", RoundRobinScheduler(DRAM_CAPACITY_MB, CXL_CAPACITY_MB)),
        ("Greedy", GreedyScheduler(DRAM_CAPACITY_MB, CXL_CAPACITY_MB)),
        ("PriorityWeighted", GreedyPriorityScheduler(DRAM_CAPACITY_MB, CXL_CAPACITY_MB)),
    ]
    
    results = []
    
    for scheduler_name, scheduler in schedulers:
        # Get assignment
        assignment = scheduler.schedule(tasks)
        
        # Compute metrics
        total_cost = scheduler.compute_total_cost(tasks, assignment)
        
        # Count tasks per tier
        dram_tasks = sum(1 for tier in assignment.values() if tier == "DRAM")
        cxl_tasks = sum(1 for tier in assignment.values() if tier == "CXL")
        
        # Memory usage
        dram_used = sum(task.memory_requirement_mb for task in tasks 
                       if assignment[task.task_id] == "DRAM")
        cxl_used = sum(task.memory_requirement_mb for task in tasks 
                      if assignment[task.task_id] == "CXL")
        
        # DRAM utilization
        dram_utilization_pct = (dram_used / DRAM_CAPACITY_MB) * 100
        
        # Simulate avg latency (based on CXL tasks and their sensitivity)
        avg_latency_ms = 0.0
        for task in tasks:
            if assignment[task.task_id] == "DRAM":
                avg_latency_ms += 100.0  # DRAM baseline: 100ms
            else:
                # CXL adds latency based on sensitivity
                avg_latency_ms += 100.0 + (200.0 * task.memory_sensitivity)
        avg_latency_ms /= len(tasks)
        
        # Simulated makespan (total execution time in seconds)
        # Assume tasks run sequentially, each takes 1-3s base time
        # CXL tasks take longer
        makespan_s = 0.0
        for task in tasks:
            base_time = task.memory_requirement_mb / 500.0  # ~2s for 1GB task
            if assignment[task.task_id] == "CXL":
                base_time *= (1.0 + task.memory_sensitivity * 0.5)  # Up to 50% slower
            makespan_s += base_time
        
        results.append({
            'scheduler': scheduler_name,
            'avg_latency_ms': avg_latency_ms,
            'total_latency_cost': total_cost,
            'dram_tasks': dram_tasks,
            'cxl_tasks': cxl_tasks,
            'makespan_s': makespan_s,
            'dram_utilization_pct': dram_utilization_pct
        })
    
    return results


def main():
    """Generate all_schedulers_summary.csv"""
    print("="*80)
    print("DAY 4: Aggregating All Scheduler Results")
    print("="*80)
    print()
    
    # Get results
    results = aggregate_scheduler_results()
    
    # Create results directory
    os.makedirs('results', exist_ok=True)
    
    # Save to CSV
    csv_path = 'results/all_schedulers_summary.csv'
    fieldnames = ['scheduler', 'avg_latency_ms', 'total_latency_cost', 
                 'dram_tasks', 'cxl_tasks', 'makespan_s', 'dram_utilization_pct']
    
    with open(csv_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)
    
    print(f"✅ Results saved to {csv_path}\n")
    
    # Print formatted table
    print("="*80)
    print("ALL SCHEDULERS SUMMARY")
    print("="*80)
    print(f"{'Scheduler':<18} {'Avg Latency':<15} {'Total Cost':<15} {'DRAM':<8} {'CXL':<8} {'Makespan':<12} {'DRAM %':<10}")
    print(f"{'':18} {'(ms)':<15} {'':15} {'Tasks':<8} {'Tasks':<8} {'(sec)':<12} {'':10}")
    print("-"*80)
    
    for result in results:
        print(f"{result['scheduler']:<18} "
              f"{result['avg_latency_ms']:<15.2f} "
              f"{result['total_latency_cost']:<15.0f} "
              f"{result['dram_tasks']:<8} "
              f"{result['cxl_tasks']:<8} "
              f"{result['makespan_s']:<12.2f} "
              f"{result['dram_utilization_pct']:<10.1f}")
    
    # Best scheduler
    best_cost = min(results, key=lambda x: x['total_latency_cost'])
    best_makespan = min(results, key=lambda x: x['makespan_s'])
    
    print("\n" + "="*80)
    print("KEY INSIGHTS")
    print("="*80)
    print(f"🏆 Best Cost: {best_cost['scheduler']} ({best_cost['total_latency_cost']:.0f})")
    print(f"⚡ Fastest Makespan: {best_makespan['scheduler']} ({best_makespan['makespan_s']:.2f}s)")
    print()


if __name__ == "__main__":
    main()
