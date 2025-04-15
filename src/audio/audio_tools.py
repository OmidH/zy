import threading
import pyaudio
from pydub import AudioSegment
from pydub.playback import play

from ..helper.logger import getLogger

logging = getLogger()

stop_recording = False


def stop():
    global stop_recording
    input("Press Enter to stop recording...")
    stop_recording = True


def record_audio(filename):
    chunk = 1024
    sample_format = pyaudio.paInt16
    channels = 1
    fs = 44100
    stop_recording = threading.Event()

    p = pyaudio.PyAudio()

    stream = p.open(format=sample_format,
                    channels=channels,
                    rate=fs,
                    frames_per_buffer=chunk,
                    input=True)

    frames = []

    stop_thread = threading.Thread(target=lambda: (input("Press Enter to stop recording..."), stop_recording.set()))
    stop_thread.start()

    print('Recording... Press Enter to stop')
    while not stop_recording.is_set():
        data = stream.read(chunk, exception_on_overflow=False)
        frames.append(data)

    stream.stop_stream()
    stream.close()
    p.terminate()
    stop_thread.join()

    # Save the recorded data as an MP3 file
    sound = AudioSegment(
        data=b''.join(frames),
        sample_width=p.get_sample_size(sample_format),
        frame_rate=fs,
        channels=channels
    )
    sound.export(filename, format="mp3")
    logging.info(f'Recording saved as {filename}')


def play_audio(filename):
    logging.info(f'Playing ... {filename}')
    try:
        audio = AudioSegment.from_mp3(filename)
        play(audio)
    except Exception as e:
        print(f"Error playing {filename}: {e}")
