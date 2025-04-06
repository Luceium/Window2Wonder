import os
import time
import numpy as np
import pyaudio
import openwakeword
from typing import Callable, Dict, List

class WakeWordListener:
    def __init__(
        self, 
        models_path: str = "./models",
        callback: Callable[[str], None] = None,
        sensitivity: float = 0.5
    ):
        """
        Initialize wake word listener with models from specified directory
        
        Args:
            models_path: Path to directory containing wake word models
            callback: Function to call when wake word is detected
            sensitivity: Detection sensitivity (0.0 to 1.0, higher = more sensitive)
        """
        # Set up audio parameters
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 16000
        self.CHUNK = 1280  # 80ms chunks (recommended for openwakeword)
        
        # Find models in the directory
        self.models_path = models_path
        self.model_files = self._find_model_files()
        
        if not self.model_files:
            raise ValueError(f"No model files found in {models_path}")
            
        print(f"Loading {len(self.model_files)} wake word models...")
        
        # Initialize the detector with the models
        self.detector = openwakeword.Model(
            wakeword_models=self.model_files,
            inference_framework="onnx",
            sensitivity=sensitivity
        )
        
        # Store callback function
        self.callback = callback if callback else self._default_callback
        
        # Create cooldown tracking to prevent repeated triggers
        self.last_detection_time = {}
        self.cooldown_time = 2.0  # seconds between detections for the same wake word
        
        print(f"Wake word listener initialized with models: {[os.path.basename(m) for m in self.model_files]}")

    def _find_model_files(self) -> List[str]:
        """Find all .onnx model files in the models directory"""
        model_files = []
        if os.path.exists(self.models_path):
            for file in os.listdir(self.models_path):
                if file.endswith(".onnx"):
                    model_files.append(os.path.join(self.models_path, file))
        return model_files
    
    def _default_callback(self, wake_word: str) -> None:
        """Default callback that simply prints the detected wake word"""
        print(f"Wake word detected: {wake_word}")
    
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
                
                # Check for detections
                current_time = time.time()
                for model_name, prediction in predictions.items():
                    # Get the base name of the model without path and extension
                    base_model_name = os.path.basename(model_name).replace(".onnx", "")
                    
                    # Check if prediction exceeds threshold
                    if prediction > 0.5:  # Default threshold for positive detection
                        # Check if we're in cooldown period for this model
                        if (base_model_name not in self.last_detection_time or 
                            current_time - self.last_detection_time[base_model_name] > self.cooldown_time):
                            
                            # Update last detection time
                            self.last_detection_time[base_model_name] = current_time
                            
                            # Call the callback function
                            self.callback(base_model_name)
                
                # Small sleep to reduce CPU usage
                time.sleep(0.01)
                
        except KeyboardInterrupt:
            print("\nStopping wake word listener...")
        finally:
            # Clean up
            stream.stop_stream()
            stream.close()
            p.terminate()
            print("Wake word listener stopped")
    
def example_callback(wake_word: str) -> None:
    """Example callback function that handles detected wake words"""
    print(f"Detected wake word: {wake_word}!")
    # You can add your own logic here, like activating voice assistants, etc.
    
if __name__ == "__main__":
    # Example usage
    listener = WakeWordListener(
        models_path="./models",
        callback=example_callback
    )
    listener.start_listening()