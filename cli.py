from collections import defaultdict
from datetime import datetime
import getpass
import time
from typer import Option, Typer, Argument
from elevenlabs import ElevenLabs
from client import clean_audio, clone_voice, estimate_cost, transcribe_audio, generate_script, get_available_voices
import os
import io
import re
from pydub import AudioSegment

from common import AudioAIFunction
from helpers.audio_helpers import validate_audio_filepath
from helpers.helpers import display_available_voices

os.environ["PATH"] = "/usr/local/bin:" + os.environ["PATH"]

if not os.environ.get("ANTHROPIC_API_KEY"):
    os.environ["ANTHROPIC_API_KEY"] = getpass.getpass("Enter API key for Anthropic: ")

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
    input_file: str = Argument(
        ...,  # ... means required argument
        help="Path to the input audio file to be cleaned"
    )
):
    """
    Clean background noise from an audio file.
    
    The cleaned audio file will be saved in the same directory as the input file
    with a '_clean' suffix added to the filename.
    """
    client = ElevenLabs()
    try:
        output_file = clean_audio(client, input_file)
        print(f"Successfully cleaned audio. Output saved to: {output_file}")
    except ValueError as e:
        print(f"Error: {e}")

@app.command(no_args_is_help=True,)
def transcribe(
    input_file: str = Argument(
        ...,  # ... means required argument
        help="Path to the input audio file to transcribe"
    ),
    speakers: int = Argument(
        4,  # default value
        help="Number of expected speakers in the audio"
    ),
    force: bool = Argument(
        False,  # default value
        help="Skip confirmation prompt"
    )
):
    """
    Transcribe an audio file with speaker diarization.
    
    The transcript will identify different speakers and include timestamps.
    Requires an audio file with clear speech.
    """
    client = ElevenLabs()
    try:
        transcribe_audio(client, input_file, speakers_expected=speakers, force=force)
    except ValueError as e:
        print(f"Error: {e}")

@app.command(no_args_is_help=True,)
def script(
    transcription_file: str = Argument(
        ...,  # required argument
        help="Path to the transcription file"
    ),
    length: int = Argument(
        10,  # default 10 minutes
        help="Target length of the script in minutes"
    ),
    audience: str = Argument(
        "general",  # default value
        help="Target audience (e.g., general, technical, academic)"
    ),
    type: str = Argument(
        "discussion",  # default value
        help="Type of podcast (e.g., discussion, interview, debate)"
    )
):
    """
    Generate a podcast script from a transcription file.
    
    Converts a raw transcription into a structured, concise script
    optimized for the specified length and audience.
    """
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

def write_podcast_audio(client: ElevenLabs, script_path: str, speaker_voice_ids: dict, output_path: str = f"./audio/podcast_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"):
    """
    Write the podcast audio to a file.
    """
    # Initialize audio segments list
    silence = AudioSegment.silent(duration=500)  # 0.5s silence
    audio_segments = [silence]

    # Process each line in the script
    with open(script_path, 'r') as f:
        # Count total lines for progress tracking
        all_lines = f.readlines()
        f.seek(0)  # Reset file pointer to beginning
        total_lines = len([line for line in all_lines if line.strip()])  # Count non-empty lines
        processed_lines = 0
        start_time = datetime.now()
        
        for line in f:
            # Update progress tracking
            if line.strip():  # Only count non-empty lines
                processed_lines += 1
                if processed_lines > 1:  # After we have some data to estimate
                    elapsed_time = (datetime.now() - start_time).total_seconds()
                    time_per_line = elapsed_time / processed_lines
                    remaining_lines = total_lines - processed_lines
                    estimated_time_remaining = remaining_lines * time_per_line
                    print(f"Progress: {processed_lines}/{total_lines} lines ({processed_lines/total_lines*100:.1f}%) - Est. remaining time: {estimated_time_remaining:.1f} seconds", end="\r")
            line = line.strip()
            if not line:  # Skip empty lines
                continue
            
            # Split the speaker name from the line
            match = re.match(r'^([^:]+):\s*(.*)', line)
            if not match:
                print(f"Skipping improperly formatted line: {line}")
                continue
            
            speaker, text = match.groups()
            
            # Get the voice ID for this speaker
            if speaker.lower() not in speaker_voice_ids:
                print(f"Warning: No voice ID for speaker {speaker.lower()}, skipping line")
                continue
            
            voice_id = speaker_voice_ids[speaker.lower()]
            
            # Generate audio for this line
            try:
                audio_bytes = client.text_to_speech.convert(
                    text=text,
                    voice_id=voice_id,
                    model_id="eleven_multilingual_v2",
                    output_format="mp3_44100_128",
                )
                audio_bytes = b''.join(audio_bytes) # convert from generator to bytes
                
                # Convert bytes to AudioSegment
                audio_segment = AudioSegment.from_file(io.BytesIO(audio_bytes), format="mp3")
                
                # Add silence to end
                processed_segment = audio_segment + silence
                
                # Add to our list
                audio_segments.append(processed_segment)
                
            except Exception as e:
                print(f"Error generating audio for line: {e}")
    
    # Combine all segments
    if not audio_segments:
        print("No audio segments were generated.")
        return
    
    print("\nCombining audio segments...")
    final_audio = audio_segments[0]
    for segment in audio_segments[1:]:
        final_audio += segment
    
    # Export the final audio
    final_audio.export(output_path, format="mp3")
    print(f"\nPodcast audio saved to: {output_path}")
    return output_path

