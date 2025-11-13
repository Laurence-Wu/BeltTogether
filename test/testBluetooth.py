import pyaudio
import numpy as np


def list_audio_devices():
    """
    List all available audio devices and identify Bluetooth headphones.
    """
    p = pyaudio.PyAudio()

    print("=" * 60)
    print("Available Audio Devices")
    print("=" * 60 + "\n")

    bluetooth_devices = []

    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        device_name = info['name']
        channels = info['maxOutputChannels']
        sample_rate = int(info['defaultSampleRate'])

        # Check if it's a Bluetooth device and output capable
        if channels > 0 and ('bluetooth' in device_name.lower() or 'headset' in device_name.lower() or 'headphone' in device_name.lower()):
            bluetooth_devices.append((i, device_name, sample_rate))
            print(f"[{i}] {device_name} (Output Channels: {channels}, Sample Rate: {sample_rate} Hz) ✓ BLUETOOTH")
        else:
            print(f"[{i}] {device_name} (Output Channels: {channels})")

    print()
    p.terminate()
    return bluetooth_devices


def play_tone(device_index, frequency=440, duration=2, sample_rate=44100):
    """
    Play a simple tone to test the audio device.

    Args:
        device_index: Index of the audio device
        frequency: Frequency in Hz (default 440 Hz = A note)
        duration: Duration in seconds
        sample_rate: Sample rate in Hz
    """
    p = pyaudio.PyAudio()

    try:
        # Get device info
        device_info = p.get_device_info_by_index(device_index)
        channels = int(device_info['maxOutputChannels'])

        print(f"Playing {frequency} Hz tone for {duration} seconds on device: {device_info['name']}")

        # Generate audio data (sine wave)
        samples = int(sample_rate * duration)
        t = np.linspace(0, duration, samples)
        wave = np.sin(2 * np.pi * frequency * t).astype(np.float32)

        # Open audio stream
        stream = p.open(
            format=pyaudio.paFloat32,
            channels=channels,
            rate=sample_rate,
            output=True,
            output_device_index=device_index
        )

        # Play the sound
        stream.write(wave.tobytes())

        # Clean up
        stream.stop_stream()
        stream.close()

        print("Playback complete!")

    except Exception as e:
        print(f"Error playing sound: {e}")
    finally:
        p.terminate()


def play_audio_file(device_index, file_path):
    """
    Play an audio file on the specified device.

    Args:
        device_index: Index of the audio device
        file_path: Path to the audio file (.wav, .mp3, etc.)
    """
    try:
        from pydub import AudioSegment
        import io

        # Determine file format
        file_ext = file_path.lower().split('.')[-1]

        print(f"Playing audio file: {file_path}")
        print(f"Format: {file_ext.upper()}")

        # Load audio file
        print("Loading audio file...")
        audio = AudioSegment.from_file(file_path, format=file_ext)

        # Get audio parameters
        n_channels = audio.channels
        sample_rate = audio.frame_rate
        duration = len(audio) / 1000.0

        print(f"Channels: {n_channels}, Sample Rate: {sample_rate} Hz, Duration: {duration:.2f}s")

        # Get audio data as bytes
        audio_data = audio.raw_data

        # Open audio stream
        p = pyaudio.PyAudio()
        stream = p.open(
            format=pyaudio.paInt16,
            channels=n_channels,
            rate=sample_rate,
            output=True,
            output_device_index=device_index
        )

        # Play audio in chunks
        chunk_size = 4096
        for i in range(0, len(audio_data), chunk_size):
            chunk = audio_data[i:i + chunk_size]
            stream.write(chunk)

        # Clean up
        stream.stop_stream()
        stream.close()
        p.terminate()

        print("Playback complete!")

    except Exception as e:
        print(f"Error playing audio file: {e}")
        print(f"Make sure pydub is installed: pip install pydub")


# Main execution
if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Bluetooth Headphone Audio Test")
    print("=" * 60 + "\n")

    # List all devices
    bluetooth_devices = list_audio_devices()

    if not bluetooth_devices:
        print("No Bluetooth audio devices found.")
        print("Make sure your Bluetooth headphones are paired and set as default device.\n")
    else:
        print(f"\nFound {len(bluetooth_devices)} Bluetooth device(s):\n")

        # Display Bluetooth devices with numbering starting from 1
        for i, (device_index, device_name, sample_rate) in enumerate(bluetooth_devices, 1):
            print(f"({i}) Device [{device_index}]: {device_name}")

        print()

        try:
            user_input = input("Select Bluetooth device number (1-" + str(len(bluetooth_devices)) + ", or 0 to exit): ").strip().replace('[', '').replace(']', '')
            choice = int(user_input)

            if choice == 0:
                print("Exiting...")
            elif 1 <= choice <= len(bluetooth_devices):
                device_index, device_name, sample_rate = bluetooth_devices[choice - 1]

                print(f"\nYou selected: {device_name}\n")

                # Menu for what to play
                print("What would you like to play?")
                print("[1] Test tone (440 Hz)")
                print("[2] Test tone (1000 Hz)")
                print("[3] Play audio file")
                print("[0] Exit")

                action = input("\nEnter your choice: ")

                if action == "1":
                    play_tone(device_index, frequency=440, duration=2, sample_rate=sample_rate)
                elif action == "2":
                    play_tone(device_index, frequency=1000, duration=2, sample_rate=sample_rate)
                elif action == "3":
                    file_path = input("Enter the path to your audio file: ")
                    play_audio_file(device_index, file_path)
                elif action == "0":
                    print("Exiting...")
            else:
                print("Invalid selection.")

        except ValueError:
            print("Invalid input.")

    print("\nDone!")
