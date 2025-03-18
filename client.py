from audio_helpers import validate_audio_filepath
from elevenlabs import ElevenLabs
from pydub import AudioSegment
import requests
import os


import assemblyai as aai


def save_raw_transcript(transcript: aai.Transcript, output_path: str) -> None:
    """
    Save transcript utterances to a text file with speaker labels
    
    Args:
        transcript: AssemblyAI Transcript object containing utterances
        output_path: Path to save the transcript text file
    """
    with open(output_path, 'w') as f:
        for utterance in transcript.utterances:
            # Format timestamp in MM:SS
            start_time = int(utterance.start / 1000)  # Convert ms to seconds
            minutes = start_time // 60
            seconds = start_time % 60
            timestamp = f"[{minutes:02d}:{seconds:02d}]"
            
            # Write line with timestamp, speaker label, and text
            f.write(f"{timestamp} Speaker {utterance.speaker}: {utterance.text}\n")

def clean_audio(client: ElevenLabs, input_filepath: str) -> str:
    """
    Given a filepath to an audio file, clean background noise using an ElevenLabs client
    and output a new audio file in the same folder as the given file with a _clean suffix. 
    
    Args:
        input_filepath: Path to input audio file
        
    Returns:
        str: Path to the cleaned output audio file
        
    Raises:
        ValueError: If input file extension is not a recognized audio format
    """
    # Validate input filepath and get format
    input_format = validate_audio_filepath(input_filepath)
    
    # Load the audio file with detected format
    audio = AudioSegment.from_file(input_filepath, format=input_format)
    
    # background noise cleaning using ElevenLabs client
    # Confirm cost
    print("Calculating estimated cost...")
    audio_length_ms = len(audio)
    estimated_cost = estimate_cost(audio_length_ms, "clean")
    print(f"\nEstimated length: {audio_length_ms/1000/60:.1f} minutes") 
    print(f"Estimated cost: ${estimated_cost:.2f}")
    if input("\nProceed with audio cleaning? [y/N]: ").lower() != 'y':
        raise ValueError("Audio cleaning cancelled by user")

    output_filepath = input_filepath.rsplit('.', 1)[0] + '_clean.mp3'
    
    # Split audio if longer than API limit (3500 seconds)
    MAX_LENGTH_SEC = 3500
    MAX_LENGTH_MS = MAX_LENGTH_SEC * 1000
    
    # Create list to store cleaned segments
    cleaned_segments = []
    
    try:
        if len(audio) > MAX_LENGTH_MS:
            print("Audio exceeds maximum length, splitting into segments...")
            # Split into segments
            num_segments = (len(audio) + MAX_LENGTH_MS - 1) // MAX_LENGTH_MS
            for i in range(num_segments):
                print(f"Processing segment {i+1} of {num_segments}...")
                start_ms = i * MAX_LENGTH_MS
                end_ms = min((i + 1) * MAX_LENGTH_MS, len(audio))
                segment = audio[start_ms:end_ms]
                
                # Save segment to temp file
                temp_filepath = f"{input_filepath}_temp_{i}.{input_format}"
                segment.export(temp_filepath, format="mp3")
                
                try:
                    # Process segment
                    print(f"Calling ElevenLabs API for segment {i+1}...")
                    url = "https://api.elevenlabs.io/v1/audio-isolation"
                    files = {"audio": open(temp_filepath, 'rb')}
                    headers = {"xi-api-key": client._client_wrapper._api_key}
                    response = requests.post(url, files=files, headers=headers)
                    cleaned_segments.append(response.content)
                finally:
                    # Clean up temp file
                    os.remove(temp_filepath)
                    
            # Combine all cleaned segments into one audio file
            print("Combining cleaned segments...")
            combined_audio = AudioSegment.empty()
            for segment_bytes in cleaned_segments:
                # Load each segment bytes into AudioSegment
                segment = AudioSegment.from_mp3(io.BytesIO(segment_bytes))
                combined_audio += segment
                
            # Export the combined audio to output file
            print(f"Writing output to {output_filepath}...")
            combined_audio.export(output_filepath, format="mp3")
                    
        else:
            # Process entire file if under limit
            print("Calling ElevenLabs API...")
            url = "https://api.elevenlabs.io/v1/audio-isolation"
            files = {"audio": open(input_filepath, 'rb')}
            headers = {"xi-api-key": client._client_wrapper._api_key}
            response = requests.post(url, files=files, headers=headers)
            
            print(f"Writing output to {output_filepath}...")
            with open(output_filepath, 'wb') as f:
                f.write(response.content)
                
    except Exception as e:
        # Clean up output file if it exists
        if os.path.exists(output_filepath):
            os.remove(output_filepath)
        raise e
    
    return output_filepath


def get_cloned_voice(client: ElevenLabs, voice_id: str):
    return client.voices.get(voice_id)

def estimate_cost(audio_length_ms: int, function: str) -> float:
    """
    Calculate the estimated cost for various ElevenLabs API operations.
    
    Args:
        audio_length_ms: Length of audio in milliseconds
        function: Type of operation ('clean', 'transcribe', or 'text_to_speech')
        
    Returns:
        float: Estimated cost in USD
        
    Raises:
        ValueError: If function type is not recognized
    """
    match function:
        case "clean":
            # ElevenLabs charges 1000 credits per minute of cleaning
            # estimate $5/30,000 credits
            minutes = audio_length_ms/1000/60
            return minutes * 1000 * 5 / 30000

        case "transcribe":
            # ElevenLabs charges approximately $0.40 per hour of audio.
            # https://elevenlabs.io/docs/capabilities/speech-to-text#pricing
            hours = audio_length_ms / 1000 / 60 / 60
            return hours * 0.40

        case "text_to_speech":
            # ElevenLabs charges approximately $0.05 per minute of audio.
            # https://play.ht/blog/elevenlabs-pricing/
            minutes = audio_length_ms / 1000 / 60
            return minutes * 0.05

        case _:
            raise ValueError(f"Unknown function type: {function}. " 
                           "Supported types are: 'clean', 'transcribe', 'text_to_speech'")