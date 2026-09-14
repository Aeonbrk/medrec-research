"""Offline no-op WandB shim for the unchanged HypeMed sanity run."""

config = {}


class _Run:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


def init(*_args, **_kwargs):
    return _Run()


def log(*_args, **_kwargs):
    return None


def finish(*_args, **_kwargs):
    return None
