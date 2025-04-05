from pydantic import BaseModel
import os
from typing import List

# Moved from client.py
from src.config import WORDS_PER_MINUTE # Import from config
from src.llm_service import LLMService # Import the new service


def generate_script(transcription_path: str, length_minutes: int, audience: str = "general", type: str = "discussion") -> str:
    """
    Generate a script from a transcription using LLMService.
    
    Args:
        transcription_path: Path to the transcription file
        length_minutes: Target length in minutes
        audience: Target audience for the script
        type: Type of podcast (discussion, interview, etc.)
    
    Returns:
        str: Path to the generated script file
    """
    # Read transcription
    with open(transcription_path, 'r') as f:
        transcription = f.read()

    # Read prompt template
    prompt_path = 'prompts/script_generation.md'
    if not os.path.exists(prompt_path):
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
    with open(prompt_path, 'r') as f:
        prompt_template = f.read()
    
    # Calculate word count target
    word_count = length_minutes * WORDS_PER_MINUTE
    
    # Format prompt with parameters
    prompt = prompt_template.format(
        length_minutes=length_minutes,
        audience=audience,
        type=type,
        word_count=word_count
    )
    
    # Use LLMService for generation
    llm = LLMService() # Initialize the service
    
    # Construct the full prompt for the LLM
    full_prompt = f"{prompt}\n\nTRANSCRIPT:\n{transcription}\n\nSCRIPT:"
    
    # Calculate max tokens (commented out, as it's not used)
    # max_tokens_to_generate = max(1000, int(word_count * 1.5))
    
    # Generate script text using the service (removed max_tokens)
    script_content = llm.generate_text(prompt=full_prompt)
    
    if not script_content:
         print("Warning: LLM script generation returned empty content.")
         # Decide how to handle - maybe return empty path or raise error?
         # For now, continue to write empty file

    # Generate output filename
    output_dir = os.path.dirname(transcription_path)
    base_name = os.path.basename(transcription_path).rsplit('.', 1)[0]
    script_path = os.path.join(output_dir, f"{base_name}_script.txt")
    
    # Write the script to a file
    os.makedirs(output_dir, exist_ok=True)
    with open(script_path, 'w') as f:
        f.write(script_content)
    
    print(f"Script written to {script_path}")
    return script_path
