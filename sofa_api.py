"""
SOFA HRTF API - Clean interface for spatial audio processing

This module provides a simple, programmatic API for loading SOFA files
and applying Head-Related Transfer Functions (HRTFs) to audio signals.
"""

import numpy as np
from scipy.signal import fftconvolve
import pysofaconventions as sofa


class HRTFProcessor:
    """
    Simplified HRTF processor for spatial audio synthesis.

    Usage:
        processor = HRTFProcessor("mit_kemar_normal_pinna.sofa")
        left, right = processor.spatialize_audio(audio, azimuth=45, elevation=0, distance=1.5)
    """

    def __init__(self, sofa_path: str):
        """
        Load a SOFA file and initialize the HRTF processor.

        Args:
            sofa_path: Path to the SOFA file

        Raises:
            FileNotFoundError: If SOFA file doesn't exist
            RuntimeError: If SOFA file is invalid
        """
        self.sofa_path = sofa_path
        self.hrtf = None
        self.source_positions = None
        self.impulse_responses = None
        self.sample_rate = None
        self.az_list = None
        self.el_list = None

        self._load_sofa()

    def _load_sofa(self):
        """Load and validate SOFA file."""
        try:
            self.hrtf = sofa.SOFAFile(self.sofa_path, 'r')
        except Exception as e:
            raise RuntimeError(f"Failed to load SOFA file '{self.sofa_path}': {e}")

        try:
            # Load source positions: shape (M, 3) = [azimuth, elevation, distance]
            self.source_positions = self.hrtf.getVariableValue("SourcePosition")
            self.az_list = self.source_positions[:, 0]
            self.el_list = self.source_positions[:, 1]

            # Load impulse responses: shape (M, R, N)
            # M = number of directions, R = 2 ears, N = IR length
            self.impulse_responses = self.hrtf.getDataIR()

            # Load sampling rate
            sr_array = self.hrtf.getVariableValue("Data.SamplingRate")
            self.sample_rate = int(sr_array[0])

            print(f"[OK] Loaded SOFA file: {self.sofa_path}")
            print(f"  Directions: {self.impulse_responses.shape[0]}, "
                  f"IR length: {self.impulse_responses.shape[2]}, "
                  f"Sample rate: {self.sample_rate} Hz")
        except Exception as e:
            raise RuntimeError(f"Failed to parse SOFA data: {e}")

    def position_to_spherical(self, x: float, y: float, z: float) -> tuple:
        """
        Convert 3D Cartesian coordinates to spherical coordinates.

        Args:
            x, y, z: Position in meters (y is vertical)

        Returns:
            (azimuth_deg, elevation_deg, distance_m)
        """
        distance = np.sqrt(x**2 + y**2 + z**2)

        if distance < 1e-6:
            # Near origin - undefined angles
            azimuth = 0.0
            elevation = 0.0
        else:
            # Azimuth: angle in horizontal plane (0° = forward, 90° = left)
            azimuth = np.degrees(np.arctan2(x, z))
            # Elevation: angle above horizontal (-90° = below, 0° = horizontal, 90° = above)
            elevation = np.degrees(np.arcsin(y / distance))

        return float(azimuth), float(elevation), float(distance)

    def spherical_to_position(self, azimuth_deg: float, elevation_deg: float,
                            distance_m: float) -> tuple:
        """
        Convert spherical coordinates to 3D Cartesian coordinates.

        Args:
            azimuth_deg: Azimuth angle in degrees (0° = forward)
            elevation_deg: Elevation angle in degrees (0° = horizontal)
            distance_m: Distance in meters

        Returns:
            (x, y, z) position tuple
        """
        az_rad = np.radians(azimuth_deg)
        el_rad = np.radians(elevation_deg)

        x = distance_m * np.sin(az_rad) * np.cos(el_rad)
        y = distance_m * np.sin(el_rad)
        z = distance_m * np.cos(az_rad) * np.cos(el_rad)

        return (float(x), float(y), float(z))

    def _find_closest_direction(self, azimuth_deg: float, elevation_deg: float) -> int:
        """
        Find the closest measured HRTF direction to the requested angles.

        Args:
            azimuth_deg: Desired azimuth angle
            elevation_deg: Desired elevation angle

        Returns:
            Index of closest direction in the HRTF dataset
        """
        diff_az = self.az_list - azimuth_deg
        diff_el = self.el_list - elevation_deg
        dist2 = diff_az**2 + diff_el**2
        idx = np.argmin(dist2)
        return int(idx)

    def _distance_to_gain(self, distance_m: float, min_dist: float = 0.5,
                          max_dist: float = 3.0) -> float:
        """
        Convert distance to loudness gain using inverse square law approximation.

        Args:
            distance_m: Distance in meters
            min_dist: Minimum distance for maximum gain
            max_dist: Maximum distance for minimum gain

        Returns:
            Gain factor (0.2 to 1.0)
        """
        clamped_dist = np.clip(distance_m, min_dist, max_dist)
        gain = (max_dist - clamped_dist) / (max_dist - min_dist) * 0.8 + 0.2
        return float(np.clip(gain, 0.2, 1.0))

    def get_hrtf(self, azimuth_deg: float, elevation_deg: float) -> tuple:
        """
        Get the HRTF filters for given direction.

        Args:
            azimuth_deg: Azimuth angle in degrees
            elevation_deg: Elevation angle in degrees

        Returns:
            (hrir_left, hrir_right) - impulse response arrays for each ear
        """
        idx = self._find_closest_direction(azimuth_deg, elevation_deg)
        hrir_left = self.impulse_responses[idx, 0, :]
        hrir_right = self.impulse_responses[idx, 1, :]
        return hrir_left, hrir_right

    def spatialize_audio(self, audio: np.ndarray, azimuth_deg: float = 0.0,
                        elevation_deg: float = 0.0, distance_m: float = 1.0) -> tuple:
        """
        Apply HRTF to mono audio to create stereo spatial effect.

        Args:
            audio: Mono audio signal (numpy array, float32)
            azimuth_deg: Source azimuth angle in degrees
            elevation_deg: Source elevation angle in degrees
            distance_m: Source distance in meters

        Returns:
            (left_channel, right_channel) - stereo output arrays
        """
        if audio.ndim != 1:
            raise ValueError("Input audio must be mono (1D array)")

        # Get distance-based gain
        gain = self._distance_to_gain(distance_m)
        audio_with_gain = audio * gain

        # Get HRTF filters for this direction
        hrir_left, hrir_right = self.get_hrtf(azimuth_deg, elevation_deg)

        # Apply convolution
        left_channel = fftconvolve(audio_with_gain, hrir_left, mode='same')
        right_channel = fftconvolve(audio_with_gain, hrir_right, mode='same')

        return left_channel.astype(np.float32), right_channel.astype(np.float32)

    def get_sample_rate(self) -> int:
        """Get the sample rate of the HRTF dataset."""
        return self.sample_rate

    def close(self):
        """Close the SOFA file."""
        if self.hrtf:
            try:
                self.hrtf.close()
            except Exception:
                pass


# Convenience functions for quick usage
def spatialize_simple(sofa_path: str, audio: np.ndarray, azimuth: float = 0.0,
                     elevation: float = 0.0, distance: float = 1.0) -> tuple:
    """
    Quick function to spatialize audio without creating processor object.

    Args:
        sofa_path: Path to SOFA file
        audio: Mono audio signal
        azimuth: Azimuth angle in degrees
        elevation: Elevation angle in degrees
        distance: Distance in meters

    Returns:
        (left_channel, right_channel) - stereo output
    """
    processor = HRTFProcessor(sofa_path)
    try:
        return processor.spatialize_audio(audio, azimuth, elevation, distance)
    finally:
        processor.close()