def delete_generated_voices(client: ElevenLabs, speaker_voice_ids: dict):
    for voice_id in speaker_voice_ids.values():
        client.voices.delete(voice_id)

@app.command()
def list_voices():
    """
    List available voices.
    """
    client = ElevenLabs()
    voices = get_available_voices(client)

    display_available_voices(voices)

@app.command(no_args_is_help=True)
def generate_podcast_audio(
    script_file: str = Argument(
        ...,  # required argument
        help="Path to the script file to generate podcast from"
    )
):
    """
    Generate a podcast from a script file.
    
    Converts a structured script into an audio podcast using voice cloning technology.
    """
    try:
        # Initialize ElevenLabs client
        client = ElevenLabs()
        
        # Read the script file
        with open(script_file, 'r') as f:
            script_content = f.read()
        
        # Parse the script to identify speakers
        speakers = set()
        for line in script_content.split('\n'):
            if ':' in line:
                speaker = line.split(':', 1)[0].strip()
                speakers.add(speaker)
        
        print(f"Identified speakers in script: {', '.join(speakers)}")

        
        # display
        available_voices = get_available_voices(client)
        display_available_voices(available_voices)

        # Map speakers to voice IDs
        print("Match speakers to available voices:")
        speaker_voice_ids = {}
        
        for speaker in speakers:
            # Check if there's an exact match in available voices
            exact_match = None
            for voice in available_voices:
                if voice.name.lower() == speaker.lower():
                    exact_match = voice
                    break
            
            if exact_match:
                # Ask for confirmation if there's an exact match
                confirm = input(f"Found voice '{exact_match.name}' for speaker '{speaker}'. Use this voice? (y/n): ")
                if confirm.lower() in ['y', 'yes']:
                    speaker_voice_ids[speaker.lower()] = exact_match.voice_id
                    continue
            
            # If no exact match or user declined the match, ask for manual selection
            while True:
                voice_name = input(f"Please enter the name of an existing voice to use for speaker '{speaker}': ")
                selected_voice = None
                
                for voice in available_voices:
                    if voice.name.lower() == voice_name.lower():
                        selected_voice = voice
                        break
                
                if selected_voice:
                    speaker_voice_ids[speaker.lower()] = selected_voice.voice_id
                    break
                else:
                    print(f"Voice '{voice_name}' not found. Please try again.")

        
        print("\nGenerating audio for each line...")
        write_podcast_audio(client, script_file, speaker_voice_ids)
        
    except Exception as e:
        print(f"Error generating podcast: {e}")

    
