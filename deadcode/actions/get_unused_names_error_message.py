from typing import List, Optional

from deadcode.data_types import Args
from deadcode.visitor.code_item import CodeItem


def get_unused_names_error_message(unused_names: List[CodeItem], args: Args) -> Optional[str]:
    if not unused_names:
        return None

    if args.quiet:
        return ""

    if args.count:
        return f"{len(unused_names)}"

    error_messages_of_unused_code_items = []
    for item in unused_names:
        error_message = (
            f"{item.filename_with_position} "
            f"\033[91m{item.error_code}\033[0m "
            f"{item.type_.replace('_', ' ').capitalize()} "
            f"`\033[1m{item.name}\033[0m` "
            f"is never used"
        )
        if args.no_color:
            error_message = error_message.replace("\033[91m", "").replace("\033[1m", "").replace("\033[0m", "")
        error_messages_of_unused_code_items.append(error_message)

    return "\n".join(error_messages_of_unused_code_items)
