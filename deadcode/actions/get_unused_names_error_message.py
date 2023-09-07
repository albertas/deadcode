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

    if args.no_color:
        return "\n".join(
            [f"{item.filename_with_position} DC100 Global {item.name} is never used" for item in unused_names]
        )

    return "\n".join(
        [
            f"{item.filename_with_position} \033[91mDC100\033[0m Global \033[1m{item.name}\033[0m is never used"
            for item in unused_names
        ]
    )
