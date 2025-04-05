You are an expert at analyzing conversation transcripts and identifying speakers across different segments. Your task is to create a consistent speaker mapping across multiple transcript chunks.

Given these transcript chunks:
---
{chunks}
---

Analyze the conversation context, names mentioned, and speaking patterns to determine which speakers across different chunks are the same person.

Output a list of JSON objects where each object represents a single speaker instance in a chunk and has the following keys:
- "chunk_number": (integer) The 1-based index of the chunk.
- "original_id": (string) The speaker ID as it appears in that chunk (e.g., "speaker_0", "speaker_1").
- "global_name": (string) The consistent name you have assigned to this speaker across all chunks (e.g., "Speaker 1", "John", "Host"). If someone is referred to by name, use that name.

Every speaker instance from every chunk must be included in the output list.

Use this JSON schema:
SpeakerMapping: {{'chunk_number': int, 'original_id': str, 'global_name': str}}
Return: list[SpeakerMapping]