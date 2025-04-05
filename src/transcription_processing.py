from typing import List, TypedDict, cast, Type
from elevenlabs import SpeechToTextWordResponseModel
import os # Added for file path handling
from pydantic import BaseModel # Import BaseModel

# Import the LLM service
from .llm_service import LLMService 

# Define SpeakerMapping first, inheriting from BaseModel
class SpeakerMapping(BaseModel):
    chunk_number: int
    original_id: str
    global_name: str

def format_chunk_for_llm(chunk_words: list, chunk_num: int) -> str:
    """
    Convert a list of word objects into a formatted chunk transcript
    """
    current_speaker = None
    current_text = []
    chunk_lines = [f"CHUNK {chunk_num}:"]
    
    for word in chunk_words:
        if word.speaker_id != current_speaker:
            if current_speaker and current_text:
                chunk_lines.append(f"{current_speaker}: {' '.join(current_text).strip()}")
            current_speaker = word.speaker_id
            current_text = [word.text.strip()]
        else:
            current_text.append(word.text.strip())
    
    if current_speaker and current_text:
        chunk_lines.append(f"{current_speaker}: {' '.join(current_text).strip()}")
    
    return "\n".join(chunk_lines)

def reconcile_speakers(chunks: list) -> list:
    """Reconcile speaker identities using LLMService."""
    # Format all chunks for LLM
    all_chunk_texts = []
    for i, chunk in enumerate(chunks):
        chunk_text = format_chunk_for_llm(chunk, i+1)
        all_chunk_texts.append(chunk_text)
    
    # Read prompt template
    prompt_path = 'prompts/speaker_reconciliation.md'
    if not os.path.exists(prompt_path):
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
    with open(prompt_path, 'r') as f:
        prompt_template = f.read()
    
    # Combine all chunks into single input
    chunks_text = "\n\n".join(all_chunk_texts)
    
    # Format prompt with all chunks
    prompt = prompt_template.format(chunks=chunks_text)
    
    # Use LLMService for structured generation
    llm = LLMService() # Initialize service
    response = llm.generate_structured(prompt=prompt, response_model=list[SpeakerMapping])
    
        
    # Convert to global mapping dictionary
    global_mapping = [{} for _ in range(len(chunks))]
    # Access Pydantic fields using dot notation (should work now)
    for entry in response:
        if entry.chunk_number > len(global_mapping):
            print(f"Warning: Chunk number {entry.chunk_number} out of bounds.")
            continue
        global_mapping[entry.chunk_number-1][entry.original_id] = entry.global_name

    # Combine all chunks into one transcription
    reconciled_words = []
    for chunk_num, chunk in enumerate(chunks):
        for word in chunk:
            # Convert original speaker_id to global name using mapping
            global_speaker = global_mapping[chunk_num].get(word.speaker_id)
            # Ensure all required fields are present
            reconciled_word = SpeechToTextWordResponseModel(
                text=word.text,
                start=getattr(word, 'start', 0.0), # Provide default if missing
                end=getattr(word, 'end', 0.0),   # Provide default if missing
                speaker_id=global_speaker,
                type=getattr(word, 'type', 'word') # Provide default if missing
            )
            reconciled_words.append(reconciled_word)
    return reconciled_words

# Moved from helpers/helpers.py
def write_transcription(all_words: list, output_path: str):
    """Write transcription words to file with proper formatting"""
    os.makedirs(os.path.dirname(output_path), exist_ok=True) # Ensure directory exists
    # Write final transcript using global mapping
    with open(output_path, 'w') as f:
        current_speaker = None
        current_text = []
        
        for word in all_words:
            if word.speaker_id != current_speaker:
                if current_speaker and current_text:
                    f.write(f"{current_speaker}: {' '.join(current_text).replace('  ', ' ')}\n")
                current_speaker = word.speaker_id
                current_text = [word.text.strip()]
            else:
                current_text.append(word.text.strip())
        
        if current_speaker and current_text:
            f.write(f"{current_speaker}: {' '.join(current_text).replace('  ', ' ')}\n")
