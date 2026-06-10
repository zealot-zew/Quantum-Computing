"""
generate_plots.py
P5 Day 4 — Generate benchmark comparison plots from all_schedulers_summary.csv
Run this from the project root: python generate_plots.py
"""

import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

# ── Data from benchmark run ──────────────────────────────────────────────────
schedulers = ['FCFS', 'Round Robin', 'Greedy', 'Priority\nGreedy', 'RQAOA\n(fallback)']
latency_costs = [592000, 638080, 553600, 553600, 904320]
makespans = [6.059, 3.745, 10.127, 7.518, 9.061]
avg_times = [1.813, 1.370, 2.294, 2.170, 2.231]
dram_util = [93.8, 75.0, 100.0, 100.0, 0.0]

colors = ['#4C72B0', '#DD8452', '#55A868', '#C44E52', '#8172B2']
best_color = '#55A868'
worst_color = '#C44E52'

os.makedirs('results/plots', exist_ok=True)

# ── Plot 1: Latency Cost Comparison ──────────────────────────────────────────
fig, ax = plt.subplots(figsize=(10, 6))
bar_colors = [best_color if v == min(latency_costs) else
              worst_color if v == max(latency_costs) else
              '#4C72B0' for v in latency_costs]
bars = ax.bar(schedulers, latency_costs, color=bar_colors, edgecolor='white', linewidth=1.2)

for bar, val in zip(bars, latency_costs):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 8000,
            f'{val:,.0f}', ha='center', va='bottom', fontsize=9, fontweight='bold')

ax.set_title('Total Latency Cost by Scheduler\n(Lower is Better)', fontsize=14, fontweight='bold', pad=15)
ax.set_ylabel('Latency Cost (ns·MB)', fontsize=11)
ax.set_xlabel('Scheduler', fontsize=11)
ax.set_ylim(0, max(latency_costs) * 1.15)
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x:,.0f}'))
ax.grid(axis='y', alpha=0.3, linestyle='--')
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

from matplotlib.patches import Patch
legend_elements = [Patch(facecolor=best_color, label='Best (Greedy)'),
                   Patch(facecolor=worst_color, label='Worst (RQAOA fallback)'),
                   Patch(facecolor='#4C72B0', label='Other schedulers')]
ax.legend(handles=legend_elements, loc='upper right', fontsize=9)

plt.tight_layout()
plt.savefig('results/plots/latency_comparison.png', dpi=150, bbox_inches='tight')
plt.close()
print("✅ Saved: results/plots/latency_comparison.png")

# ── Plot 2: Makespan Comparison ───────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(10, 6))
bar_colors2 = [best_color if v == min(makespans) else
               worst_color if v == max(makespans) else
               '#4C72B0' for v in makespans]
bars2 = ax.bar(schedulers, makespans, color=bar_colors2, edgecolor='white', linewidth=1.2)

for bar, val in zip(bars2, makespans):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.15,
            f'{val:.2f}s', ha='center', va='bottom', fontsize=9, fontweight='bold')

ax.set_title('Makespan by Scheduler\n(Total wall-clock time — Lower is Better)', fontsize=14, fontweight='bold', pad=15)
ax.set_ylabel('Makespan (seconds)', fontsize=11)
ax.set_xlabel('Scheduler', fontsize=11)
ax.set_ylim(0, max(makespans) * 1.15)
ax.grid(axis='y', alpha=0.3, linestyle='--')
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

legend_elements2 = [Patch(facecolor=best_color, label='Best (Round Robin)'),
                    Patch(facecolor=worst_color, label='Worst (Greedy)'),
                    Patch(facecolor='#4C72B0', label='Other schedulers')]
ax.legend(handles=legend_elements2, loc='upper right', fontsize=9)

plt.tight_layout()
plt.savefig('results/plots/makespan_comparison.png', dpi=150, bbox_inches='tight')
plt.close()
print("✅ Saved: results/plots/makespan_comparison.png")

# ── Plot 3: DRAM Utilisation ──────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(10, 6))
bar_colors3 = [best_color if v == max(dram_util) else
               worst_color if v == min(dram_util) else
               '#4C72B0' for v in dram_util]
bars3 = ax.bar(schedulers, dram_util, color=bar_colors3, edgecolor='white', linewidth=1.2)

for bar, val in zip(bars3, dram_util):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
            f'{val:.1f}%', ha='center', va='bottom', fontsize=9, fontweight='bold')

ax.set_title('DRAM Utilisation by Scheduler\n(Higher is Better — more fast memory used)', fontsize=14, fontweight='bold', pad=15)
ax.set_ylabel('DRAM Utilisation (%)', fontsize=11)
ax.set_xlabel('Scheduler', fontsize=11)
ax.set_ylim(0, 120)
ax.axhline(y=100, color='gray', linestyle='--', alpha=0.5, label='Max capacity (100%)')
ax.grid(axis='y', alpha=0.3, linestyle='--')
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

legend_elements3 = [Patch(facecolor=best_color, label='Best (Greedy & Priority — 100%)'),
                    Patch(facecolor=worst_color, label='Worst (RQAOA fallback — 0%)'),
                    Patch(facecolor='#4C72B0', label='Other schedulers')]
ax.legend(handles=legend_elements3, loc='lower right', fontsize=9)

plt.tight_layout()
plt.savefig('results/plots/utilization_comparison.png', dpi=150, bbox_inches='tight')
plt.close()
print("✅ Saved: results/plots/utilization_comparison.png")

# ── Plot 4: Combined summary ───────────────────────────────────────────────────
fig, axes = plt.subplots(1, 3, figsize=(16, 5))
fig.suptitle('Scheduler Benchmark Summary — All Metrics', fontsize=14, fontweight='bold')

# Latency
axes[0].bar(schedulers, latency_costs, color=colors, edgecolor='white')
axes[0].set_title('Latency Cost\n(Lower = Better)', fontsize=11)
axes[0].set_ylabel('ns·MB')
axes[0].yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x/1000:.0f}k'))
axes[0].tick_params(axis='x', labelsize=8)
axes[0].grid(axis='y', alpha=0.3)

# Makespan
axes[1].bar(schedulers, makespans, color=colors, edgecolor='white')
axes[1].set_title('Makespan\n(Lower = Better)', fontsize=11)
axes[1].set_ylabel('Seconds')
axes[1].tick_params(axis='x', labelsize=8)
axes[1].grid(axis='y', alpha=0.3)

# DRAM Util
axes[2].bar(schedulers, dram_util, color=colors, edgecolor='white')
axes[2].set_title('DRAM Utilisation\n(Higher = Better)', fontsize=11)
axes[2].set_ylabel('%')
axes[2].set_ylim(0, 115)
axes[2].tick_params(axis='x', labelsize=8)
axes[2].grid(axis='y', alpha=0.3)

for ax in axes:
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

plt.tight_layout()
plt.savefig('results/plots/summary_all_metrics.png', dpi=150, bbox_inches='tight')
plt.close()
print("✅ Saved: results/plots/summary_all_metrics.png")

print("\n🎉 All 4 plots generated in results/plots/")