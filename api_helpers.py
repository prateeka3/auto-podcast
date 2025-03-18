import assemblyai as aai
from elevenlabs import ElevenLabs
import pandas as pd
import os

def init_aai_api_key():
    """Initialize AssemblyAI API key from environment variable"""
    aai.settings.api_key = os.environ.get('ASSEMBLYAI_API_KEY')
    
    if not aai.settings.api_key:
        print("Please provide an ASSEMBLYAI_API_KEY in the .envrc")



def list_transcripts():
    """List existing transcripts as a dataframe ordered by timestamp descending"""
    init_aai_api_key()
    transcriber = aai.Transcriber()
    transcripts = transcriber.list_transcripts().transcripts
    
    # Convert to dataframe with relevant fields
    df = pd.DataFrame([{
        'id': t.id,
        'status': t.status,
        'created': t.created,
        'audio_url': t.audio_url
    } for t in transcripts])
    
    if not df.empty:
        df = df.sort_values('created', ascending=False)
    
    return df

def get_transcript(transcript_id: str) -> aai.Transcript:
    """
    Get a transcript by its ID
    
    Args:
        transcript_id: The ID of the transcript to retrieve
        
    Returns:
        AssemblyAI Transcript object
    """
    init_aai_api_key()
    return aai.Transcript.get_by_id(transcript_id)

def get_cloned_voice(voice_id: str):
    client = ElevenLabs()
    return client.voices.get(voice_id)

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
