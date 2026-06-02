import re

# Characters that must be escaped in Telegram legacy Markdown outside code blocks
_ESCAPE_CHARS = re.compile(r"([_*\[\]`])")


def escape_markdown(text: str) -> str:
    return _ESCAPE_CHARS.sub(r"\\\1", text)
