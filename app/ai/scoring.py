import re

from app.ai.base import MessageScore

_SCORE_PATTERN = re.compile(r"SCORE:\s*(\d+)", re.IGNORECASE)
_SUMMARY_PATTERN = re.compile(r"SUMMARY:\s*(.+?)(?=SCORE:|\Z)", re.IGNORECASE | re.DOTALL)


def parse_score_response(raw: str) -> MessageScore:
    score_match = _SCORE_PATTERN.search(raw)
    summary_match = _SUMMARY_PATTERN.search(raw)

    score = int(score_match.group(1)) if score_match else 5
    score = max(1, min(10, score))

    summary = summary_match.group(1).strip() if summary_match else raw.strip()[:200]
    return MessageScore(score=score, summary=summary)


def parse_batch_score_response(raw: str, expected: int) -> list[MessageScore]:
    scores = [int(x) for x in _SCORE_PATTERN.findall(raw)]
    summaries = [s.strip() for s in _SUMMARY_PATTERN.findall(raw)]

    results: list[MessageScore] = []
    for i in range(expected):
        score = scores[i] if i < len(scores) else 5
        score = max(1, min(10, score))
        summary = summaries[i] if i < len(summaries) else ""
        if not summary:
            summary = raw.strip()[:120]
        results.append(MessageScore(score=score, summary=summary[:280]))
    return results


def format_batch_messages(texts: list[str]) -> str:
    return "\n\n".join(f"--- MSG #{i} ---\n{text}" for i, text in enumerate(texts, start=1))
