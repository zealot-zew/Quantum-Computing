import matplotlib.pyplot as plt


def plot_latency_comparison(results):
    """
    Example:
    {
        "FCFS": 250,
        "RR": 220,
        "Greedy": 180,
        "RQAOA": 150
    }
    """

    schedulers = list(results.keys())
    values = list(results.values())

    plt.figure(figsize=(8, 5))
    plt.bar(schedulers, values)
    plt.title("Latency Comparison")
    plt.ylabel("Latency (ns)")
    plt.savefig("latency_comparison.png")
    plt.close()


def plot_makespan_comparison(results):

    schedulers = list(results.keys())
    values = list(results.values())

    plt.figure(figsize=(8, 5))
    plt.bar(schedulers, values)
    plt.title("Makespan Comparison")
    plt.ylabel("Time")
    plt.savefig("makespan_comparison.png")
    plt.close()


def plot_utilization(results):

    labels = list(results.keys())
    values = list(results.values())

    plt.figure(figsize=(8, 5))
    plt.bar(labels, values)
    plt.title("Memory Utilization")
    plt.ylabel("Utilization (%)")
    plt.savefig("utilization_comparison.png")
    plt.close()