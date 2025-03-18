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

def cut_audio_segment(input_filepath: str, length_seconds: float, output_filepath: str) -> None:
    """
    Cut an audio file to a specified length and export it, auto-detecting formats from file extensions
    
    Args:
        input_filepath: Path to input audio file
        length_seconds: Length to cut audio to in seconds 
        output_filepath: Path to save shortened audio file
        
    Raises:
        ValueError: If input or output file extensions are not recognized audio formats
    """
    # Validate both filepaths and get their formats
    input_format = validate_audio_filepath(input_filepath)
    output_format = validate_audio_filepath(output_filepath)
    
    # Load the audio file with detected format
    audio = AudioSegment.from_file(input_filepath, format=input_format)
    
    # Cut to specified length (convert seconds to milliseconds)
    shortened_audio = audio[:int(length_seconds*1000)]
    
    # Export shortened version with detected format
    shortened_audio.export(output_filepath, format=output_format)

