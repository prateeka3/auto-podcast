# auto-podcast
Create a short podcast from a conversation.

# Walkthrough
1. Load cleaned audio file
2. Transcribe audio with diarization (speaker labels)
3. Use an LLM to shorten this into a 15 minute podcast script (offline)
4. clone voices with longest voice clips for each speaker from original audio
5. generate shortened podcast audio using script and cloned speaker voices

See autopodcast.ipynb for a walkthrough of the code with an example conversation between 4 friends about AI Therapy.

# TODO
- using and specifying the LLM model to use
- speaker identification as a cli option
- speaker identification as an option in transcription
- include function for shortening/summarizing into podcast script
- Generalize script shortening prompt for any number of speakers or podcast length
- Test with another public conversation
- Instead of passing the ElevenLabs client around, create a singleton wrapper
