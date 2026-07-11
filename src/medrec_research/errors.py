"""Errors raised at Unified Research Protocol boundaries."""


class ProtocolValidationError(ValueError):
    """Raised when protocol data is incomplete, unsafe, or inconsistent."""


__all__ = ("ProtocolValidationError",)
