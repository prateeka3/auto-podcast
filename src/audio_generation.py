from typing import Dict
from datetime import datetime
import io
import re
import os
from pydub import AudioSegment

# Import the singleton client getter
from .config import get_elevenlabs_client


def write_podcast_audio(script_path: str, speaker_voice_ids: Dict[str, str], output_path: str | None = None):
    """
    Write the podcast audio to a file using the singleton client.
    Generates an output path if none is provided.
    """
    if output_path is None:
        output_dir = os.path.dirname(script_path)
        base_name = os.path.basename(script_path).rsplit('.', 1)[0]
        output_path = os.path.join(output_dir, f"{base_name}_podcast_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
    client = get_elevenlabs_client()
    silence = AudioSegment.silent(duration=500)
    audio_segments = [silence]

    with open(script_path, 'r') as f:
        # Count total lines for progress tracking
        all_lines = f.readlines()
        f.seek(0)
        total_lines = len([line for line in all_lines if line.strip()])
        processed_lines = 0
        start_time = datetime.now()
        
        for line in f:
            if line.strip():
                processed_lines += 1
                if processed_lines > 1:
                    elapsed_time = (datetime.now() - start_time).total_seconds()
                    time_per_line = elapsed_time / processed_lines
                    remaining_lines = total_lines - processed_lines
                    estimated_time_remaining = remaining_lines * time_per_line
                    print(f"Progress: {processed_lines}/{total_lines} lines ({processed_lines/total_lines*100:.1f}%) - Est. remaining time: {estimated_time_remaining:.1f} seconds", end="\r")
            
            line = line.strip()
            if not line:
                continue
            
            # Split the speaker name from the line
            match = re.match(r'^([^:]+):\s*(.*)', line)
            if not match:
                print(f"\nSkipping improperly formatted line: {line}")
                continue
            
            speaker, text = match.groups()
            speaker_key = speaker.lower()
            if speaker_key not in speaker_voice_ids:
                print(f"\nWarning: No voice ID for speaker {speaker} (key: {speaker_key}), skipping line")
                continue
            
            voice_id = speaker_voice_ids[speaker_key]
            
            # Generate audio for this line
            try:
                audio_bytes = client.text_to_speech.convert(
                    text=text,
                    voice_id=voice_id,
                    model_id="eleven_multilingual_v2",
                    output_format="mp3_44100_128",
                )
                audio_bytes = b''.join(audio_bytes)
                
                if not audio_bytes:
                    print(f"\nWarning: Empty audio generated for line: {line}")
                    continue
                    
                audio_segment = AudioSegment.from_file(io.BytesIO(audio_bytes), format="mp3")
                processed_segment = audio_segment + silence
                audio_segments.append(processed_segment)
                
            except Exception as e:
                print(f"\nError generating audio for line: {line} - {e}")
    
    if len(audio_segments) <= 1:
        print("\nNo audio segments were generated.")
        return None
    
    print("\nCombining audio segments...")
    final_audio = AudioSegment.empty()
    for segment in audio_segments:
        final_audio += segment
    
    # Export the final audio
    try:
        final_audio.export(output_path, format="mp3")
        print(f"\nPodcast audio saved to: {output_path}")
        return output_path
    except Exception as e:
        print(f"\nError exporting final audio: {e}")
        return None
