from metrics import (
    calculate_avg_completion_time,
    calculate_makespan,
    calculate_latency_cost,
    calculate_dram_utilization
)

tasks = [
    {
        "completion_time": 10,
        "latency": 100
    },
    {
        "completion_time": 20,
        "latency": 150
    }
]

print("Average Completion Time:",
      calculate_avg_completion_time(tasks))

print("Makespan:",
      calculate_makespan(tasks))

print("Latency Cost:",
      calculate_latency_cost(tasks))

print("DRAM Utilization:",
      calculate_dram_utilization(12, 16))