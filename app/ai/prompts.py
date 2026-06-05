TELEGRAM_DIGEST_PROMPT = """Create a short digest from these Telegram channel posts.

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

GMAIL_DIGEST_PROMPT = """Create a short digest from these Gmail inbox emails.

Write the entire digest in {language_name} only.
Pick the most important emails (skip newsletters spam, promos, automated noise).
Up to 10 numbered highlights, 1-2 sentences each.

For each item you MUST end with the email link in parentheses — copy the exact POST_URL
from that email. Never write <LINK> or the word LINK alone.

Example:
1. Invoice from AWS for March. (https://mail.google.com/mail/u/0/#inbox/abc123)

Key trends:
- <trend>

Emails:
{messages}"""
