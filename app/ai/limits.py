from dataclasses import dataclass


@dataclass(frozen=True)
class DigestAiLimits:
    max_context_tokens: int
    max_output_tokens: int
    max_messages: int
    message_max_chars: int
    min_message_chars: int
    reasoning_effort: str | None
