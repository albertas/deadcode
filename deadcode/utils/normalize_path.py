from pathlib import PurePath


def normalize_path(value: str | PurePath) -> str:
    """Return the path as a string with forward-slash separators."""
    if isinstance(value, PurePath):
        return value.as_posix()

    return str(value).replace('\\', '/')
