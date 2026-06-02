SINGLE_DIGEST_PROMPT = """Create a Telegram digest from the channel posts below.

IMPORTANT:
- Write the entire digest in {language_name} only.
- Pick only important updates (skip spam, greetings, ads, low-value chatter).
- Up to 12 numbered highlights; each 1-2 concrete sentences.
- At the end of EVERY numbered item, append the source link exactly as in LINK (keep markdown unchanged).

Format in Telegram Markdown (NOT HTML):
- Use *bold* for section titles
- Numbered items: *1.* text ending with the LINK line
- Section *Key trends:* with bullets starting with •

Example item:
*1.* City hall announced new metro line extension. ([@channel](https://t.me/channel/123))

Posts:
{messages}"""
