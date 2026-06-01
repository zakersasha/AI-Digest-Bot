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

Format the digest like this:
1. <highlight>
2. <highlight>
3. <highlight>

Key trends:
- <trend>
- <trend>

Messages:
{messages}"""
