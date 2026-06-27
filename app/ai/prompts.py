NO_NEW_CONTENT_MARKER = "NO_NEW_CONTENT"

_LINK_RULES = """
Link format for each item: one markdown hyperlink [{link_label}](POST_URL) — copy POST_URL exactly.
Never use raw URLs in parentheses. Never write <LINK> or LINK alone.
"""

_SKIP_RULES = """
Always SKIP and never include in the digest:
- Ads, sponsored posts, promos, affiliate links, discounts, giveaways, "реклама", #ad
- Greetings, memes, engagement bait, empty reposts
- Gmail: marketing newsletters, promos, spam, bulk automated mail (unless security/billing critical)
"""

_SELECTION_RULES = """
Select ONLY genuinely important items (0–7). Do NOT summarize every message.
Quality over quantity: one strong item beats ten weak ones.
If nothing important remains, or only ads/spam/promo — respond with exactly:
NO_NEW_CONTENT
(no other text, no header, no list)
"""

_TELEGRAM_MULTI_CHANNEL_RULES = """
When posts come from several channels (sections marked === Channel Name ===):
- Pick the best genuinely important item from EACH channel that has worthy news.
- If a channel has only ads, memes, or low-value posts — include nothing from it.
- Do NOT fill the digest from a single channel when other channels also have informative items.
- Prefer one strong item per channel before adding a second item from the same channel.
"""

TELEGRAM_DIGEST_PROMPT = (
    "Create a digest from Telegram channel posts.\n\n"
    "Write in {language_name} only.\n"
    f"{_SKIP_RULES.strip()}\n"
    f"{_SELECTION_RULES.strip()}\n"
    f"{_TELEGRAM_MULTI_CHANNEL_RULES.strip()}\n"
    f"{_LINK_RULES.strip()}\n\n"
    "Each item MUST start with the channel name in bold markdown: **Channel Name** — then the summary.\n"
    "Use the exact SOURCE name from each post block (not @username).\n\n"
    "Example item:\n"
    "1. **Москва 24/7** — Metro line extension announced for 2026. [{link_label}](https://t.me/moscowmap/76844)\n\n"
    "Posts:\n"
    "{messages}"
)

GMAIL_DIGEST_PROMPT = (
    "Create a digest from Gmail inbox emails.\n\n"
    "Write in {language_name} only.\n"
    f"{_SKIP_RULES.strip()}\n"
    f"{_SELECTION_RULES.strip()}\n"
    f"{_LINK_RULES.strip()}\n\n"
    "Example item:\n"
    "1. AWS invoice for March needs payment. [{link_label}](https://mail.google.com/mail/u/0/#inbox/abc123)\n\n"
    "Emails:\n"
    "{messages}"
)

LINKEDIN_DIGEST_PROMPT = (
    "Create a digest from LinkedIn profile posts.\n\n"
    "Write in {language_name} only.\n"
    f"{_SKIP_RULES.strip()}\n"
    f"{_SELECTION_RULES.strip()}\n"
    f"{_LINK_RULES.strip()}\n\n"
    "Example item:\n"
    "1. Company raised Series B funding. [{link_label}](https://www.linkedin.com/feed/update/urn:li:activity:123)\n\n"
    "Posts:\n"
    "{messages}"
)

COMBINED_DIGEST_PROMPT = (
    "Create a digest from Telegram posts and Gmail emails.\n\n"
    "Write in {language_name} only.\n"
    f"{_SKIP_RULES.strip()}\n"
    f"{_SELECTION_RULES.strip()}\n"
    f"{_LINK_RULES.strip()}\n\n"
    "Content:\n"
    "{messages}"
)
