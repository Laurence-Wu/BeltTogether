import numpy as np
from scipy.signal import fftconvolve
import soundfile as sf
import pysofaconventions as sofa


# ------------------------------------------------------------
# 1. Load the MIT KEMAR "normal pinna" SOFA file
# ------------------------------------------------------------
SOFA_PATH = "mit_kemar_normal_pinna.sofa"    # make sure this file is in the same folder

hrtf = sofa.SOFAFile(SOFA_PATH, 'r')

# Source positions: columns = [azimuth, elevation, distance]
# Units are typically: degrees, degrees, meters.
source_pos = hrtf.getVariableValue("SourcePosition")  # shape: (M, 3)
az_list = source_pos[:, 0]
el_list = source_pos[:, 1]

# Impulse responses: shape = (M, R, N)
# M = number of directions, R = 2 ears, N = IR length
ir = hrtf.getDataIR()
# Sampling rate (comes as an array like [44100.])
sr = int(hrtf.getVariableValue("Data.SamplingRate")[0])

print(f"Loaded SOFA file: {SOFA_PATH}")
print(f"Number of directions: {ir.shape[0]}, IR length: {ir.shape[2]}, samplerate: {sr} Hz")


# ------------------------------------------------------------
# 2. Helper: find closest HRTF index for a given (az, el)
# ------------------------------------------------------------
def find_closest_direction(az_deg, el_deg):
    """
    Returns index of the closest measured direction in the KEMAR dataset
    to the requested (az_deg, el_deg).
    """
    # simple squared distance in angle space
    diff_az = az_list - az_deg
    diff_el = el_list - el_deg
    dist2 = diff_az**2 + diff_el**2
    idx = np.argmin(dist2)
    return idx


# ------------------------------------------------------------
# 3. Helper: simple mono beep generator
# ------------------------------------------------------------
def make_beep(freq=1000.0, length=0.15, sr=44100):
    """Generate a short sine beep with fade in/out."""
    t = np.linspace(0, length, int(sr * length), endpoint=False)
    beep = np.sin(2 * np.pi * freq * t)

    # apply a short fade to avoid clicks
    fade_len = int(0.01 * sr)
    env = np.ones_like(beep)
    env[:fade_len] *= np.linspace(0.0, 1.0, fade_len)
    env[-fade_len:] *= np.linspace(1.0, 0.0, fade_len)
    return (beep * env).astype(np.float32)


# ------------------------------------------------------------
# 4. Fake ToF events (you will replace this later)
# Each event: (time_sec, azimuth_deg, elevation_deg, distance_m)
# ------------------------------------------------------------
events = [
    (0.5,  -60,   0, 1.5),   # left-front
    (1.5,    0,  20, 0.8),   # slightly above straight ahead
    (2.5,  +60, -10, 2.0),   # right-front, slightly below
]

total_duration = 4.0               # seconds
num_samples = int(total_duration * sr)

left_mix  = np.zeros(num_samples, dtype=np.float32)
right_mix = np.zeros(num_samples, dtype=np.float32)

# Pre-generate a base beep
base_beep = make_beep(freq=1200.0, length=0.15, sr=sr)


# ------------------------------------------------------------
# 5. Render each event using KEMAR HRTF
# ------------------------------------------------------------
for (t_sec, az_deg, el_deg, dist_m) in events:
    start = int(t_sec * sr)

    # Distance → loudness (simple mapping: closer = louder)
    min_d, max_d = 0.5, 3.0
    d_clamped = np.clip(dist_m, min_d, max_d)
    gain = (max_d - d_clamped) / (max_d - min_d) * 0.8 + 0.2  # between 0.2 and 1.0

    mono = base_beep * gain

    # Find closest KEMAR direction
    idx = find_closest_direction(az_deg, el_deg)
    hrir_left = ir[idx, 0, :]   # left ear response
    hrir_right = ir[idx, 1, :]  # right ear response

    # Convolve mono beep with left/right HRIRs
    left  = fftconvolve(mono, hrir_left)
    right = fftconvolve(mono, hrir_right)

    # Mix into main buffers
    end = start + len(left)
    if end > num_samples:
        end = num_samples
        left  = left[:end - start]
        right = right[:end - start]

    left_mix[start:end]  += left.astype(np.float32)
    right_mix[start:end] += right.astype(np.float32)

# Avoid clipping
max_val = max(np.max(np.abs(left_mix)), np.max(np.abs(right_mix)), 1e-6)
if max_val > 1.0:
    left_mix  /= max_val
    right_mix /= max_val

# ------------------------------------------------------------
# 6. Write stereo WAV
# ------------------------------------------------------------
stereo = np.stack([left_mix, right_mix], axis=1)
sf.write("kemar_demo.wav", stereo, sr)

print("Done! Wrote 'kemar_demo.wav'. Listen with headphones for 3D effect.")
