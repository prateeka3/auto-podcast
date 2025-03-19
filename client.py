from audio_helpers import validate_audio_filepath
from elevenlabs import ElevenLabs
from pydub import AudioSegment
import requests
import os


from common import AudioAIFunction


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
        raise ValueError("Audio cleaning cancelled by user. Try lalal.ai for a cheaper alternative")

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


def transcribe_audio(
    client: ElevenLabs,
    audio_path: str,
    speakers_expected: int,
    transcription_path: str = './transcription/raw_transcript.txt',
    force: bool = False
):
    """
    Transcribe audio with speaker diarization and custom spellings.
    Prompts for confirmation before consuming API credits.
    
    Args:
        audio_path: Path to audio file
        speakers_expected: Number of expected speakers
        filter_profanity: Whether to filter out profanity
        force: Skip confirmation prompt if True
        
    Returns:
        filepath of transcription
    """
    # Calculate estimated cost. ElevenLabs charges ~$0.40 per hour
    # https://elevenlabs.io/docs/capabilities/speech-to-text#pricing
    audio = AudioSegment.from_file(audio_path)
    
    if not force:
        audio_length_ms = len(audio)
        estimated_cost = estimate_cost(audio_length_ms, AudioAIFunction.SPEECH_TO_TEXT)
        print(f"\nEstimated length: {1000 / 60:.1f} minutes")
        print(f"Estimated cost: ${estimated_cost:.2f}")
        confirm = input("\nProceed with transcription? [y/N]: ")
        
        if confirm.lower() != 'y':
            print("Transcription cancelled by user")
            return None
            
    # Perform transcription
    transcription = client.speech_to_text.convert(
        model_id="scribe_v1",
        file=open(audio_path, "rb"),
        num_speakers=speakers_expected,
        diarize=True,
    )

    # Process and write transcription
    current_speaker = None
    current_text = []
    
    with open(transcription_path, 'w') as f:
        for word in transcription.words:
            if word.speaker_id != current_speaker:
                # Write previous speaker's text if it exists
                if current_speaker and current_text:
                    f.write(f"{current_speaker}: {' '.join(current_text).replace('  ', ' ')}\n")
                # Start new speaker
                current_speaker = word.speaker_id
                current_text = [word.text.strip()]
            else:
                current_text.append(word.text.strip())
        
        # Write final speaker's text
        if current_speaker and current_text:
            f.write(f"{current_speaker}: {' '.join(current_text).replace('  ', ' ')}\n")
    
    print(f"Transcription saved to: {transcription_path}")
    return transcription

def get_cloned_voice(client: ElevenLabs, voice_id: str):
    return client.voices.get(voice_id)

def estimate_cost(audio_length_ms: int, function: AudioAIFunction) -> float:
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
        case AudioAIFunction.CLEAN:
            # ElevenLabs charges 1000 credits per minute of cleaning
            # estimate $5/30,000 credits
            minutes = audio_length_ms/1000/60
            return minutes * 1000 * 5 / 30000

        case AudioAIFunction.SPEECH_TO_TEXT:
            # ElevenLabs charges approximately $0.40 per hour of audio.
            # https://elevenlabs.io/docs/capabilities/speech-to-text#pricing
            hours = audio_length_ms / 1000 / 60 / 60
            return hours * 0.40

        case AudioAIFunction.TEXT_TO_SPEECH:
            # ElevenLabs charges approximately $0.17 per minute of audio.
            # https://play.ht/blog/elevenlabs-pricing/
            minutes = audio_length_ms / 1000 / 60
            raise ValueError("not sure")
            return minutes * 0.17

        case _:
            raise ValueError(f"Unknown function type: {function}. " 
                           "Supported types are: 'clean', 'transcribe', 'text_to_speech'")