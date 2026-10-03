"""Pluggable OTP delivery.

Dev uses the console provider (prints the code to the server log and stashes
the latest code per channel+target in memory so tests can pull it). Prod will
plug in Twilio or an Egyptian gateway behind the same interface.
"""

from __future__ import annotations

import logging
from typing import Protocol

log = logging.getLogger(__name__)

# Dev-only in-memory stash: (channel, target) -> code. Tests read this; prod
# providers do not populate it. Not thread-safe by design — single-worker dev.
LAST_CODES: dict[tuple[str, str], str] = {}


class OtpProvider(Protocol):
    def send(self, *, channel: str, target: str, code: str) -> None: ...


class ConsoleProvider:
    def send(self, *, channel: str, target: str, code: str) -> None:
        log.info("[OTP:%s] -> %s = %s", channel, target, code)
        LAST_CODES[(channel, target)] = code


class TwilioProvider:
    """Stub — real Twilio wiring lands with Phase 1 ops task."""

    def send(self, *, channel: str, target: str, code: str) -> None:  # pragma: no cover
        raise NotImplementedError("TwilioProvider is a Phase 1 ops task")


def get_provider(name: str) -> OtpProvider:
    if name == "console":
        return ConsoleProvider()
    if name == "twilio":
        return TwilioProvider()
    raise ValueError(f"Unknown OTP provider: {name}")
