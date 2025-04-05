import os
from pydub import AudioSegment

# Moved from helpers/audio_helpers.py
def validate_audio_filepath(filepath: str) -> str:
    """
    Validate if a filepath has a supported audio format extension
    
    Args:
        filepath: Full path to audio file to validate
        
    Returns:
        str: The detected audio format
        
    Raises:
        ValueError: If file extension is not a recognized audio format
    """
    supported_formats = {'mp3', 'wav', 'ogg', 'm4a', 'mp4', 'wma', 'aac', 'flac'}
    
    try:
        file_format = filepath.split('.')[-1].lower()
    except IndexError:
        raise ValueError(f"Invalid filepath: {filepath}. No file extension found.")
        
    if file_format not in supported_formats:
        raise ValueError(f"File '{filepath}' has unsupported format '.{file_format}'. "
                        f"Supported formats are: {', '.join(supported_formats)}")
                        
    return file_format

# Moved from helpers/audio_helpers.py
def process_large_audio(
    audio: AudioSegment,
    process_chunk_fn: callable,
    max_length_sec: int = 3500,
    input_filepath: str = None,
    progress_prefix: str = "Processing"
) -> list:
    """
    Split large audio files into chunks, process each chunk, and return list of results.
    
    Args:
        audio: AudioSegment to process
        process_chunk_fn: Function that takes (chunk: AudioSegment, temp_path: str) and returns result
        max_length_sec: Maximum length in seconds for each chunk
        input_filepath: Used to generate temporary filenames
        progress_prefix: Prefix for progress messages
        
    Returns:
        list: List of results from processing each chunk
    """
    max_length_ms = max_length_sec * 1000
    results = []
    
    try:
        if len(audio) > max_length_ms:
            print(f"{progress_prefix} exceeds maximum length, splitting into segments...")
            # Split into segments
            num_segments = (len(audio) + max_length_ms - 1) // max_length_ms
            for i in range(num_segments):
                print(f"{progress_prefix} segment {i+1} of {num_segments}...")
                start_ms = i * max_length_ms
                end_ms = min((i + 1) * max_length_ms, len(audio))
                segment = audio[start_ms:end_ms]
                
                temp_filepath = None
                if input_filepath:
                    base, ext = os.path.splitext(input_filepath)
                    temp_filepath = f"{base}_temp_{i}{ext}" # Use original extension
                    segment.export(temp_filepath, format=ext.lstrip('.'))
                
                try:
                    # Process segment
                    result = process_chunk_fn(segment, temp_filepath)
                    results.append(result)
                finally:
                    # Clean up temp file
                    if temp_filepath and os.path.exists(temp_filepath):
                        os.remove(temp_filepath)
        else:
            # Process entire file if under limit
            print(f"{progress_prefix} entire file...")
            result = process_chunk_fn(audio, input_filepath)
            results.append(result)
            
    except Exception as e:
        if temp_filepath and os.path.exists(temp_filepath):
             os.remove(temp_filepath)
        raise e
    
    return results
