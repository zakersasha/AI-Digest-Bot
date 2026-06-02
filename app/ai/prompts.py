SINGLE_DIGEST_PROMPT = """Create a short digest from these Telegram channel posts.

Write the entire digest in {language_name} only.
Pick the most important updates (skip spam, greetings, ads).
Up to 10 numbered highlights, 1-2 sentences each.
At the end of each item, append the LINK line unchanged (markdown).

Format:
1. <highlight> <LINK>
2. <highlight> <LINK>

Key trends:
- <trend>

Posts:
{messages}"""
