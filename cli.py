from collections import defaultdict
from datetime import datetime
import getpass
import time
from typer import Option, Typer, Argument
import os
import re
from pydub import AudioSegment
import io

from src.config import AudioAIFunction
from src.utils import display_available_voices, estimate_cost
from src.audio_processing import validate_audio_filepath
from src.voice_management import VoiceManager
from client import clean_audio, transcribe_audio
from src.script_generation import generate_script
from src.audio_generation import write_podcast_audio

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

os.environ["PATH"] = "/usr/local/bin:" + os.environ["PATH"]

app = Typer(
    no_args_is_help=True,
    help="Audio processing toolkit",
)

@app.command(no_args_is_help=True,)
def main():
    """
    Welcome to the audio processing toolkit.
    Run with --help to see available commands.
    """

@app.command(no_args_is_help=True,)
def clean(
    input_file: str = Argument(..., help="Path to the input audio file to be cleaned")
):
    """Clean background noise from an audio file."""
    try:
        output_file = clean_audio(input_file)
        print(f"Successfully cleaned audio. Output saved to: {output_file}")
    except Exception as e:
        print(f"Error cleaning audio: {e}")

@app.command(no_args_is_help=True,)
def transcribe(
    input_file: str = Argument(..., help="Path to the input audio file to transcribe"),
    speakers: int = Argument(4, help="Number of expected speakers"),
    force: bool = Option(False, "--force", help="Skip confirmation prompt")
):
    """Transcribe an audio file with speaker diarization."""
    try:
        output_path, _ = transcribe_audio(input_file, speakers_expected=speakers, force=force, return_raw_transcription=True)
        if output_path:
            print(f"Successfully transcribed audio. Output saved to: {output_path}")
        else:
             print("Transcription failed or was cancelled.")
    except Exception as e:
        print(f"Error transcribing audio: {e}")

@app.command(no_args_is_help=True,)
def script(
    transcription_file: str = Argument(..., help="Path to the transcription file"),
    length: int = Argument(10, help="Target length of the script in minutes"),
    audience: str = Argument("general", help="Target audience"),
    type: str = Argument("discussion", help="Type of podcast")
):
    """Generate a podcast script from a transcription file."""
    try:
        script_path = generate_script(
            transcription_file,
            length_minutes=length,
            audience=audience,
            type=type
        )
        print(f"Successfully generated script. Output saved to: {script_path}")
    except Exception as e:
        print(f"Error generating script: {e}")

@app.command()
def list_voices():
    """List available voices."""
    try:
        vm = VoiceManager()
        voices = vm.get_available_voices()
        display_available_voices(voices)
    except Exception as e:
        print(f"Error listing voices: {e}")

@app.command(no_args_is_help=True)
def generate_podcast_audio(
    script_file: str = Argument(..., help="Path to the script file")
):
    """Generate a podcast from a script file using available or selected voices."""
    try:
        with open(script_file, 'r') as f:
            script_content = f.read()
        speakers = set()
        for line in script_content.split('\n'):
            if ':' in line:
                speaker = line.split(':', 1)[0].strip()
                speakers.add(speaker)
        
        if not speakers:
            print("Error: No speakers found in the script.")
            return
            
        print(f"Identified speakers in script: {list(speakers)}")

        vm = VoiceManager()
        available_voices = vm.get_available_voices()
        display_available_voices(available_voices)

        print("\nMatch speakers to available voices:")
        speaker_voice_ids = {}
        for speaker in speakers:
            speaker_lower = speaker.lower()
            exact_match = next((v for v in available_voices if v.name.lower() == speaker_lower), None)
            
            if exact_match:
                confirm = input(f"Found voice '{exact_match.name}' for speaker '{speaker}'. Use this voice? (y/n): ").lower()
                if confirm in ['y', 'yes']:
                    speaker_voice_ids[speaker_lower] = exact_match.voice_id
                    continue
            
            while True:
                voice_name = input(f"Enter existing voice name for speaker '{speaker}': ").lower()
                selected_voice = next((v for v in available_voices if v.name.lower() == voice_name), None)
                if selected_voice:
                    speaker_voice_ids[speaker_lower] = selected_voice.voice_id
                    break
                else:
                    print(f"Voice '{voice_name}' not found. Try again.")
        
        print("\nGenerating podcast audio...")
        output_path = write_podcast_audio(script_file, speaker_voice_ids)
        if output_path:
            print(f"Successfully generated podcast audio: {output_path}")
        else:
            print("Failed to generate podcast audio.")
            
    except Exception as e:
        print(f"Error generating podcast audio: {e}")

    
