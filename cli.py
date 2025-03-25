from datetime import datetime
import getpass
from typer import Typer, Argument
from elevenlabs import ElevenLabs
from client import clean_audio, transcribe_audio, generate_script, get_available_voices
import os
import io
import re
from pydub import AudioSegment

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
                    speaker_voice_ids[speaker] = exact_match.voice_id
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
                    speaker_voice_ids[speaker] = selected_voice.voice_id
                    break
                else:
                    print(f"Voice '{voice_name}' not found. Please try again.")

        # Initialize audio segments list
        silence = AudioSegment.silent(duration=500)  # 0.5s silence
        audio_segments = [silence]
        
        # Generate output path
        output_path = './audio/podcast.mp3'
        
        print("\nGenerating audio for each line...")
        # Process each line in the script
        with open(script_file, 'r') as f:
            # Count total lines for progress tracking
            all_lines = f.readlines()
            f.seek(0)  # Reset file pointer to beginning
            total_lines = len([l for l in all_lines if l.strip()])  # Count non-empty lines
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
                if speaker not in speaker_voice_ids:
                    print(f"Warning: No voice ID for speaker {speaker}, skipping line")
                    continue
                
                voice_id = speaker_voice_ids[speaker]
                
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
        
    except Exception as e:
        print(f"Error generating podcast: {e}")

    

if __name__ == "__main__":
    app()

