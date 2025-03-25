import os
from pydub import AudioSegment

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

def cut_audio_segment(input_filepath: str, length_seconds: float, output_suffix: str = "_shortened") -> str:
    """
    Cut an audio file to a specified length and export it, auto-detecting formats from file extensions
    
    Args:
        input_filepath: Path to input audio file
        length_seconds: Length to cut audio to in seconds 

    Returns:
        str: Path to the shortened output audio file
        
    Raises:
        ValueError: If input or output file extensions are not recognized audio formats
    """
    # Validate input filepath and get format
    file_format = validate_audio_filepath(input_filepath)
    
    # Generate output filepath with suffix
    output_filepath = input_filepath.rsplit('.', 1)[0] + output_suffix + '.' + file_format
    
    # Load the audio file with detected format
    audio = AudioSegment.from_file(input_filepath, format=file_format)
    
    # Cut to specified length (convert seconds to milliseconds)
    shortened_audio = audio[:int(length_seconds*1000)]
    
    # Export shortened version with detected format
    shortened_audio.export(output_filepath, format=file_format)

    return output_filepath

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
                
                # Save segment to temp file if needed
                temp_filepath = None
                if input_filepath:
                    temp_filepath = f"{input_filepath}_temp_{i}.mp3"
                    segment.export(temp_filepath, format="mp3")
                
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
            result = process_chunk_fn(audio, input_filepath)
            results.append(result)
            
    except Exception as e:
        raise e
    
    return results