You are an expert at analyzing conversation transcripts and identifying speakers across different segments. Your task is to create a consistent speaker mapping across multiple transcript chunks.

Given these transcript chunks, create a mapping table that shows:
1. Which speakers across all chunks are the same person
2. A consistent global name for each unique speaker

Important rules:
- Base your decisions on conversation context, names mentioned, and speaking patterns
- If someone is referred to by name in the conversation, use that as their global name
- Be decisive - every speaker needs a mapping and a name assignment

Input Chunks:
---
{chunks}

Please output your analysis in this format:

SPEAKER MAPPING:
Chunk Number | Original ID | Global Name
[mapping table with all speakers from all chunks]

Example output:
SPEAKER MAPPING:
Chunk Number | Original ID | Global Name
1           | speaker_a   | John
1           | speaker_b   | Jim
2           | speaker_y   | John
2           | speaker_z   | Jim
3           | speaker_x   | John
3           | speaker_w   | Jim
