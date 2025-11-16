"""
Interactive 3D Spatial Audio GUI

Provides a 3D visualization and control interface for spatial audio positioning.
Users can drag a sound source sphere in 3D space and hear audio from that position.

Usage:
    python audio_3d_gui.py

Keyboard Controls:
    - W/A/S/D: Move source forward/left/back/right
    - Q/E: Move source up/down
    - SPACE: Play/Pause
    - R: Reset position
    - ESC: Exit

Mouse Controls:
    - Left drag: Rotate camera
    - Right drag: Pan camera
    - Scroll: Zoom in/out
    - Click on red sphere: Drag to move source (left mouse button)
"""

import numpy as np
from vpython import (
    canvas, sphere, vector, color, rate,
    scene, cylinder, curve, keysdown
)
from audio_engine import Audio3DEngine, PositionUpdate
from pathlib import Path
import argparse
import soundfile as sf
from datetime import datetime


class Audio3DGUI:
    """Interactive 3D spatial audio GUI using VPython."""

    # Configuration constants
    LISTENER_RADIUS = 0.15
    SOURCE_RADIUS = 0.25
    GRID_SIZE = 5.0
    GRID_SPACING = 0.5
    UPDATE_RATE = 60  # FPS

    def __init__(self, sofa_path: str = "mit_kemar_normal_pinna.sofa", offline_mode: bool = False):
        """
        Initialize the GUI.

        Args:
            sofa_path: Path to SOFA HRTF file
            offline_mode: If True, record to file instead of real-time playback
        """
        self.sofa_path = sofa_path
        self.offline_mode = offline_mode
        self.engine = None
        self.running = False

        # Scene setup
        self.scene = None
        self.listener_sphere = None
        self.source_sphere = None
        self.distance_line = None
        self.grid_lines = []
        self.info_text = None

        # Offline recording mode
        self.is_recording = False
        self.recorded_frames = []
        self.offline_position = 0


        print("=" * 60)
        print("3D Spatial Audio Visualization")
        print("=" * 60)

    def _setup_scene(self):
        """Initialize VPython scene."""
        self.scene = canvas(
            title="3D Spatial Audio - HRTF Spatialization",
            width=1200,
            height=800,
            background=color.black
        )

        # Scene settings
        self.scene.range = 3.0
        self.scene.camera.pos = vector(3, 2, 4)
        self.scene.center = vector(0, 0, 0)

        # Create grid
        self._create_grid()

        # Create listener (blue sphere at origin)
        self.listener_sphere = sphere(
            pos=vector(0, 0, 0),
            radius=self.LISTENER_RADIUS,
            color=color.blue,
            emissive=True,
            name="listener"
        )

        # Create source (red draggable sphere)
        self.source_sphere = sphere(
            pos=vector(1.5, 0, 0),
            radius=self.SOURCE_RADIUS,
            color=color.red,
            emissive=True,
            name="source"
        )

        # Connection line
        self.distance_line = cylinder(
            pos=self.listener_sphere.pos,
            axis=self.source_sphere.pos - self.listener_sphere.pos,
            radius=0.05,
            color=color.white,
        )

    def _create_grid(self):
        """Create reference grid on ground plane."""
        # Grid lines along X axis
        for z in np.arange(-self.GRID_SIZE, self.GRID_SIZE + self.GRID_SPACING,
                          self.GRID_SPACING):
            line = curve(
                pos=[vector(-self.GRID_SIZE, 0, z), vector(self.GRID_SIZE, 0, z)],
                color=color.gray(0.3)
            )
            self.grid_lines.append(line)

        # Grid lines along Z axis
        for x in np.arange(-self.GRID_SIZE, self.GRID_SIZE + self.GRID_SPACING,
                          self.GRID_SPACING):
            line = curve(
                pos=[vector(x, 0, -self.GRID_SIZE), vector(x, 0, self.GRID_SIZE)],
                color=color.gray(0.3)
            )
            self.grid_lines.append(line)

        # Origin axes
        axis_x = cylinder(pos=vector(0, 0, 0), axis=vector(1, 0, 0),
                         radius=0.03, color=color.red)
        axis_y = cylinder(pos=vector(0, 0, 0), axis=vector(0, 1, 0),
                         radius=0.03, color=color.green)
        axis_z = cylinder(pos=vector(0, 0, 0), axis=vector(0, 0, 1),
                         radius=0.03, color=color.cyan)

    def _update_visualization(self):
        """Update 3D visualization based on engine state."""
        if not self.engine:
            return

        # Update distance line
        if self.distance_line:
            self.distance_line.pos = self.listener_sphere.pos
            self.distance_line.axis = self.source_sphere.pos - self.listener_sphere.pos

        # Update position information
        pos = self.engine.get_position()
        az, el, dist = self.engine.processor.position_to_spherical(pos.x, pos.y, pos.z)

        # Update display
        if self.offline_mode:
            mode_str = f"[REC] Recording" if self.is_recording else "[OFFLINE]"
            time_str = f"Frames: {len(self.recorded_frames)}"
        else:
            mode_str = f"[PLAY] Playing" if self.engine.is_playing else "[PAUSE] Paused"
            time_str = f"Time: {self.engine.get_playback_position():.2f}s / {self.engine.get_duration():.2f}s"

        info = (
            f"{mode_str}  {time_str}\n"
            f"Position: X={pos.x:.2f}m  Y={pos.y:.2f}m  Z={pos.z:.2f}m\n"
            f"Azimuth: {az:.1f}°  Elevation: {el:.1f}°  Distance: {dist:.2f}m"
        )

        scene.caption = info

    def _handle_mouse_events(self):
        """Handle mouse interaction - VPython handles camera pan/zoom automatically."""
        # VPython's built-in mouse handling takes care of:
        # - Right-click drag: pan camera
        # - Scroll: zoom in/out
        # - Left-click drag: not supported in standard VPython
        # Use keyboard controls (WASD/QE) to move the source sphere instead
        pass

    def _handle_keyboard_events(self):
        """Handle keyboard input using keysdown()."""
        keys = keysdown()  # Get list of currently pressed keys
        step = 0.1
        position_changed = False

        for key in keys:
            if key == 'w':
                self.source_sphere.pos.z -= step
                position_changed = True
            elif key == 's':
                self.source_sphere.pos.z += step
                position_changed = True
            elif key == 'a':
                self.source_sphere.pos.x -= step
                position_changed = True
            elif key == 'd':
                self.source_sphere.pos.x += step
                position_changed = True
            elif key == 'q':
                self.source_sphere.pos.y += step
                position_changed = True
            elif key == 'e':
                self.source_sphere.pos.y -= step
                position_changed = True
            elif key == ' ':
                if not self.offline_mode:
                    if self.engine.is_playing:
                        self.engine.pause()
                    else:
                        self.engine.resume()
            elif key == 'b':
                if self.offline_mode:
                    self.start_recording()
            elif key == 'n':
                if self.offline_mode:
                    self.stop_recording()
            elif key == 'r':
                self.source_sphere.pos = vector(1.5, 0, 0)
                self.engine.update_position(1.5, 0, 0)
                position_changed = False  # Already updated
            elif key == 'esc':
                self.running = False
                return

        # Clamp position to valid range
        max_range = self.GRID_SIZE
        self.source_sphere.pos.x = np.clip(self.source_sphere.pos.x, -max_range, max_range)
        self.source_sphere.pos.y = np.clip(self.source_sphere.pos.y, -max_range, max_range)
        self.source_sphere.pos.z = np.clip(self.source_sphere.pos.z, -max_range, max_range)

        # Update engine if position changed
        if position_changed:
            self.engine.update_position(
                x=self.source_sphere.pos.x,
                y=self.source_sphere.pos.y,
                z=self.source_sphere.pos.z
            )

    def start_recording(self):
        """Start recording spatial audio to file."""
        if not self.offline_mode or self.is_recording:
            return

        self.is_recording = True
        self.recorded_frames = []
        self.offline_position = 0
        print("[REC] Recording started... Press N to stop and save")

    def stop_recording(self):
        """Stop recording and save to file."""
        if not self.is_recording:
            return

        self.is_recording = False

        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"spatial_audio_{timestamp}.wav"

        # Combine recorded frames into stereo array
        if len(self.recorded_frames) > 0:
            stereo_audio = np.concatenate(self.recorded_frames, axis=0)

            # Save to WAV file
            sr = self.engine.get_sample_rate()
            sf.write(output_file, stereo_audio, sr)

            duration = len(stereo_audio) / sr
            print(f"[SAVED] {output_file} ({duration:.2f}s, {len(self.recorded_frames)} frames)")
        else:
            print("[INFO] No frames recorded")

        self.recorded_frames = []

    def process_offline_frame(self):
        """Process audio frame in offline mode (no real-time constraints)."""
        if not self.is_recording or self.engine.audio_data is None:
            return

        # Read chunk of audio (larger chunks OK since no timing constraint)
        chunk_size = 4096

        start_idx = self.offline_position
        end_idx = min(start_idx + chunk_size, len(self.engine.audio_data))

        if start_idx >= len(self.engine.audio_data):
            # Reached end of audio
            print("[INFO] Reached end of audio, stopping recording")
            self.stop_recording()
            return

        audio_chunk = self.engine.audio_data[start_idx:end_idx]

        # Get current position
        pos = self.engine.get_position()
        az, el, dist = self.engine.processor.position_to_spherical(pos.x, pos.y, pos.z)

        # Apply HRTF (NO TIME PRESSURE = NO UNDERFLOWS!)
        left, right = self.engine.processor.spatialize_audio(
            audio_chunk, azimuth_deg=az, elevation_deg=el, distance_m=dist
        )

        # Store as stereo frame
        stereo_frame = np.stack([left, right], axis=1)
        self.recorded_frames.append(stereo_frame)

        # Advance position
        self.offline_position = end_idx

    def load_audio(self, audio_path: str):
        """Load audio file."""
        if not Path(audio_path).exists():
            print(f"[ERROR] Audio file not found: {audio_path}")
            return False

        try:
            self.engine.load_audio(audio_path)
            self.audio_file = audio_path
            return True
        except Exception as e:
            print(f"[ERROR] Error loading audio: {e}")
            return False

    def initialize_engine(self):
        """Initialize the audio engine."""
        try:
            self.engine = Audio3DEngine(self.sofa_path)
            print(f"[OK] Audio engine initialized")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to initialize engine: {e}")
            return False

    def run(self, audio_path: str):
        """
        Run the application.

        Args:
            audio_path: Path to audio file to play
        """
        # Initialize
        if not self.initialize_engine():
            return

        if not self.load_audio(audio_path):
            return

        # Setup scene
        self._setup_scene()
        self.running = True

        # Start audio based on mode
        if not self.offline_mode:
            try:
                self.engine.start(buffer_size=128)
            except Exception as e:
                print(f"[ERROR] Failed to start audio: {e}")
                return

        print("\n" + "=" * 60)
        print("Controls:")
        print("  W/A/S/D - Move source forward/left/back/right")
        print("  Q/E     - Move source up/down")
        if self.offline_mode:
            print("  B       - Begin recording")
            print("  N       - End recording (save file)")
        else:
            print("  Space   - Play/Pause")
        print("  R       - Reset position")
        print("  ESC     - Exit")
        print("=" * 60 + "\n")

        # Main loop
        try:
            while self.running:
                rate(self.UPDATE_RATE)

                # Process offline frame if recording
                if self.offline_mode:
                    self.process_offline_frame()

                # Update visualization
                self._update_visualization()

                # Handle input
                self._handle_keyboard_events()
                self._handle_mouse_events()

        except KeyboardInterrupt:
            print("\n[STOP] Interrupted by user")
        finally:
            self.cleanup()

    def cleanup(self):
        """Cleanup and shutdown."""
        print("\nCleaning up...")
        if self.engine:
            self.engine.stop()
        self.running = False
        print("[OK] Shutdown complete")


