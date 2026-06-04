"""Legacy module — scheduling is handled by app.workers.digest_scheduler."""

from app.workers.digest_scheduler import DigestScheduler, get_digest_scheduler, init_digest_scheduler

__all__ = ["DigestScheduler", "get_digest_scheduler", "init_digest_scheduler"]
