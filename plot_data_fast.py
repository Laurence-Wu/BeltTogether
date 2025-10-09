#!/usr/bin/env python3
"""
Plot ADC data from CSV file using matplotlib (optimized for large files)
"""

import matplotlib.pyplot as plt
import numpy as np

# Read CSV file efficiently (only what we need)
print("Reading data.csv...")

time_data = []
sample_data = []

# Read file line by line to avoid memory issues
with open('data_amplified.csv', 'r') as f:
    header = f.readline()  # Skip header

    line_count = 0
    for line in f:
        parts = line.strip().split(',')
        if len(parts) >= 2:
            try:
                time_data.append(float(parts[0]))
                sample_data.append(int(parts[1]))
                line_count += 1

                # Optionally limit samples for faster plotting
                if line_count >= 100000:  # Plot first 100k samples
                    print(f"Limiting to first {line_count} samples for performance...")
                    break

            except ValueError:
                continue

print(f"Loaded {len(sample_data)} samples")

# Convert to numpy arrays for faster processing
time_array = np.array(time_data)
sample_array = np.array(sample_data)

# Convert time to milliseconds
time_ms = time_array / 1000.0

# Create figure with subplots
fig, axes = plt.subplots(3, 1, figsize=(14, 10))

# Plot 1: Sample values over time
axes[0].plot(time_ms, sample_array, linewidth=0.5, color='blue')
axes[0].set_xlabel('Time (ms)')
axes[0].set_ylabel('ADC Value')
axes[0].set_title(f'ADC Samples vs Time ({len(sample_data)} samples)')
axes[0].grid(True, alpha=0.3)

# Plot 2: Zoomed view (first 1000 samples)
zoom_samples = min(1000, len(sample_array))
axes[1].plot(time_ms[:zoom_samples], sample_array[:zoom_samples],
             linewidth=1, color='red', marker='o', markersize=2)
axes[1].set_xlabel('Time (ms)')
axes[1].set_ylabel('ADC Value')
axes[1].set_title(f'Zoomed View (First {zoom_samples} samples)')
axes[1].grid(True, alpha=0.3)

# Plot 3: Histogram of values
axes[2].hist(sample_array, bins=100, color='green', alpha=0.7, edgecolor='black')
axes[2].set_xlabel('ADC Value')
axes[2].set_ylabel('Frequency')
axes[2].set_title('Distribution of ADC Values')
axes[2].grid(True, alpha=0.3)

# Add statistics text
mean_val = np.mean(sample_array)
std_val = np.std(sample_array)
min_val = np.min(sample_array)
max_val = np.max(sample_array)

stats_text = f'Mean: {mean_val:.2f}\nStd: {std_val:.2f}\nMin: {min_val}\nMax: {max_val}'
axes[2].text(0.02, 0.98, stats_text, transform=axes[2].transAxes,
             verticalalignment='top', fontsize=10,
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

# Print statistics
print("\n=== Statistics ===")
print(f"Mean: {mean_val:.2f}")
print(f"Std Dev: {std_val:.2f}")
print(f"Min: {min_val}")
print(f"Max: {max_val}")
print(f"Range: {max_val - min_val}")

# Calculate sample rate if we have time data
if len(time_array) > 1:
    time_diff = np.diff(time_array)
    avg_interval_us = np.mean(time_diff)
    sample_rate_hz = 1_000_000 / avg_interval_us if avg_interval_us > 0 else 0
    print(f"\nAverage sample interval: {avg_interval_us:.2f} μs")
    print(f"Estimated sample rate: {sample_rate_hz:.2f} Hz")

plt.tight_layout()
plt.savefig('adc_plot.png', dpi=150)
print("\nPlot saved as adc_plot.png")
plt.show()
