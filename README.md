# auto-podcast
Create a short podcast from a conversation.

# Walkthrough
1. Load cleaned audio file
2. Transcribe audio with diarization (speaker labels)
3. Use an LLM to shorten this into a 15 minute podcast script (offline)

See autopodcast.ipynb for a walkthrough of the code with an example conversation between 4 friends about AI Therapy.

# TODO
1. include function for audio cleaning (via lalal.ai api or similar)
2. include function for shortening/summarizing into podcast script
3. Generalize script shortening prompt for any number of speakers or podcast length
4. Test with another public conversation
5. make script available via cli
