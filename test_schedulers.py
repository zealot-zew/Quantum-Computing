"""
Quick test script for Day 2 scheduler implementations.
"""

from src.scheduler import get_canonical_tasks, DRAM_CAPACITY_MB, CXL_CAPACITY_MB
from src.scheduler.fcfs_scheduler import FCFSScheduler
from src.scheduler.round_robin_scheduler import RoundRobinScheduler
from src.scheduler.greedy_scheduler import GreedyScheduler


def test_scheduler(scheduler_name, scheduler, tasks):
    """Test a scheduler and print results."""
    print(f"\n{'='*80}")
    print(f"{scheduler_name} Scheduler")
    print(f"{'='*80}")
    
    try:
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
        
        print(f"✅ Success!")
        print(f"Total Latency Cost: {cost:.2f}")
        print(f"DRAM Tasks: {dram_tasks} ({dram_used:.1f} MB / {DRAM_CAPACITY_MB:.1f} MB)")
        print(f"CXL Tasks: {cxl_tasks} ({cxl_used:.1f} MB / {CXL_CAPACITY_MB:.1f} MB)")
        print(f"\nAssignment:")
        for task_id in sorted(assignment.keys()):
            task = next(t for t in tasks if t.task_id == task_id)
            print(f"  Task {task_id}: {assignment[task_id]:4s} "
                  f"({task.memory_requirement_mb:6.1f} MB, "
                  f"sensitivity={task.memory_sensitivity:.2f})")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    """Run all scheduler tests."""
    print("="*80)
    print("TESTING DAY 2 SCHEDULER IMPLEMENTATIONS")
    print("="*80)
    
    tasks = get_canonical_tasks()
    print(f"\nTesting with {len(tasks)} canonical tasks")
    print(f"Total Memory Required: {sum(t.memory_requirement_mb for t in tasks):.1f} MB")
    print(f"DRAM Capacity: {DRAM_CAPACITY_MB:.1f} MB")
    print(f"CXL Capacity: {CXL_CAPACITY_MB:.1f} MB")
    
    # Test all schedulers
    schedulers = [
        ("FCFS", FCFSScheduler(DRAM_CAPACITY_MB, CXL_CAPACITY_MB)),
        ("Round Robin", RoundRobinScheduler(DRAM_CAPACITY_MB, CXL_CAPACITY_MB)),
        ("Greedy", GreedyScheduler(DRAM_CAPACITY_MB, CXL_CAPACITY_MB)),
    ]
    
    results = {}
    for name, scheduler in schedulers:
        success = test_scheduler(name, scheduler, tasks)
        results[name] = success
    
    # Summary
    print(f"\n{'='*80}")
    print("TEST SUMMARY")
    print(f"{'='*80}")
    for name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{name:<20} {status}")
    
    all_passed = all(results.values())
    print(f"\nOverall: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")


if __name__ == "__main__":
    main()
