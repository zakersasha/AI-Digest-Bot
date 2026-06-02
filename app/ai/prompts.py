MESSAGE_SCORING_PROMPT = """Analyze this Telegram message.

Return:
- importance score from 1 to 10
- short summary in 1 sentence

Format your response exactly as:
SCORE: <number>
SUMMARY: <one sentence>

Message:
{message}"""

FINAL_DIGEST_PROMPT = """Create a short digest from these Telegram messages.

Focus only on:
- important updates
- trends
- announcements
- insights

Ignore:
- spam
- greetings
- low-value chatter

Format the response in Telegram Markdown (NOT HTML):
- Use *bold* for section titles and emphasis
- Numbered highlights on separate lines: *1.* First highlight
- End with section *Key trends:* and bullet lines starting with •

Example structure:
*1.* OpenAI released a new model...
*2.* Python 3.13 beta announced...

*Key trends:*
• AI tooling growth
• Increased GPU demand

Do not use # headers or HTML tags. Escape nothing unless required.

Messages:
{messages}"""
