import sys
from typing import TextIO


def print_safely(text: str, file: TextIO | None = None) -> None:
    """Print text without crashing when stdout cannot encode it.

    ``file`` defaults to ``sys.stdout``. The stream is never rebound or
    closed. When printing fails, the stream is reconfigured to UTF-8 and the
    print is retried. As a last resort the text is printed with non-ASCII
    characters replaced by ``?``.
    """
    target = file if file is not None else sys.stdout
    try:
        print(text, file=target)
        return
    except UnicodeEncodeError:
        pass

    reconfigure = getattr(target, 'reconfigure', None)
    if callable(reconfigure):
        try:
            reconfigure(encoding='utf-8')
            print(text, file=target)
            return
        except UnicodeEncodeError:
            pass

    print(text.encode('ascii', 'replace').decode('ascii'), file=target)
