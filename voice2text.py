import numpy as np
import pyaudio
import wave
import webrtcvad
import time
import os
from typing import Optional, Tuple
from faster_whisper import WhisperModel
import tempfile

class VoiceListener:
    def __init__(self, model_size="base", device="cpu"):
        """
        Initialize the voice listener with Faster Whisper model
        
        Args:
            model_size: Size of the Whisper model ("tiny", "base", "small", "medium", "large")
            device: Device to run the model on ("cpu" or "cuda" for GPU)
        """
        # Initialize the Whisper model
        self.model = WhisperModel(model_size, device=device)
        
        # Audio recording parameters
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 16000
        self.CHUNK_DURATION_MS = 30  # 30ms chunks
        self.CHUNK_SIZE = int(self.RATE * self.CHUNK_DURATION_MS / 1000)
        self.SILENCE_THRESHOLD = 2.0  # seconds of silence to stop recording
        
        # Initialize VAD (Voice Activity Detector)
        self.vad = webrtcvad.Vad(3)  # Aggressiveness mode (3 is most aggressive)

    def record_audio(self) -> Tuple[np.ndarray, bool]:
        """
        Record audio until silence is detected
        
        Returns:
            Tuple of audio data as numpy array and boolean indicating if speech was detected
        """
        p = pyaudio.PyAudio()
        
        stream = p.open(
            format=self.FORMAT,
            channels=self.CHANNELS,
            rate=self.RATE,
            input=True,
            frames_per_buffer=self.CHUNK_SIZE
        )
        
        print("Listening... (speak now)")
        
        # Buffer to store audio data
        audio_data = []
        silent_chunks = 0
        voice_detected = False
        max_silent_chunks = int(self.SILENCE_THRESHOLD * 1000 / self.CHUNK_DURATION_MS)
        
        try:
            # Keep recording until enough silence is detected after speech
            while True:
                chunk = stream.read(self.CHUNK_SIZE)
                audio_data.append(chunk)
                
                # Check if this chunk contains speech
                try:
                    is_speech = self.vad.is_speech(chunk, self.RATE)
                except:
                    is_speech = False
                
                if is_speech:
                    voice_detected = True
                    silent_chunks = 0
                elif voice_detected:
                    silent_chunks += 1
                
                # If we've detected speech before and now have enough silence, stop recording
                if voice_detected and silent_chunks >= max_silent_chunks:
                    break
                
                # Visual feedback
                if is_speech:
                    print(".", end="", flush=True)
                elif voice_detected:
                    print("-", end="", flush=True)
        
        finally:
            print("\nProcessing...")
            stream.stop_stream()
            stream.close()
            p.terminate()
        
        # Convert audio chunks to numpy array
        audio_data = b''.join(audio_data)
        audio_np = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
        
        return audio_np, voice_detected

    def save_audio_to_temp_file(self, audio_data: np.ndarray) -> str:
        """Save audio data to a temporary WAV file"""
        temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        temp_file.close()
        
        with wave.open(temp_file.name, 'wb') as wf:
            wf.setnchannels(self.CHANNELS)
            wf.setsampwidth(2)  # 16-bit audio
            wf.setframerate(self.RATE)
            wf.writeframes((audio_data * 32768).astype(np.int16).tobytes())
        
        return temp_file.name

    def transcribe(self, audio_file: str) -> str:
        """Transcribe audio file using Faster Whisper"""
        segments, info = self.model.transcribe(audio_file, beam_size=5)
        
        # Combine all segments into one text
        transcription = " ".join([segment.text for segment in segments])
        
        # Clean up the temporary file
        os.remove(audio_file)
        
        return transcription.strip()

    def listen_and_transcribe(self) -> Optional[str]:
        """
        Listen for user speech and transcribe it
        
        Returns:
            Transcribed text or None if no speech was detected
        """
        audio_data, voice_detected = self.record_audio()
        
        if not voice_detected:
            print("No speech detected.")
            return None
        
        audio_file = self.save_audio_to_temp_file(audio_data)
        transcription = self.transcribe(audio_file)
        
        return transcription

def transcribe_speech() -> Optional[str]:
    """
    Function to listen to the user and return transcription when they stop talking
    
    Returns:
        Transcribed text or None if no speech was detected
    """
    listener = VoiceListener(model_size="base")
    return listener.listen_and_transcribe()

if __name__ == "__main__":
    print("Say something...")
    text = transcribe_speech()
    if text:
        print(f"You said: {text}")
    else:
        print("No speech detected")