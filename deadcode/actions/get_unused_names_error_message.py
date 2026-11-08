from collections.abc import Iterable

from deadcode.data_types import Args
from deadcode.visitor.code_item import CodeItem
from deadcode.visitor.ignore import _match


def get_unused_names_error_message(unused_names: Iterable[CodeItem], args: Args) -> str | None:
    unused_names = list(unused_names)
    had_unused_names = bool(unused_names)

    if args.only:
        unused_names = [item for item in unused_names if _match(item.filename, args.only)]

    if not unused_names:
        # Filtering away every finding keeps the historical empty message instead of reporting a clean run.
        return '' if had_unused_names and not args.count and not args.quiet else None

    if args.quiet:
        return ''

    if args.count:
        return f'{len(unused_names)}'

    messages = []
    for item in unused_names:
        message = f'{item.filename_with_position} \033[91m{item.error_code}\033[0m '
        message += item.message or (
            f'{item.type_.replace("_", " ").capitalize()} `\033[1m{item.name}\033[0m` is never used'
        )
        if args.no_color:
            message = message.replace('\033[91m', '').replace('\033[1m', '').replace('\033[0m', '')
        messages.append(message)

    if args.fix:
        message = f'\nRemoved \033[1m{len(messages)}\033[0m unused code item{"s" if len(messages) > 1 else ""}!'
        if args.no_color:
            message = message.replace('\x1b[1m', '').replace('\x1b[0m', '')
        messages.append(message)

    return '\n'.join(messages)
