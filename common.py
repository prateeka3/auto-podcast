from enum import Enum

WORDS_PER_MINUTE = 150
class AudioAIFunction(Enum):
    CLEAN = "clean"
    SPEECH_TO_TEXT = "speech_to_text"
    CLONE_VOICE = "clone_voice"
    TEXT_TO_SPEECH = "text_to_speech"
    