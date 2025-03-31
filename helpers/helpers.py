from datetime import datetime
from typing import List, TypedDict
from elevenlabs import SpeechToTextWordResponseModel
from langchain.chat_models import init_chat_model

class SpeakerMapping(TypedDict):
    chunk_number: int
    original_id: str
    global_name: str

class ReconciliationResult(TypedDict):
    speaker_mapping: List[SpeakerMapping]

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
    """
    Reconcile speaker identities across multiple transcript chunks using LLM.
    
    Args:
        chunks: List of transcript chunks, where each chunk contains word objects
        
    Returns:
        List: one combined transcription with global speaker names
    """
    # Format all chunks for LLM
    all_chunk_texts = []
    for i, chunk in enumerate(chunks):
        chunk_text = format_chunk_for_llm(chunk, i+1)
        all_chunk_texts.append(chunk_text)
    
    # Read prompt template
    with open('prompts/speaker_reconciliation.md', 'r') as f:
        prompt_template = f.read()
    
    # Combine all chunks into single input
    chunks_text = "\n\n".join(all_chunk_texts)
    
    # Format prompt with all chunks
    prompt = prompt_template.format(chunks=chunks_text)
    
    # Single LLM call for speaker reconciliation across all chunks
    model = init_chat_model("claude-3-5-sonnet-latest", model_provider="anthropic")
    response = model.with_structured_output(ReconciliationResult).invoke(prompt)
    
    # Convert to global mapping dictionary
    global_mapping = [{} for _ in range(len(chunks))]
    for entry in response['speaker_mapping']:
        global_mapping[entry['chunk_number']-1][entry['original_id']] = entry['global_name']

    # Combine all chunks into one transcription
    reconciled_words = []
    for chunk_num, chunk in enumerate(chunks):
        for word in chunk:
            # Convert original speaker_id to global name using mapping
            global_speaker = global_mapping[chunk_num].get(word.speaker_id)
            reconciled_word = SpeechToTextWordResponseModel(
                text=word.text,
                start=word.start,
                end=word.end,
                speaker_id=global_speaker,
                type=word.type
            )
            reconciled_words.append(reconciled_word)
    return reconciled_words

def write_transcription(all_words: list, output_path: str):
    """Write transcription words to file with proper formatting"""
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

def display_available_voices(voices: list):
    """Display available voices in a formatted table"""
    # Create a formatted table
    table = "Available Voices:\n"
    table += "-" * 50 + "\n"
    table += f"{'Name':<30} {'Created At':<20}\n"
    table += "-" * 50 + "\n"
    
    for voice in voices:
        # Convert unix timestamp to readable datetime
        created_at = datetime.fromtimestamp(voice.created_at_unix).strftime('%Y-%m-%d %H:%M:%S')
        table += f"{voice.name:<30} {created_at:<20}\n"
    print(table)
