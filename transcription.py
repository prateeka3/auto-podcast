from pydub import AudioSegment
import pandas as pd
import os
from elevenlabs.client import ElevenLabs
import re

def extract_longest_speaker_segments(transcript: aai.Transcript, audio_filepath: str, save_speaker_audios: bool = False) -> pd.DataFrame:
    """
    Extract and save the longest continuous segment for each speaker from a transcript.
    
    Args:
        transcript: Transcript object containing utterances with speaker, start and end times
        audio_filepath: Path to the audio file to extract segments from
        save_audio: Whether to save audio segments to disk (default: False)
        
    Returns:
        pd.DataFrame: DataFrame containing the longest segments per speaker
    """
    # Convert transcript to dataframe
    rows = []
    for utterance in transcript.utterances:
        rows.append({"start": utterance.start, 
                    "end": utterance.end, 
                    "speaker": utterance.speaker})
    df = pd.DataFrame(rows)
    
    # Find longest segment per speaker
    df['length'] = df.end - df.start
    longest_per_speaker = df.groupby('speaker')['length'].idxmax()
    longest_segments = df.loc[longest_per_speaker]
    
    # Optionally extract and save audio segments
    if save_speaker_audios:
        audio = AudioSegment.from_file(audio_filepath)
        for _, row in longest_segments.iterrows():
            speaker_audio = audio[row['start']:row['end']]
            os.makedirs('./audio/voices', exist_ok=True)
            speaker_audio.export(f"./audio/voices/speaker_{row['speaker']}.mp3", format="mp3")
    
    return longest_segments

def script_to_audio(script_file_path: str, output_file_path: str):
    """
    for each line in the script:
    - split the initial "NAME:" off from the rest of the text
    - generate the audio for the line using the voice id from the name
    - add 0.5s of whitespace on either end
    - add the audio to a list
    finally, concat all audio in the list together and print it
    """
    client = ElevenLabs()

    # List to store audio segments
    audio_segments = []

    silence = AudioSegment.silent(duration=500)
    
    # Read the script file
    with open(script_file_path, 'r') as file:
        counter = 0
        for line in file:
            counter+=1
            if counter == 10:
                break
            line = line.strip()
            if not line:  # Skip empty lines
                continue
            
            # Split the speaker name from the line
            match = re.match(r'^([A-Z]+):\s*(.*)', line)
            if not match:
                print(f"Skipping improperly formatted line: {line}")
                continue
            
            speaker_name, text = match.groups()
            
            # Get the voice ID for this speaker
            if speaker_name not in SPEAKER_NAME_TO_VOICE_ID:
                print(f"Warning: No voice ID for speaker {speaker_name}, skipping line")
                continue
            
            voice_id = SPEAKER_NAME_TO_VOICE_ID[speaker_name]
            
            # Generate audio for this line
            print(f"Generating audio for {speaker_name}: {text}")
            try:
                audio_bytes = client.text_to_speech.convert(
                    text=text,
                    voice_id=voice_id,
                    model_id="eleven_multilingual_v2",
                    output_format="mp3_44100_128",
                    voice_settings=VoiceSettings(
                        stability=0.6,
                        similarity_boost=0.3,
                        style=0.4,
                    ),
                )

                # Handle the case where audio_bytes is a generator
                if hasattr(audio_bytes, '__iter__') and not isinstance(audio_bytes, bytes):
                    # Collect all chunks into a single bytes object
                    all_bytes = b''
                    for chunk in audio_bytes:
                        all_bytes += chunk
                    audio_bytes = all_bytes
                
                # Convert bytes to AudioSegment
                audio_segment = AudioSegment.from_file(io.BytesIO(audio_bytes), format="mp3")
                
                # Add silence to beginning and end
                processed_segment = silence + audio_segment + silence
                
                # Add to our list
                audio_segments.append(processed_segment)
                
            except Exception as e:
                print(f"Error generating audio for line: {e}")
    
    # Concatenate all audio segments
    if not audio_segments:
        print("No audio segments were generated.")
        return
    
    final_audio = audio_segments[0]
    for segment in audio_segments[1:]:
        final_audio += segment
    
    # Export the final audio
    final_audio.export(output_file_path, format="mp3")
    print(f"Audio saved to {output_file_path}")


def clone_voice(clone_name: str, sample_paths: list[str], description: str = None):
    """
    Clone a voice using ElevenLabs API from audio samples.
    Estimates cost and prompts for confirmation before proceeding.
    
    Args:
        clone_name: Name for the cloned voice
        sample_paths: List of paths to audio sample files
        description: Optional description of the voice
        
    Returns:
        Voice ID of the cloned voice
    """
    client = ElevenLabs()
    
    # Calculate total size of samples
    total_mb = sum(os.path.getsize(path) / (1024 * 1024) for path in sample_paths)
    estimated_credits = total_mb * 0.2  # ElevenLabs charges ~$0.20 per MB
    
    print(f"\nTotal sample size: {total_mb:.1f} MB")
    print(f"Estimated credit cost: ${estimated_credits:.2f}")
    confirm = input("\nProceed with voice cloning? [y/N]: ")
    
    if confirm.lower() != 'y':
        print("Voice cloning cancelled")
        return None
        
    # Clone the voice
    voice = client.clone(
        name=clone_name,
        files=sample_paths,
        description=description
    )
    
    # Print clone info
    print("\nVoice clone created successfully!")
    print(f"Name: {voice.name}")
    print(f"Voice ID: {voice.voice_id}")
    print(f"Created: {voice.created_at}")
    print(f"Dashboard URL: https://elevenlabs.io/voice-lab/voice/{voice.voice_id}")