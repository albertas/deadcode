import sys


def print_safely(text: str) -> None:
    """Print text without crashing when stdout cannot encode it.

    The stream is never rebound or closed. When printing fails, the stream is
    reconfigured to UTF-8 and the print is retried. As a last resort the text
    is printed with non-ASCII characters replaced by ``?``.
    """
    try:
        print(text)
        return
    except UnicodeEncodeError:
        pass

    reconfigure = getattr(sys.stdout, 'reconfigure', None)
    if callable(reconfigure):
        try:
            reconfigure(encoding='utf-8')
            print(text)
            return
        except UnicodeEncodeError:
            pass

    print(text.encode('ascii', 'replace').decode('ascii'))