def find_audio_files():
    """Find available audio files in the project directory."""
    current_dir = Path.cwd()
    audio_files = []

    # Look for common audio formats
    for pattern in ['*.wav', '*.mp3', '*.ogg', '*.flac']:
        audio_files.extend(current_dir.glob(pattern))

    return sorted([str(f.name) for f in audio_files])


def main():
    """Main entry point."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="3D Spatial Audio with HRTF Spatialization",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python audio_3d_gui.py          # Real-time mode
  python audio_3d_gui.py --file   # Offline recording mode (no underflows)
        """
    )
    parser.add_argument('--file', action='store_true',
                       help='Offline mode: Record spatial audio to file instead of real-time playback')
    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("3D Spatial Audio with HRTF Spatialization")
    if args.file:
        print("MODE: Offline Recording (--file)")
    else:
        print("MODE: Real-time Playback")
    print("=" * 60 + "\n")


    # Default to first audio file
    audio_path = "testMusic.mp3"

    # Check for SOFA file
    sofa_path = "mit_kemar_normal_pinna.sofa"
    if not Path(sofa_path).exists():
        print(f"[ERROR] SOFA file not found: {sofa_path}")
        print("  Please ensure the MIT KEMAR SOFA file is in the current directory.\n")
        return

    # Create and run GUI (pass offline_mode flag)
    gui = Audio3DGUI(sofa_path, offline_mode=args.file)
    gui.run(audio_path)


if __name__ == "__main__":
    main()
