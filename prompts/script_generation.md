# Conversation to Podcast Script Adaptation

<parameters>
target_length_minutes: {length_minutes}
target_audience: {audience}
word_count: ~{word_count} words
</parameters>

<example>
MAYA: Welcome to our conversation about home cooking. I'm joined by Elena and Jackson today.
ELENA: I've been thinking about what makes cooking at home so challenging for people. Maya, what's your biggest obstacle?
MAYA: Time management, definitely. After a long work day, it's so tempting to just order takeout.
JACKSON: For me it's planning. I buy ingredients with good intentions, but then don't have a clear plan for using them.
ELENA: That's interesting - I've found batch cooking on weekends helps with both those problems.
MAYA: Thanks everyone for sharing your insights today. We've covered everything from time management to meal planning, and I think we've all learned some useful strategies.
</example>

<input_format>
Raw conversation transcript with speaker labels. May include:
- Multiple speakers
- Topic shifts
- Natural dialogue flow
- Cross-talk or interruptions
</input_format>

<output_requirements>
1. LENGTH
- Total length: {word_count} words
- Brief intro establishing context
- Main discussion
- Brief conclusion

2. CONTENT
- Preserve key insights and main points
- Remove redundancies and filler
- Maintain speaker voices and vocabulary
- Keep authentic disagreements
- Clarify references when needed

3. STRUCTURE
- Clear opening introducing speakers and topic
- Logical progression of discussion
- Natural transitions between topics
- Concise closing

4. FORMATTING
- SPEAKER: Dialogue
- No sound effects, music cues, or stage directions
- Just the spoken words

5. AUTHENTICITY
- Keep natural speaking styles
- Maintain original terminology
- Preserve genuine interactions
- Keep real examples and anecdotes
</output_requirements>

<output_format>
Same as input. A raw conversation transcript between the speakers from the input but as a podcast adhering to all the rules.
</output_format>

<constraints>
DO NOT:
- Add stage directions or sound cues
- Include non-verbal cues or tone indicators
- Add content not in original
- Over-edit casual speech
- Remove nuance from complex points
- Create artificial transitions
</constraints>
