#!/usr/bin/env python3
"""
Real-time plotting from arduino-cli monitor pipe
Usage: arduino-cli monitor -p COM5 -c baudrate=115200 | python live_plot.py
"""

import sys
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from collections import deque
import numpy as np

# Configuration
MAX_POINTS = 1000  # Number of points to keep in memory

# Data storage
sample_numbers = deque(maxlen=MAX_POINTS)
sample_values = deque(maxlen=MAX_POINTS)
all_samples = []  # Keep all for histogram

sample_count = 0

# Create figure with subplots
fig = plt.figure(figsize=(14, 8))
gs = fig.add_gridspec(2, 2, hspace=0.3, wspace=0.3)

ax1 = fig.add_subplot(gs[0, :])  # Time series (full width)
ax2 = fig.add_subplot(gs[1, 0])  # Histogram
ax3 = fig.add_subplot(gs[1, 1])  # Statistics

# Initialize plots
line, = ax1.plot([], [], 'b-', linewidth=0.8)
ax1.set_xlabel('Sample Number')
ax1.set_ylabel('ADC Value')
ax1.set_title('Real-time ADC Samples')
ax1.grid(True, alpha=0.3)
ax1.set_ylim(0, 4096)

# Histogram setup
ax2.set_xlabel('ADC Value')
ax2.set_ylabel('Frequency')
ax2.set_title('Value Distribution')
ax2.grid(True, alpha=0.3)

# Statistics text
stats_text = ax3.text(0.1, 0.5, 'Waiting for data...',
                      transform=ax3.transAxes,
                      fontsize=12, verticalalignment='center',
                      family='monospace')
ax3.axis('off')

def read_stdin():
    """Read from stdin (piped from arduino-cli)"""
    global sample_count

    for line in sys.stdin:
        line = line.strip()

        # Skip header
        if 'Time_us' in line or 'Sample' in line:
            continue

        # Parse data
        try:
            if ',' in line:
                parts = line.split(',')
                if len(parts) >= 2:
                    value = int(parts[1])
                else:
                    continue
            else:
                value = int(line)

            sample_count += 1
            sample_numbers.append(sample_count)
            sample_values.append(value)
            all_samples.append(value)

            yield value

        except ValueError:
            continue

def update_plot(frame):
    """Update plot with new data"""
    if len(sample_values) == 0:
        return line,

    # Update time series
    line.set_data(list(sample_numbers), list(sample_values))

    if len(sample_numbers) > 1:
        ax1.set_xlim(min(sample_numbers), max(sample_numbers))

        # Auto-scale y-axis with some margin
        if len(sample_values) > 10:
            min_val = min(sample_values)
            max_val = max(sample_values)
            margin = (max_val - min_val) * 0.1 or 100
            ax1.set_ylim(max(0, min_val - margin), min(4096, max_val + margin))

    # Update histogram (every 10 samples for performance)
    if sample_count % 10 == 0 and len(all_samples) > 10:
        ax2.clear()
        ax2.hist(all_samples, bins=50, color='green', alpha=0.7, edgecolor='black')
        ax2.set_xlabel('ADC Value')
        ax2.set_ylabel('Frequency')
        ax2.set_title('Value Distribution')
        ax2.grid(True, alpha=0.3)

    # Update statistics
    if len(all_samples) > 0:
        mean_val = np.mean(all_samples)
        std_val = np.std(all_samples)
        min_val = np.min(all_samples)
        max_val = np.max(all_samples)

        stats_str = f"""
╔═══════════════════════════╗
║      STATISTICS          ║
╠═══════════════════════════╣
║ Samples: {sample_count:>15} ║
║ Mean:    {mean_val:>15.2f} ║
║ Std Dev: {std_val:>15.2f} ║
║ Min:     {min_val:>15} ║
║ Max:     {max_val:>15} ║
║ Range:   {max_val - min_val:>15} ║
╚═══════════════════════════╝
        """
        stats_text.set_text(stats_str)

    return line,

# Set up animation
print("Starting live plot... (Reading from stdin)", file=sys.stderr)
print("Pipe arduino-cli output to this script:", file=sys.stderr)
print("  arduino-cli monitor -p COM5 -c baudrate=115200 | python live_plot.py", file=sys.stderr)

# Create a generator from stdin
data_gen = read_stdin()

# Animate
ani = animation.FuncAnimation(fig, update_plot, frames=data_gen,
                             interval=50, blit=False, cache_frame_data=False)

plt.tight_layout()
plt.show()

print(f"\nTotal samples collected: {sample_count}", file=sys.stderr)
