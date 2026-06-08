"""
Day 3 - Run all 4 classical schedulers and save results to CSV.

This script runs FCFS, Round Robin, Greedy, and Priority-Weighted Greedy
schedulers, computes performance metrics, and saves to results/classical_baselines.csv
"""

import csv
import os
from src.scheduler import get_canonical_tasks, DRAM_CAPACITY_MB, CXL_CAPACITY_MB
from src.scheduler.fcfs_scheduler import FCFSScheduler
from src.scheduler.round_robin_scheduler import RoundRobinScheduler
from src.scheduler.greedy_scheduler import GreedyScheduler
from src.scheduler.greedy_priority_scheduler import GreedyPriorityScheduler as PriorityWeightedGreedyScheduler


def compute_metrics(scheduler_name, scheduler, tasks):
    """Compute and return metrics for a scheduler."""
    # Get assignment
    assignment = scheduler.schedule(tasks)
    
    # Compute cost
    cost = scheduler.compute_total_cost(tasks, assignment)
    
    # Count tasks per tier
    dram_tasks = sum(1 for tier in assignment.values() if tier == "DRAM")
    cxl_tasks = sum(1 for tier in assignment.values() if tier == "CXL")
    
    # Calculate memory usage
    dram_used = sum(task.memory_requirement_mb for task in tasks 
                   if assignment[task.task_id] == "DRAM")
    cxl_used = sum(task.memory_requirement_mb for task in tasks 
                  if assignment[task.task_id] == "CXL")
    
    # DRAM utilization percentage
    dram_utilization = (dram_used / DRAM_CAPACITY_MB) * 100
    
    return {
        'scheduler': scheduler_name,
        'total_latency_cost': cost,
        'dram_tasks': dram_tasks,
        'cxl_tasks': cxl_tasks,
        'dram_used_mb': dram_used,
        'cxl_used_mb': cxl_used,
        'dram_utilization_pct': dram_utilization,
        'assignment': assignment
    }


def main():
    """Run all schedulers and save results."""
    print("="*80)
    print("DAY 3: Running All Classical Schedulers")
    print("="*80)
    
    tasks = get_canonical_tasks()
    print(f"\nTesting with {len(tasks)} canonical tasks")
    print(f"DRAM Capacity: {DRAM_CAPACITY_MB:.1f} MB")
    print(f"CXL Capacity: {CXL_CAPACITY_MB:.1f} MB\n")
    
    # Define all schedulers
    schedulers = [
        ("FCFS", FCFSScheduler(DRAM_CAPACITY_MB, CXL_CAPACITY_MB)),
        ("RoundRobin", RoundRobinScheduler(DRAM_CAPACITY_MB, CXL_CAPACITY_MB)),
        ("Greedy", GreedyScheduler(DRAM_CAPACITY_MB, CXL_CAPACITY_MB)),
        ("PriorityWeighted", PriorityWeightedGreedyScheduler(DRAM_CAPACITY_MB, CXL_CAPACITY_MB)),
    ]
    
    results = []
    
    # Run each scheduler
    for name, scheduler in schedulers:
        print(f"Running {name}...")
        try:
            metrics = compute_metrics(name, scheduler, tasks)
            results.append(metrics)
            print(f"  ✅ Cost: {metrics['total_latency_cost']:.2f}, "
                  f"DRAM: {metrics['dram_tasks']}, CXL: {metrics['cxl_tasks']}")
        except Exception as e:
            print(f"  ❌ Error: {e}")
    
    # Create results directory if it doesn't exist
    os.makedirs('results', exist_ok=True)
    
    # Save to CSV
    csv_path = 'results/classical_baselines.csv'
    with open(csv_path, 'w', newline='') as f:
        fieldnames = ['scheduler', 'total_latency_cost', 'dram_tasks', 'cxl_tasks',
                     'dram_used_mb', 'cxl_used_mb', 'dram_utilization_pct']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for result in results:
            row = {k: v for k, v in result.items() if k != 'assignment'}
            writer.writerow(row)
    
    print(f"\n✅ Results saved to {csv_path}")
    
    # Print summary table
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    print(f"{'Scheduler':<20} {'Cost':<15} {'DRAM Tasks':<12} {'CXL Tasks':<12} {'DRAM %':<10}")
    print(f"{'-'*80}")
    for result in results:
        print(f"{result['scheduler']:<20} "
              f"{result['total_latency_cost']:<15.2f} "
              f"{result['dram_tasks']:<12} "
              f"{result['cxl_tasks']:<12} "
              f"{result['dram_utilization_pct']:<10.1f}")
    
    # Find best scheduler
    best = min(results, key=lambda x: x['total_latency_cost'])
    print(f"\n🏆 Best Scheduler: {best['scheduler']} (Cost: {best['total_latency_cost']:.2f})")


if __name__ == "__main__":
    main()
