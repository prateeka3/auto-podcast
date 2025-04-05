
from elevenlabs import SpeechToTextWordResponseModel
from src.audio_processing import process_large_audio, validate_audio_filepath
from pydub import AudioSegment
import requests
import io

from src.config import AudioAIFunction, get_elevenlabs_client
from src.transcription_processing import reconcile_speakers, write_transcription
from src.utils import estimate_cost

def clean_audio(input_filepath: str) -> str:
    """Clean background noise using the singleton ElevenLabs client."""
    client = get_elevenlabs_client()
    input_format = validate_audio_filepath(input_filepath)
    audio = AudioSegment.from_file(input_filepath, format=input_format)
    
    print("Calculating estimated cost...")
    audio_length_ms = len(audio)
    estimated_cost = estimate_cost(audio_length_ms, AudioAIFunction.CLEAN)
    print(f"\nEstimated length: {audio_length_ms/1000/60:.1f} minutes") 
    print(f"Estimated cost: ${estimated_cost:.2f}")
    if input("\nProceed with audio cleaning? [y/N]: ").lower() != 'y':
        raise ValueError("Audio cleaning cancelled by user.")

    def process_chunk(chunk: AudioSegment, temp_path: str) -> bytes:
        """Process a single chunk for audio cleaning"""
        url = "https://api.elevenlabs.io/v1/audio-isolation"
        files = {"audio": open(temp_path, 'rb')}
        headers = {"xi-api-key": client._client_wrapper._api_key}
        response = requests.post(url, files=files, headers=headers)
        return response.content

    cleaned_segments = process_large_audio(
        audio=audio,
        process_chunk_fn=process_chunk,
        input_filepath=input_filepath,
        progress_prefix="Cleaning"
    )
    
    output_filepath = input_filepath.rsplit('.', 1)[0] + '_clean.mp3'
    if len(cleaned_segments) > 1:
        print("Combining cleaned segments...")
        combined_audio = AudioSegment.empty()
        for segment_bytes in cleaned_segments:
            segment = AudioSegment.from_mp3(io.BytesIO(segment_bytes))
            combined_audio += segment
        combined_audio.export(output_filepath, format="mp3")
    else:
        with open(output_filepath, 'wb') as f:
            f.write(cleaned_segments[0])
    
    return output_filepath

def transcribe_audio(
    audio_path: str,
    speakers_expected: int,
    transcription_path: str = './transcription/raw_transcript.txt',
    force: bool = False,
    return_raw_transcription: bool = False
) -> tuple[str, list[SpeechToTextWordResponseModel]] | str:
    """
    Transcribe audio with speaker diarization.
    """
    audio = AudioSegment.from_file(audio_path)
    client = get_elevenlabs_client()
    
    if not force:
        audio_length_ms = len(audio)
        estimated_cost = estimate_cost(audio_length_ms, AudioAIFunction.SPEECH_TO_TEXT)
        print(f"\nEstimated length: {audio_length_ms / 1000 / 60:.1f} minutes")
        print(f"Estimated cost: ${estimated_cost:.2f}")
        confirm = input("\nProceed with transcription? [y/N]: ")
        
        if confirm.lower() != 'y':
            print("Transcription cancelled by user")
            return None, None if return_raw_transcription else None
            
    def process_chunk(chunk: AudioSegment, temp_path: str) -> list:
        """Process a single chunk for transcription"""
        transcription = client.speech_to_text.convert(
            model_id="scribe_v1",
            file=open(temp_path, "rb"),
            num_speakers=speakers_expected,
            diarize=True,
            tag_audio_events=False
        )
        return transcription.words

    all_chunks = []
    for chunk in process_large_audio(
        audio=audio,
        process_chunk_fn=process_chunk,
        input_filepath=audio_path,
        progress_prefix="Transcribing"
    ):
        all_chunks.append(chunk)

    full_raw_transcription = reconcile_speakers(all_chunks)
    write_transcription(full_raw_transcription, transcription_path)
    
    if return_raw_transcription:
        return transcription_path, full_raw_transcription
    return transcription_path