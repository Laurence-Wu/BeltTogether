"""
Real-time 3D Audio Engine

Handles real-time audio playback with dynamic HRTF spatialization.
Updates HRTF parameters based on sound source position in real-time.
"""

import numpy as np
import sounddevice as sd
import soundfile as sf
from threading import Lock
from sofa_api import HRTFProcessor


class PositionUpdate:
    """Container for sound source position."""

    def __init__(self, x: float = 0.0, y: float = 0.0, z: float = 0.0):
        self.x = x
        self.y = y
        self.z = z

    def __repr__(self):
        return f"Position(x={self.x:.2f}, y={self.y:.2f}, z={self.z:.2f})"


class Audio3DEngine:
    """
    Real-time 3D spatial audio engine with dynamic HRTF processing.

    Usage:
        engine = Audio3DEngine("mit_kemar_normal_pinna.sofa")
        engine.load_audio("music.wav")
        engine.start()

        # In main loop:
        engine.update_position(x=1.0, y=0.0, z=0.0)

        # When done:
        engine.stop()
    """

    def __init__(self, sofa_path: str, output_device: int = None):
        """
        Initialize the audio engine.

        Args:
            sofa_path: Path to SOFA HRTF file
            output_device: Audio device index (None = default)
        """
        self.sofa_path = sofa_path
        self.output_device = output_device
        self.processor = HRTFProcessor(sofa_path)

        # Audio data
        self.audio_data = None
        self.audio_position = 0
        self.sample_rate = self.processor.get_sample_rate()

        # Position tracking
        self.current_position = PositionUpdate()
        self.position_lock = Lock()

        # Playback control
        self.is_playing = False
        self.is_running = False

        # Audio stream
        self.stream = None

        # Performance monitoring
        self.underruns = 0

    def load_audio(self, audio_path: str, resample_rate: int = None):
        """
        Load audio file.

        Args:
            audio_path: Path to audio file (WAV, FLAC, OGG, etc.)
            resample_rate: Target sample rate (None = keep original)

        Raises:
            FileNotFoundError: If audio file not found
            RuntimeError: If audio loading fails
        """
        try:
            audio_data, file_sr = sf.read(audio_path, dtype='float32')

            # Convert stereo to mono if needed
            if audio_data.ndim > 1:
                audio_data = np.mean(audio_data, axis=1)

            # Resample if needed
            if resample_rate and resample_rate != file_sr:
                from scipy.signal import resample
                num_samples = int(len(audio_data) * resample_rate / file_sr)
                audio_data = resample(audio_data, num_samples)
                file_sr = resample_rate

            # Ensure sample rate matches HRTF
            if file_sr != self.sample_rate:
                from scipy.signal import resample
                num_samples = int(len(audio_data) * self.sample_rate / file_sr)
                audio_data = resample(audio_data, num_samples)

            self.audio_data = audio_data
            self.audio_position = 0

            print(f"[OK] Loaded audio: {audio_path}")
            print(f"  Duration: {len(self.audio_data) / self.sample_rate:.2f}s, "
                  f"Sample rate: {self.sample_rate} Hz")
        except Exception as e:
            raise RuntimeError(f"Failed to load audio file '{audio_path}': {e}")

    def update_position(self, x: float = 0.0, y: float = 0.0, z: float = 0.0):
        """
        Update the sound source position.

        Args:
            x, y, z: Position in meters (y is vertical)
        """
        with self.position_lock:
            self.current_position.x = x
            self.current_position.y = y
            self.current_position.z = z

    def get_position(self) -> PositionUpdate:
        """Get current sound source position."""
        with self.position_lock:
            return PositionUpdate(self.current_position.x,
                                 self.current_position.y,
                                 self.current_position.z)

    def _audio_callback(self, outdata, frames, time_info, status):
        """
        Callback for audio streaming.
        Called by sounddevice for each audio buffer.
        """
        if status:
            print(f"[WARN] Audio status: {status}")
            if status.output_underflow:
                self.underruns += 1

        if not self.is_playing or self.audio_data is None:
            outdata.fill(0)
            return

        # Get current position
        pos = self.get_position()

        # Convert 3D position to spherical coordinates
        az, el, dist = self.processor.position_to_spherical(pos.x, pos.y, pos.z)

        # Read audio chunk
        start_idx = self.audio_position
        end_idx = start_idx + frames

        if end_idx > len(self.audio_data):
            # Loop audio
            chunk = self.audio_data[start_idx:]
            remaining = frames - len(chunk)
            if remaining > 0:
                chunk = np.concatenate([chunk, self.audio_data[:remaining]])
            self.audio_position = remaining
        else:
            chunk = self.audio_data[start_idx:end_idx]
            self.audio_position = end_idx

        # Apply HRTF processing
        left, right = self.processor.spatialize_audio(chunk, az, el, dist)

        # Normalize to prevent clipping
        max_val = max(np.max(np.abs(left)), np.max(np.abs(right)), 1e-6)
        if max_val > 1.0:
            left /= max_val
            right /= max_val

        # Output stereo
        outdata[:, 0] = left
        outdata[:, 1] = right

    def start(self, buffer_size: int = 128):
        """
        Start audio playback.

        Args:
            buffer_size: Audio buffer size in samples (smaller = lower latency)
        """
        if self.audio_data is None:
            raise RuntimeError("No audio loaded. Call load_audio() first.")

        if self.is_running:
            return

        self.is_running = True
        self.is_playing = True

        try:
            self.stream = sd.OutputStream(
                channels=2,
                samplerate=self.sample_rate,
                device=self.output_device,
                blocksize=buffer_size,
                callback=self._audio_callback,
                latency='low'
            )
            self.stream.start()
            print(f"[OK] Audio playback started")
        except Exception as e:
            self.is_running = False
            raise RuntimeError(f"Failed to start audio stream: {e}")

    def pause(self):
        """Pause playback."""
        self.is_playing = False
        print("[PAUSE] Playback paused")

    def resume(self):
        """Resume playback."""
        if not self.is_running:
            raise RuntimeError("Audio stream not running. Call start() first.")
        self.is_playing = True
        print("[PLAY] Playback resumed")

    def stop(self):
        """Stop audio playback and cleanup."""
        if not self.is_running:
            return

        self.is_playing = False
        self.is_running = False

        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None

        print("[STOP] Playback stopped")

    def get_playback_position(self) -> float:
        """Get current playback position in seconds."""
        if self.sample_rate == 0:
            return 0.0
        return self.audio_position / self.sample_rate

    def get_duration(self) -> float:
        """Get total audio duration in seconds."""
        if self.audio_data is None or self.sample_rate == 0:
            return 0.0
        return len(self.audio_data) / self.sample_rate

    def is_audio_loaded(self) -> bool:
        """Check if audio is loaded."""
        return self.audio_data is not None

    def get_sample_rate(self) -> int:
        """Get the sample rate in Hz."""
        return self.sample_rate

    def get_info(self) -> dict:
        """Get engine information."""
        return {
            'sofa_path': self.sofa_path,
            'sample_rate': self.sample_rate,
            'audio_loaded': self.is_audio_loaded(),
            'is_playing': self.is_playing,
            'duration': self.get_duration(),
            'position': self.get_playback_position(),
            'underruns': self.underruns,
        }

    def __del__(self):
        """Cleanup on destruction."""
        self.stop()
        if self.processor:
            self.processor.close()
