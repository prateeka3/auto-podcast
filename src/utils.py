from datetime import datetime

def display_available_voices(voices: list):
    """Display available voices in a formatted table"""
    # Create a formatted table
    table = "Available Voices:\n"
    table += "-" * 50 + "\n"
    table += f"{'Name':<30} {'Created At':<20}\n"
    table += "-" * 50 + "\n"
    
    for voice in voices:
        # Convert unix timestamp to readable datetime
        created_at = datetime.fromtimestamp(voice.created_at_unix).strftime('%Y-%m-%d %H:%M:%S')
        table += f"{voice.name:<30} {created_at:<20}\n"
    print(table)

# Moved estimate_cost here from client.py
# Import AudioAIFunction from config
from .config import AudioAIFunction

def estimate_cost(audio_length_ms: int, function: AudioAIFunction) -> float:
    """
    Calculate the estimated cost for various ElevenLabs API operations.
    
    Args:
        audio_length_ms: Length of audio in milliseconds
        function: Type of operation ('clean', 'transcribe', etc.)
        
    Returns:
        float: Estimated cost in USD
        
    Raises:
        ValueError: If function type is not recognized
    """
    match function:
        case AudioAIFunction.CLEAN:
            minutes = audio_length_ms/1000/60
            return minutes * 1000 * 5 / 30000
        case AudioAIFunction.SPEECH_TO_TEXT:
            hours = audio_length_ms / 1000 / 60 / 60
            return hours * 0.40
        case AudioAIFunction.TEXT_TO_SPEECH:
            minutes = audio_length_ms / 1000 / 60
            return minutes * 0.17
        case AudioAIFunction.CLONE_VOICE:
            minutes = audio_length_ms / 1000 / 60
            return minutes * 5 / 30
        case _:
            raise ValueError(f"Unknown function type: {function}.")
