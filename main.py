from vectorSearch import search
from voice2text import transcribe_speech
from wakeWord import WakeWordListener
from display import display_results

def change_stream():
    # Get transcript of request with faster whisper
    text = transcribe_speech()
    if text:
        print(f"Transcription: {text}")
        res = search(text)
        display_results(res)
    else:
        print("No transcription available.")

# Create and start the listener
listener = WakeWordListener(
    models_path="./models",
    callback=change_stream,
    sensitivity=0.6  # Adjust sensitivity as needed
)

# Start listening - this will run indefinitely until interrupted
listener.start_listening()