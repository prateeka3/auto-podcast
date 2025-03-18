from typer import Typer, Argument
from elevenlabs import ElevenLabs
from client import clean_audio
import os

os.environ["PATH"] = "/usr/local/bin:" + os.environ["PATH"]

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

if __name__ == "__main__":
    app()

