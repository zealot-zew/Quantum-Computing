"""
Plot generation utilities for scheduler evaluation.

Maintained by: Vikas (P4)
"""

import os
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np


def plot_scheduling_overhead(
    scheduler_names,
    scheduling_times,
    output_file,
):
    plt.figure(figsize=(8, 5))

    # Use log scale since quantum simulation is orders of magnitude slower
    plt.bar(
        scheduler_names,
        scheduling_times,
        color='coral'
    )

    plt.yscale('log')
    plt.title("Scheduling Overhead (Log Scale)")
    plt.xlabel("Scheduler")
    plt.ylabel("Scheduling Compute Time (s)")

    plt.tight_layout()
    plt.savefig(output_file)
    plt.close()



def plot_avg_completion_time(
    scheduler_names,
    avg_times,
    output_file,
):
    plt.figure(figsize=(8, 5))

    plt.bar(
        scheduler_names,
        avg_times,
    )

    plt.title("Average Completion Time per Scheduler")
    plt.xlabel("Scheduler")
    plt.ylabel("Average Completion Time (s)")

    plt.tight_layout()
    plt.savefig(output_file)
    plt.close()


def plot_total_latency_cost(
    scheduler_names,
    latency_costs,
    output_file,
):
    plt.figure(figsize=(8, 5))

    plt.bar(
        scheduler_names,
        latency_costs,
    )

    plt.title("Total Weighted Latency Cost")
    plt.xlabel("Scheduler")
    plt.ylabel("Latency Cost")

    plt.tight_layout()
    plt.savefig(output_file)
    plt.close()


def plot_memory_distribution(
    scheduler_names,
    dram_tasks,
    cxl_tasks,
    output_file,
):
    plt.figure(figsize=(8, 5))

    plt.bar(
        scheduler_names,
        dram_tasks,
        label="DRAM",
    )

    plt.bar(
        scheduler_names,
        cxl_tasks,
        bottom=dram_tasks,
        label="CXL",
    )

    plt.title("DRAM vs CXL Task Placement")
    plt.xlabel("Scheduler")
    plt.ylabel("Number of Tasks")

    plt.legend()

    plt.tight_layout()
    plt.savefig(output_file)
    plt.close()


def generate_all_plots(
    csv_file: str,
    output_dir: str,
):
    """
    Generate all evaluation plots from summary CSV.
    """

    os.makedirs(output_dir, exist_ok=True)

    df = pd.read_csv(csv_file)

    plot_avg_completion_time(
        df["scheduler_name"],
        df["avg_completion_time_s"],
        os.path.join(
            output_dir,
            "avg_completion_time.png",
        ),
    )

    plot_total_latency_cost(
        df["scheduler_name"],
        df["total_latency_cost_ns"],
        os.path.join(
            output_dir,
            "latency_cost.png",
        ),
    )

    plot_memory_distribution(
        df["scheduler_name"],
        df["dram_tasks"],
        df["cxl_tasks"],
        os.path.join(
            output_dir,
            "memory_distribution.png",
        ),
    )

    if "scheduling_time_s" in df.columns:
        plot_scheduling_overhead(
            df["scheduler_name"],
            df["scheduling_time_s"],
            os.path.join(
                output_dir,
                "scheduling_overhead.png",
            ),
        )

    print(f"Plots saved to {output_dir}")