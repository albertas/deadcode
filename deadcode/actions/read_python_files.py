from deadcode.data_types import FileContent, Filename

# Files one worker reads and parses sequentially before moving on to the next
# chunk.
READ_CHUNK_FILES = 32
# Chunks processed concurrently with `asyncio.gather`. Together with
# `READ_CHUNK_FILES` this bounds how many file contents are held in memory at
# once: a directory of any size is processed in waves instead of being loaded
# up front.
DEFAULT_WORKERS = 2


def read_file_chunk(filenames: list[Filename]) -> list[FileContent]:
    """Read the given files sequentially and return their bytes in the same order."""
    file_contents: list[FileContent] = []
    for filename in filenames:
        with open(filename, 'rb') as f:
            file_contents.append(f.read())
    return file_contents


def chunk_filenames(filenames: list[Filename], *, chunk_size: int = READ_CHUNK_FILES) -> list[list[Filename]]:
    """Split the file list into chunks of at most `chunk_size` files."""
    chunk_size = max(1, chunk_size)
    return [filenames[start : start + chunk_size] for start in range(0, len(filenames), chunk_size)]
