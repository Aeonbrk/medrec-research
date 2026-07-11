"""Small validation and canonical-serialization helpers."""

from __future__ import annotations

import json
import math
import os
import re
import tempfile
from collections.abc import Iterable, Mapping
from enum import StrEnum
from hashlib import sha256
from pathlib import Path
from typing import Any, TypeVar

from .errors import ProtocolValidationError

_HEX_SHA256 = re.compile(r"[0-9a-f]{64}")
_IDENTIFIER = re.compile(r"[a-z0-9][a-z0-9_.-]*")
_LOCAL_PATH = re.compile(r"(?:^|[\s=:'\"(])(?:file:|~/|\./|\.\./|/(?!/)\S+|[A-Za-z]:[\\/]|\\\\)")
_EnumT = TypeVar("_EnumT", bound=StrEnum)


def strict_fields(
    value: object,
    *,
    required: Iterable[str],
    optional: Iterable[str] = (),
    context: str,
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ProtocolValidationError(f"{context} must be an object")
    payload = dict(value)
    if any(not isinstance(key, str) for key in payload):
        raise ProtocolValidationError(f"{context} field names must be strings")
    required_set = set(required)
    allowed = required_set | set(optional)
    missing = sorted(required_set - payload.keys())
    if missing:
        raise ProtocolValidationError(f"{context} missing required field(s): {', '.join(missing)}")
    unknown = sorted(payload.keys() - allowed)
    if unknown:
        raise ProtocolValidationError(f"{context} has unknown field(s): {', '.join(unknown)}")
    return payload


def canonical_json(value: object, *, indent: int | None = None) -> str:
    separators = None if indent is not None else (",", ":")
    try:
        return json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            indent=indent,
            separators=separators,
            sort_keys=True,
        )
    except (TypeError, ValueError) as error:
        raise ProtocolValidationError("value must be finite JSON data") from error


def parse_json_object(text: str, *, context: str) -> dict[str, Any]:
    try:
        value = json.loads(text)
    except (json.JSONDecodeError, TypeError) as error:
        raise ProtocolValidationError(f"{context} must be valid JSON") from error
    if not isinstance(value, dict):
        raise ProtocolValidationError(f"{context} must be a JSON object")
    return value


def content_sha256(value: object) -> str:
    return sha256(canonical_json(value).encode("ascii")).hexdigest()


def write_json_atomic(path: str | Path, value: object) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=destination.parent,
        prefix=f".{destination.name}.",
        suffix=".tmp",
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(canonical_json(value, indent=2))
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def require_string(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ProtocolValidationError(f"{field} must be a non-empty string")
    if value != value.strip():
        raise ProtocolValidationError(f"{field} must not contain surrounding whitespace")
    return value


def require_public_string(value: object, *, field: str) -> str:
    result = require_string(value, field=field)
    if _LOCAL_PATH.search(result):
        raise ProtocolValidationError(f"{field} must not contain a local path")
    return result


def require_single_line_public_string(value: object, *, field: str) -> str:
    result = require_public_string(value, field=field)
    if any(ord(character) < 32 or ord(character) == 127 for character in result):
        raise ProtocolValidationError(f"{field} must not contain control characters")
    return result


def require_identifier(value: object, *, field: str) -> str:
    result = require_string(value, field=field)
    if not _IDENTIFIER.fullmatch(result):
        raise ProtocolValidationError(
            f"{field} must use lowercase letters, numbers, dots, dashes, or underscores"
        )
    return result


def require_sha256(value: object, *, field: str) -> str:
    result = require_string(value, field=field)
    if not _HEX_SHA256.fullmatch(result):
        raise ProtocolValidationError(f"{field} must be a lowercase SHA-256 digest")
    return result


def require_int(value: object, *, field: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise ProtocolValidationError(f"{field} must be an integer >= {minimum}")
    return value


def require_probability(value: object, *, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ProtocolValidationError(f"{field} must be a finite number between 0 and 1")
    result = float(value)
    if not math.isfinite(result) or not 0.0 <= result <= 1.0:
        raise ProtocolValidationError(f"{field} must be a finite number between 0 and 1")
    return result


def enum_member(enum_type: type[_EnumT], value: object, *, field: str) -> _EnumT:
    try:
        return enum_type(value)
    except (TypeError, ValueError) as error:
        choices = ", ".join(member.value for member in enum_type)
        raise ProtocolValidationError(f"{field} must be one of: {choices}") from error


__all__: tuple[str, ...] = ()
