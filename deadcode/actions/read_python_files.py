from deadcode.actions.parse_abstract_syntax_tree import parse_abstract_syntax_tree_or_none
from deadcode.data_types import AbstractSyntaxTree, FileContent, Filename

READ_CHUNK_FILES = 32
# D10 fallback: parsing holds the GIL, so two worker threads are slower than one.
DEFAULT_WORKERS = 1


def chunk_filenames(filenames: list[Filename], *, chunk_size: int = READ_CHUNK_FILES) -> list[list[Filename]]:
    """Split filenames into contiguous chunks, treating a non-positive size as one."""
    effective_chunk_size = max(1, chunk_size)
    return [filenames[index : index + effective_chunk_size] for index in range(0, len(filenames), effective_chunk_size)]


def read_file_chunk(filenames: list[Filename]) -> list[tuple[Filename, FileContent]]:
    """Read every file in the chunk sequentially, preserving input order and duplicates."""
    files = []
    for filename in filenames:
        with open(filename, 'rb') as file:  # noqa: PTH123
            files.append((filename, file.read()))
    return files


def _read_and_parse_chunk(filenames: list[Filename]) -> list[tuple[Filename, FileContent, AbstractSyntaxTree | None]]:
    """Read and parse every file in the chunk, preserving input order and duplicates."""
    return [
        (filename, file_content, parse_abstract_syntax_tree_or_none(file_content, filename))
        for filename, file_content in read_file_chunk(filenames)
    ]
