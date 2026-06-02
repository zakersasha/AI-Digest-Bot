MESSAGE_SCORING_PROMPT = """Analyze this Telegram message.

IMPORTANT: Write the SUMMARY in {language_name} only.

Return:
- importance score from 1 to 10
- summary in 1-2 sentences with concrete details (names, numbers, actions, outcomes)

Format your response exactly as:
SCORE: <number>
SUMMARY: <one or two sentences>

Message:
{message}"""

FINAL_DIGEST_PROMPT = """Create a digest from these Telegram message summaries.

IMPORTANT:
- Write the entire digest in {language_name} only.
- Each numbered highlight must be 1-2 useful sentences (not vague one-liners).
- At the end of EVERY numbered item, append the source link exactly as provided in the input (keep the markdown link unchanged).

Focus on:
- important updates
- trends
- announcements
- insights

Ignore:
- spam
- greetings
- low-value chatter

Format in Telegram Markdown (NOT HTML):
- Use *bold* for section titles
- Numbered items: *1.* text ending with (SOURCE_LINK)
- Section *Key trends:* with bullets starting with •

Example item format:
*1.* OpenAI announced GPT-5 with 2x speed. Pricing starts at $20/month. ([@openai](https://t.me/openai/12345))

Messages:
{messages}"""
