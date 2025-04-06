import os
import time
import numpy as np
import pyaudio
import openwakeword
from typing import Callable, Dict, List
from openwakeword.model import Model
class WakeWordListener:
    def __init__(
        self, 
        model_path: str = "./models/win_dough_win_dough.onnx",
        callback: Callable[[str], None] = None,
        sensitivity: float = 0.5
    ):
        """
        Initialize wake word listener with models from specified directory
        
        Args:
            callback: Function to call when wake word is detected
            sensitivity: Detection sensitivity (0.0 to 1.0, higher = more sensitive)
        """
        # Set up audio parameters
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 16000
        self.CHUNK = 1280  # 80ms chunks (recommended for openwakeword)
        
        # Initialize the detector with the models
        self.detector = Model(wakeword_models=[model_path], inference_framework=model_path.split('.')[-1])
        
        # Store callback function
        self.callback = callback if callback else self._default_callback
        
        # Create cooldown tracking to prevent repeated triggers
        self.last_detection_time = {}
        self.cooldown_time = 2.0  # seconds between detections for the same wake word
    
    def start_listening(self) -> None:
        """Start continuously listening for wake words"""
        p = pyaudio.PyAudio()
        
        # Open audio stream
        stream = p.open(
            format=self.FORMAT,
            channels=self.CHANNELS,
            rate=self.RATE,
            input=True,
            frames_per_buffer=self.CHUNK
        )
        
        print("Listening for wake words... (Press Ctrl+C to stop)")
        
        try:
            while True:
                # Read audio data
                audio_data = stream.read(self.CHUNK, exception_on_overflow=False)
                audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
                
                # Process with wake word detector
                predictions = self.detector.predict(audio_array)
        
                if predictions.values()[0] > 0.5:
                    self.callback()
                
        except KeyboardInterrupt:
            print("\nStopping wake word listener...")
        finally:
            # Clean up
            stream.stop_stream()
            stream.close()
            p.terminate()
            print("Wake word listener stopped")
    
def example_callback() -> None:
    """Example callback function that handles detected wake words"""
    print(f"Detected wake word!")
    # You can add your own logic here, like activating voice assistants, etc.
    
if __name__ == "__main__":
    # Example usage
    listener = WakeWordListener(
        model_path="./models/win_dough_win_dough.tflite", # "./models/win_dough_win_dough.onnx"
        callback=example_callback
    )
    listener.start_listening()