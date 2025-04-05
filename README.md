# AutoPodcast: Conversation to Podcast Generator

Transform recordings of conversations into polished, structured podcast episodes automatically. This tool leverages AI for transcription, speaker diarization, content summarization (script generation), and voice synthesis (using existing or cloned voices).

## Key Features

*   **Audio Cleaning:** Reduce background noise in the source audio (Optional).
*   **Transcription & Diarization:** Convert speech to text, identifying different speakers.
*   **Script Generation:** Automatically generate a concise podcast script from the transcription using an LLM, tailored to a target length and audience.
*   **Voice Cloning:** Create synthetic voices based on speaker samples from the original audio.
*   **Podcast Synthesis:** Generate the final podcast audio using the generated script and selected/cloned voices.
*   **Cost Estimation:** Provides an estimated cost breakdown before initiating expensive AI tasks.

## Prerequisites

*   Python 3.9+
*   API Keys:
    *   ElevenLabs (required for transcription, voice cloning, text-to-speech)
    *   Google AI / Gemini (required for script generation & speaker reconciliation)
    *   `ffmpeg` installed and available in your system PATH (required by `pydub`).

## Installation

1.  **Clone the repository:**
    ```bash
    git clone <your-repository-url>
    cd auto-podcast
    ```

2.  **Create and activate a virtual environment (recommended):**
    ```bash
    python -m venv .venv
    source .venv/bin/activate # On Windows use `.venv\Scripts\activate`
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Configuration

The tool requires API keys to function. It will prompt you for keys if they are not found as environment variables:

*   `ELEVEN_API_KEY`: Your API key for ElevenLabs.
*   `GOOGLE_API_KEY`: Your API key for Google AI Studio (Gemini).

You can set these as environment variables before running the tool to avoid prompts.

## Usage

The tool is operated via a command-line interface (`cli.py`).

```bash
python cli.py --help
```

### Core Commands

*   **Clean Audio:**
    ```bash
    python cli.py clean <input_audio_file>
    ```
    *(Example: `python cli.py clean ./audio/my_conversation.mp3`)*

*   **Transcribe Audio:**
    ```bash
    python cli.py transcribe <input_audio_file> --speakers <num_speakers> [--force]
    ```
    *(Example: `python cli.py transcribe ./audio/my_conversation_clean.mp3 --speakers 3`)*

*   **Generate Script:**
    ```bash
    python cli.py script <transcription_file> --length <minutes> --audience <audience_type> --type <podcast_type>
    ```
    *(Example: `python cli.py script ./transcription/my_conversation_clean.txt --length 10 --audience technical`)*

*   **Generate Podcast Audio (from Script):**
    *(Uses existing voices)*
    ```bash
    python cli.py generate-podcast-audio <script_file>
    ```
    *(Example: `python cli.py generate-podcast-audio ./transcription/my_conversation_clean_script.txt`)*

*   **List Available Voices from ElevenLabs:**
    ```bash
    python cli.py list-voices
    ```

### Full Pipeline

*   **Generate Podcast from Conversation:**
    *(Combines cleaning (optional), transcription, script generation, voice cloning, and audio synthesis)*
    ```bash
    python cli.py podcast-from-conversation <input_audio_file> --speakers <num> --length <min> [--clean-audio] [--audience <type>] [--podcast-type <type>]
    ```
    *(Example: `python cli.py podcast-from-conversation ./audio/raw_talk.mp3 --speakers 2 --length 15 --clean-audio`)*

## File Structure

*(Brief overview of the `src` directory structure can be added here if desired)*

## TODO / Future Enhancements

*   Implement `pipeline.py` to orchestrate workflow steps cleanly.
*   Implement low-level service wrappers for other LLMs (Anthropic, OpenAI) and ConversationalAI (AssemblyAI, Hume, Murph)
*   Improve progress reporting during long tasks

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
