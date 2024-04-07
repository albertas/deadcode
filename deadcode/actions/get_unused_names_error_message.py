from typing import Iterable, Optional

from deadcode.data_types import Args
from deadcode.visitor.code_item import CodeItem


def get_unused_names_error_message(unused_names: Iterable[CodeItem], args: Args) -> Optional[str]:
    unused_names = list(unused_names)

    if not unused_names:
        return None

    if args.quiet:
        return ''

    if args.count:
        return f'{len(unused_names)}'

    messages = []
    for item in unused_names:
        message = f'{item.filename_with_position} \033[91m{item.error_code}\033[0m '
        message += item.message or (
            f"{item.type_.replace('_', ' ').capitalize()} " f"`\033[1m{item.name}\033[0m` " f"is never used"
        )
        if args.no_color:
            message = message.replace('\033[91m', '').replace('\033[1m', '').replace('\033[0m', '')
        messages.append(message)

    if args.fix:
        message = f"\nRemoved \033[1m{len(unused_names)}\033[0m unused code item{'s' if len(unused_names) > 1 else ''}!"
        if args.no_color:
            message = message.replace('\x1b[1m', '').replace('\x1b[0m', '')
        messages.append(message)

    return '\n'.join(messages)
