import os
import getpass
from elevenlabs import ElevenLabs
from enum import Enum

# --- Constants ---
WORDS_PER_MINUTE = 150

# --- Enums ---
class AudioAIFunction(Enum):
    CLEAN = "clean"
    SPEECH_TO_TEXT = "speech_to_text"
    CLONE_VOICE = "clone_voice"
    TEXT_TO_SPEECH = "text_to_speech"

# --- API Key Management ---
def load_api_keys():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        os.environ["ANTHROPIC_API_KEY"] = getpass.getpass("Enter API key for Anthropic: ")
    if not os.environ.get("GEMINI_API_KEY"):
        os.environ["GEMINI_API_KEY"] = getpass.getpass("Enter API key for Gemini: ")
    if not os.environ.get("ELEVENLABS_API_KEY"):
        os.environ["ELEVENLABS_API_KEY"] = getpass.getpass("Enter API key for ElevenLabs: ")

# --- Singletons ---
class ElevenLabsClientSingleton:
    _instance = None
    _client = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ElevenLabsClientSingleton, cls).__new__(cls)
            load_api_keys()
            if not os.environ.get("ELEVENLABS_API_KEY"):
                 raise ValueError("ELEVENLABS_API_KEY environment variable not set.")
            cls._client = ElevenLabs()
        return cls._instance

    @property
    def client(self) -> ElevenLabs:
        if self._client is None:
            raise RuntimeError("ElevenLabs client has not been initialized.")
        return self._client

# Function to easily get the client instance
def get_elevenlabs_client() -> ElevenLabs:
    return ElevenLabsClientSingleton().client

# Load keys on module import
load_api_keys()
