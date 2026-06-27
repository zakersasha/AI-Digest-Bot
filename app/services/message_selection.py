from collections import defaultdict

from app.services.content_message import ContentMessage


def interleave_messages_by_source(
    messages: list[ContentMessage],
    limit: int,
) -> list[ContentMessage]:
    """Round-robin newest messages across channels so multi-source digests stay balanced."""
    if limit <= 0 or not messages:
        return []

    buckets: dict[str, list[ContentMessage]] = defaultdict(list)
    for msg in messages:
        buckets[msg.source].append(msg)

    for bucket in buckets.values():
        bucket.sort(key=lambda m: m.date, reverse=True)

    sources = sorted(buckets.keys())
    selected: list[ContentMessage] = []
    round_idx = 0

    while len(selected) < limit:
        added = False
        for source in sources:
            bucket = buckets[source]
            if round_idx < len(bucket):
                selected.append(bucket[round_idx])
                added = True
                if len(selected) >= limit:
                    break
        if not added:
            break
        round_idx += 1

    return selected


def select_balanced_messages_by_source(
    messages: list[ContentMessage],
    limit: int,
) -> list[ContentMessage]:
    """
    For multi-channel digests: cap messages per channel, then interleave.

    Prevents one very active channel from filling the AI context while others
    only contribute one or two posts.
    """
    if limit <= 0 or not messages:
        return []

    buckets: dict[str, list[ContentMessage]] = defaultdict(list)
    for msg in messages:
        buckets[msg.source].append(msg)

    for bucket in buckets.values():
        bucket.sort(key=lambda m: m.date, reverse=True)

    if len(buckets) <= 1:
        return next(iter(buckets.values()))[:limit]

    per_source_cap = max(2, (limit + len(buckets) - 1) // len(buckets))
    trimmed: list[ContentMessage] = []
    for source in sorted(buckets.keys()):
        trimmed.extend(buckets[source][:per_source_cap])

    return interleave_messages_by_source(trimmed, limit)
