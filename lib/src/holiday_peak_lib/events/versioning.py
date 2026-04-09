"""Shared schema-version policy for canonical event envelopes."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Final

SCHEMA_VERSION_PATTERN: Final[re.Pattern[str]] = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)$")
CURRENT_EVENT_SCHEMA_VERSION: Final[str] = "1.0"


@dataclass(frozen=True, slots=True)
class SchemaVersion:
    """Parsed major.minor schema version."""

    major: int
    minor: int

    @classmethod
    def parse(cls, value: str) -> "SchemaVersion":
        """Parse a schema version string using the canonical major.minor format."""

        if not isinstance(value, str):
            raise ValueError("schema_version must be a string in <major>.<minor> format")

        normalized = value.strip()
        match = SCHEMA_VERSION_PATTERN.fullmatch(normalized)
        if match is None:
            raise ValueError("schema_version must use <major>.<minor> format")

        return cls(major=int(match.group(1)), minor=int(match.group(2)))

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}"


@dataclass(frozen=True, slots=True)
class SchemaCompatibilityPolicy:
    """Strategy-style compatibility policy for canonical event envelopes."""

    current_version: str = CURRENT_EVENT_SCHEMA_VERSION

    def parse(self, value: str | SchemaVersion) -> SchemaVersion:
        """Return a parsed schema version instance."""

        if isinstance(value, SchemaVersion):
            return value
        return SchemaVersion.parse(value)

    def normalize(self, value: Any | None) -> str:
        """Normalize a raw schema version and enforce current-major compatibility."""

        if value is None:
            return self.current_version

        version = self.parse(value)
        self.assert_compatible(version)
        return str(version)

    def assert_compatible(self, value: str | SchemaVersion) -> None:
        """Raise when a payload version uses an unsupported major version."""

        version = self.parse(value)
        current = self.parse(self.current_version)
        if version.major != current.major:
            raise ValueError(
                "Unsupported schema_version major "
                f"{version.major}; current canonical major is {current.major}"
            )

    def is_compatible(self, value: str | SchemaVersion) -> bool:
        """Return whether a payload version is compatible with the current consumer."""

        try:
            self.assert_compatible(value)
        except ValueError:
            return False
        return True