@app.command(no_args_is_help=True,)
def podcast_from_conversation(
    input_file: str = Argument(..., help="Path to the input conversation audio file"),
    speakers: int = Argument(4, help="Number of expected speakers"),
    length_minutes: int = Argument(15, help="Target podcast length in minutes"),
    audience: str = Argument("general", help="Target audience"),
    podcast_type: str = Argument("informative", help="Podcast type"),
    clean_audio_flag: bool = Option(False, "--clean-audio", help="Clean audio before processing")
):
    """Generate a podcast from a conversation audio file (full pipeline)."""
    validate_audio_filepath(input_file)
    audio = AudioSegment.from_file(input_file)
    audio_length_ms = len(audio)
    
    # Cost Estimation (using utils)
    target_length = min(length_minutes, audio_length_ms / 60000)
    clean_cost = estimate_cost(audio_length_ms, AudioAIFunction.CLEAN) if clean_audio_flag else 0
    transcribe_cost = estimate_cost(audio_length_ms, AudioAIFunction.SPEECH_TO_TEXT)
    clone_sample_length_ms = int(min(10 * 60 * 1000, audio_length_ms / speakers if speakers > 0 else audio_length_ms))
    voice_cloning_cost = speakers * estimate_cost(clone_sample_length_ms, AudioAIFunction.CLONE_VOICE)
    tts_cost = estimate_cost(int(target_length * 60 * 1000), AudioAIFunction.TEXT_TO_SPEECH)
    total_cost = transcribe_cost + clean_cost + voice_cloning_cost + tts_cost
    
    print("\n=== Cost Estimate ===")
    print(f"Input audio: {audio_length_ms/60000:.1f} min, Target podcast: {target_length:.1f} min")
    print(f"Transcription: ${transcribe_cost:.2f}")
    if clean_audio_flag: print(f"Audio cleaning: ${clean_cost:.2f}")
    print(f"Voice cloning ({speakers} speakers): ${voice_cloning_cost:.2f}")
    print(f"Text-to-speech: ${tts_cost:.2f}")
    print(f"Total estimated: ${total_cost:.2f}")
    
    if input("\nProceed? [y/N]: ").lower() != 'y':
        print("Cancelled.")
        return
    
    # Step 1: Clean (Optional)
    processed_audio_path = input_file
    if clean_audio_flag:
        print("\n=== Cleaning Audio ===")
        processed_audio_path = clean_audio(input_file) # Uses client function
        print(f"Cleaned audio saved to: {processed_audio_path}")
    
    # Step 2: Transcribe
    print("\n=== Transcribing Audio ===")
    transcription_path, raw_transcription = transcribe_audio(processed_audio_path, speakers, force=True, return_raw_transcription=True)
    if not transcription_path or not raw_transcription:
            raise Exception("Transcription failed.")
    print(f"Transcription saved to: {transcription_path}")

    
    # Step 3: Generate Script
    print("\n=== Generating Script ===")
    script_path = generate_script(
        transcription_path, 
        length_minutes=int(target_length), # Use calculated target length
        audience=audience,
        type=podcast_type
    )
    print(f"Script saved to: {script_path}")
    
    # Step 4: Clone Voices
    print("\n=== Cloning Voices ===")
    vm = VoiceManager()
    
    samples = vm.extract_samples_from_transcription(raw_transcription, clone_sample_length_ms)
    
    speaker_voice_ids = {}
    sample_files_to_delete = []
    for speaker_id, segments in samples.items():
        if not segments: continue
        samples_audio = AudioSegment.empty()
        try:
            fmt = validate_audio_filepath(input_file) # Validate original file
            source_audio = AudioSegment.from_file(input_file, format=fmt)
            for start, end in segments:
                samples_audio += source_audio[int(start):int(end)]
        except Exception as e:
            print(f"Warning: Error extracting samples for {speaker_id}: {e}")
            continue
                        
        voice_sample_file = os.path.join(vm.sample_dir, f"{speaker_id}.mp3")
        samples_audio.export(voice_sample_file, format="mp3", parameters=["-ac", "1"])
        sample_files_to_delete.append(voice_sample_file)
        
        print(f"Cloning voice for {speaker_id}...")
        try:
            voice_id = vm.clone_voice(voice_sample_file, f"Podcast_{speaker_id}_{datetime.now().strftime('%Y%m%d')}")
            speaker_voice_ids[speaker_id.lower()] = voice_id
        except Exception as e:
            print(f"Warning: Failed to clone voice for {speaker_id}: {e}")

    # Clean up sample files
    for f_path in sample_files_to_delete:
        try:
            os.remove(f_path)
        except OSError as e:
            print(f"Warning: Could not delete sample file {f_path}: {e}")

    if not speaker_voice_ids:
        raise Exception("Voice cloning failed for all speakers.")

    # Step 5: Generate Podcast Audio
    print("\n=== Generating Podcast Audio ===")
    output_audio_path = write_podcast_audio(script_path, speaker_voice_ids)
    
    # Step 6: Clean up generated voices
    vm.delete_generated_voices(speaker_voice_ids)

    if output_audio_path:
        print(f"\nPodcast successfully generated: {output_audio_path}")
    else:
        print("\nPodcast generation finished, but final audio export failed.")

if __name__ == "__main__":
    app()

