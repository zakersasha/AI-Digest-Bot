SINGLE_DIGEST_PROMPT = """Create a short digest from these Telegram channel posts.

Write the entire digest in {language_name} only.
Pick the most important updates (skip spam, greetings, ads).
Up to 10 numbered highlights, 1-2 sentences each.

For each item you MUST end with the post link in parentheses — copy the exact POST_URL
from that post (starts with https://t.me/). Never write <LINK> or the word LINK alone.

Example:
1. Metro line extension announced. (https://t.me/moscowmap/76844)

Key trends:
- <trend>

Posts:
{messages}"""
