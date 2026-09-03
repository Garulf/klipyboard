"""Parsing of Flow Launcher's raw settings dict into a typed Settings object.

Mirrors discord-flow's settings module: never raises, falls back to sane
defaults for anything it can't make sense of.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

DEFAULT_API_KEY = ""


@dataclass(frozen=True)
class Settings:
    api_key: str = DEFAULT_API_KEY

    @property
    def has_api_key(self) -> bool:
        return bool(self.api_key)

    @classmethod
    def from_raw(cls, raw: Mapping[str, Any]) -> "Settings":
        return cls(api_key=_coerce_api_key(raw.get("api_key")))


def _coerce_api_key(value: Any) -> str:
    return value.strip() if isinstance(value, str) else DEFAULT_API_KEY
