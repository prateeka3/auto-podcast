import getpass
from typer import Typer, Argument
from elevenlabs import ElevenLabs
from client import clean_audio, transcribe_audio
import os

os.environ["PATH"] = "/usr/local/bin:" + os.environ["PATH"]

if not os.environ.get("ANTHROPIC_API_KEY"):
    os.environ["ANTHROPIC_API_KEY"] = getpass.getpass("Enter API key for Anthropic: ")

app = Typer(
    no_args_is_help=True,
    help="Audio processing toolkit",
)

@app.command()
def main():
    """
    Welcome to the audio processing toolkit.
    Run with --help to see available commands.
    """

@app.command()
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

@app.command()
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

if __name__ == "__main__":
    app()