@app.command(no_args_is_help=True,)
def podcast_from_conversation(
    input_file: str = Argument(
        ...,
        help="Path to the input conversation audio file"
    ),
    speakers: int = Argument(
        4,
        help="Number of expected speakers in the audio"
    ),
    length_minutes: int = Argument(
        15,
        help="Target length of the podcast in minutes"
    ),
    audience: str = Argument(
        "general",
        help="Target audience for the podcast"
    ),
    podcast_type: str = Argument(
        "informative",
        help="Type of podcast to generate"
    ),
    clean_audio: bool = Option(
        False,
        "--clean-audio",
        help="Whether to clean the audio before processing"
    )
):
    """
    Generate a podcast from a conversation audio file.
    
    This command combines all steps:
    1. Transcribe the audio with speaker diarization
    2. Optionally clean the audio
    3. Generate a podcast script
    4. Clone voices for each speaker
    5. Generate the final podcast audio
    """
    client = ElevenLabs()
    
    try:
        # Validate that the input file is an audio file
        validate_audio_filepath(input_file)
        
        # Load the audio file to get its length for cost estimation
        audio = AudioSegment.from_file(input_file)
        audio_length_ms = len(audio)
        
        # Calculate estimated costs for each step
        clean_cost = estimate_cost(audio_length_ms, AudioAIFunction.CLEAN) if clean_audio else 0
        transcribe_cost = estimate_cost(audio_length_ms, AudioAIFunction.SPEECH_TO_TEXT)
        clone_sample_length_ms = min(10*60*1000, audio_length_ms/speakers)
        voice_cloning_cost = speakers * estimate_cost(clone_sample_length_ms, AudioAIFunction.CLONE_VOICE)
        length_minutes = min(length_minutes, audio_length_ms/1000/60)
        tts_cost = estimate_cost(length_minutes * 60 * 1000, AudioAIFunction.TEXT_TO_SPEECH)
        
        total_cost = transcribe_cost + clean_cost + voice_cloning_cost + tts_cost
        
        # Display cost estimate and ask for confirmation
        print("\n=== Cost Estimate ===")
        print(f"Input audio length: {audio_length_ms/1000/60:.1f} minutes")
        print(f"Target podcast length: {length_minutes:.1f} minutes\n")
        print(f"Transcription: ${transcribe_cost:.2f}")
        if clean_audio:
            print(f"Audio cleaning: ${clean_cost:.2f}")
        print(f"Voice cloning ({speakers} speakers): ${voice_cloning_cost:.2f}")
        print(f"Text-to-speech: ${tts_cost:.2f}")
        print(f"Total estimated cost: ${total_cost:.2f}")
        
        if input("\nProceed with podcast generation? [y/N]: ").lower() != 'y':
            print("Podcast generation cancelled by user.")
            return
        
        # Step 1: Clean audio if requested
        processed_audio = input_file
        if clean_audio:
            print("\n=== Cleaning Audio ===")
            processed_audio = clean_audio(client, input_file)
            print(f"Audio cleaned and saved to: {processed_audio}")
        
        # Step 2: Transcribe audio with diarization
        print("\n=== Transcribing Audio ===")
        transcription_path, raw_transcription = transcribe_audio(client, processed_audio, speakers, force=True, return_raw_transcription=True)
        print(f"Transcription saved to: {transcription_path}")

        # Step 2.5: Wait for Anthropic rate limit to reset
        time.sleep(60)
        
        # Step 3: Generate podcast script
        print("\n=== Generating Podcast Script ===")
        script_path = generate_script(
            transcription_path, 
            length_minutes=length_minutes,
            audience=audience,
            type=podcast_type
        )
        print(f"Script generated and saved to: {script_path}")
        
        # Step 4: Extract speaker samples and clone voices
        print("\n=== Cloning Voices ===")
        # Extract audio samples for each speaker (max clone_sample_length_ms per speaker)
        samples = defaultdict(list)
        samples_length = defaultdict(int) # in milliseconds
        current_speaker = None
        current_segment = []
        for word in raw_transcription:
            if word.speaker_id != current_speaker:
                if current_speaker and current_segment:
                    samples[current_speaker].append((current_segment[0].start*1000, current_segment[-1].end*1000))
                    samples_length[current_speaker] += current_segment[-1].end*1000 - current_segment[0].start*1000
                current_speaker = word.speaker_id
                current_segment = [word]
            elif samples_length[current_speaker] < clone_sample_length_ms:
                current_segment.append(word)
        
        speaker_voice_ids = {}
        for speaker in samples.keys():
            # combine all samples into a single audio file per speaker under audio/voices/
            samples_audio = AudioSegment.empty()
            for start, end in samples[speaker]:
                fmt = validate_audio_filepath(input_file)
                samples_audio += AudioSegment.from_file(input_file, format=fmt)[start:end]
            voice_sample_file = f"audio/voices/{speaker}.mp3"
            samples_audio.export(voice_sample_file, format="mp3")
            
            print(f"Cloning voice for {speaker}...")
            # Clone the voice using ElevenLabs. record the voice_id
            voice_id = clone_voice(client, voice_sample_file, speaker)
            speaker_voice_ids[speaker.lower()] = voice_id
            # Delete the voice sample file after cloning
            try:
                os.remove(voice_sample_file)
                print(f"Deleted voice sample file: {voice_sample_file}")
            except Exception as e:
                print(f"Warning: Could not delete voice sample file {voice_sample_file}: {e}")
        
        # Step 5: Generate podcast audio
        print("\n=== Generating Podcast Audio ===")
        write_podcast_audio(client, script_path, speaker_voice_ids)
        print("Deleting generated voices...")
        delete_generated_voices(client, speaker_voice_ids)
    except Exception as e:
        print(f"Error generating podcast: {e}")

if __name__ == "__main__":
    app()

