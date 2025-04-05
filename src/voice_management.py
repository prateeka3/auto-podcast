from collections import defaultdict
from elevenlabs import ElevenLabs, SpeechToTextWordResponseModel
from pathlib import Path
import os

# Import the singleton client getter
from .config import get_elevenlabs_client

class VoiceManager:
    """Handles voice-related operations including cloning and sample management"""
    def __init__(self):
        self.client = get_elevenlabs_client()
        self.available_voices = None
        self.sample_dir = Path("audio/voices")
        self.sample_dir.mkdir(parents=True, exist_ok=True)

    def get_available_voices(self) -> list:
        """Get available voices from ElevenLabs (excluding premade)."""
        if self.available_voices is None:
            all_voices = self.client.voices.get_all().voices
            self.available_voices = list(filter(lambda v: v.category != "premade", all_voices))
        return self.available_voices

    def clone_voice(self, voice_sample_filepath: str, voice_name: str) -> str:
        """
        Clone a single voice using ElevenLabs.
        """
        sample_path = Path(voice_sample_filepath)
        if not sample_path.exists():
            raise FileNotFoundError(f"Sample file not found: {sample_path}")
        if sample_path.stat().st_size == 0:
            raise ValueError(f"Empty sample file: {sample_path}")

        with open(sample_path, 'rb') as f:
            voice = self.client.voices.add(
                name=voice_name,
                files=[f],
            )
        print(f"Successfully cloned voice '{voice_name}' ({voice.voice_id})")
        return voice.voice_id

    def delete_generated_voices(self, speaker_voice_ids: dict):
        """Delete generated voices by ID."""
        print("Deleting generated voices...")
        deleted_count = 0
        for voice_id in speaker_voice_ids.values():
            try:
                self.client.voices.delete(voice_id)
                deleted_count += 1
            except Exception as e:
                 print(f"Warning: Could not delete voice {voice_id}: {e}")
        print(f"Deleted {deleted_count} voices.")

    def extract_samples_from_transcription(self, raw_transcription: list[SpeechToTextWordResponseModel], clone_sample_length_ms: int) -> dict[str, list[tuple[int, int]]]:
        """Extract samples from a raw transcription."""
        samples = defaultdict(list)
        samples_length = defaultdict(int)
        for word in raw_transcription:
            # Add type check for word object
            assert word.speaker_id and word.start and word.end
            if hasattr(word, 'speaker_id') and hasattr(word, 'start') and hasattr(word, 'end'):
                speaker_id = word.speaker_id
            if speaker_id and samples_length[speaker_id] < clone_sample_length_ms:
                samples[speaker_id].append((word.start * 1000, word.end * 1000))
                samples_length[speaker_id] += int((word.end - word.start) * 1000)
        return samples
