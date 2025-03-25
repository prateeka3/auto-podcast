from typing import List
from pydantic import BaseModel
from helpers.audio_helpers import process_large_audio, validate_audio_filepath
from elevenlabs import ElevenLabs
from pydub import AudioSegment
import requests
import io
from langchain.chat_models import init_chat_model


from common import AudioAIFunction
from helpers.helpers import write_transcription

class SpeakerLine(BaseModel):
    speaker: str
    text: str

class SpeakerLines(BaseModel):
    content: List[SpeakerLine]


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

    def process_chunk(chunk: AudioSegment, temp_path: str) -> bytes:
        """Process a single chunk for audio cleaning"""
        url = "https://api.elevenlabs.io/v1/audio-isolation"
        files = {"audio": open(temp_path, 'rb')}
        headers = {"xi-api-key": client._client_wrapper._api_key}
        response = requests.post(url, files=files, headers=headers)
        return response.content

    # Process the audio in chunks
    cleaned_segments = process_large_audio(
        audio=audio,
        process_chunk_fn=process_chunk,
        input_filepath=input_filepath,
        progress_prefix="Cleaning"
    )
    
    # Combine results
    output_filepath = input_filepath.rsplit('.', 1)[0] + '_clean.mp3'
    if len(cleaned_segments) > 1:
        print("Combining cleaned segments...")
        combined_audio = AudioSegment.empty()
        for segment_bytes in cleaned_segments:
            segment = AudioSegment.from_mp3(io.BytesIO(segment_bytes))
            combined_audio += segment
        combined_audio.export(output_filepath, format="mp3")
    else:
        # Single segment, just write it directly
        with open(output_filepath, 'wb') as f:
            f.write(cleaned_segments[0])
    
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
        print(f"\nEstimated length: {audio_length_ms / 1000 / 60:.1f} minutes")
        print(f"Estimated cost: ${estimated_cost:.2f}")
        confirm = input("\nProceed with transcription? [y/N]: ")
        
        if confirm.lower() != 'y':
            print("Transcription cancelled by user")
            return None
            
    def process_chunk(chunk: AudioSegment, temp_path: str) -> list:
        """Process a single chunk for transcription"""
        transcription = client.speech_to_text.convert(
            model_id="scribe_v1",
            file=open(temp_path, "rb"),
            num_speakers=speakers_expected,
            diarize=True,
        )
        return transcription.words

    # Process the audio in chunks
    all_chunks = []
    for chunk in process_large_audio(
        audio=audio,
        process_chunk_fn=process_chunk,
        input_filepath=audio_path,
        progress_prefix="Transcribing"
    ):
        all_chunks.append(chunk)

    # Write combined transcription
    write_transcription(all_chunks, transcription_path)
    return transcription_path


def generate_script(transcription_path: str, length_minutes: int, audience: str = "general", type: str = "discussion"):
    """
    Generate a script from a transcription.
    
    Args:
        transcription_path: Path to the transcription file
        length_minutes: Target length in minutes
        audience: Target audience for the script
        type: Type of podcast (discussion, interview, etc.)
    
    Returns:
        str: Generated script
    """
    # Read transcription
    with open(transcription_path, 'r') as f:
        transcription = f.read()

    # Read prompt template
    with open('prompts/script_generation.md', 'r') as f:
        prompt_template = f.read()
    
    # Format prompt with parameters
    prompt = prompt_template.format(
        length_minutes=length_minutes,
        audience=audience,
        type=type,
        word_count=length_minutes * 150
    )
    
    # Initialize chat model
    model = init_chat_model("claude-3-5-sonnet-latest", model_provider="anthropic")
    
    # Generate script with structured output
    response = model.with_structured_output(SpeakerLines).invoke(
        prompt + f"\n\nTRANSCRIPT:\n{transcription}"
    )
    
    # Generate output filename based on input
    script_path = 'transcription/podcast_script.txt'
    
    # Write the generated script to a file
    with open(script_path, 'w') as f:
        for line in response.content:
            f.write(f"{line.speaker}: {line.text}\n")
    
    print(f"Script written to {script_path}")
    return script_path


def get_available_voices(client: ElevenLabs):
    """
    Get available voices from ElevenLabs.
    
    Returns:
        list: List of available voices
    """
    
    all_voices = client.voices.get_all().voices
    non_premade_voices = list(filter(lambda v: v.category != "premade", all_voices))
    return non_premade_voices

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