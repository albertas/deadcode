import math

from deadcode.data_types import FileContent, Filename

# Importing asyncio and starting its event loop costs more than reading a tiny
# corpus sequentially, so the async stage only takes over once the reads are
# large enough to amortise that fixed cost. This keeps small runs at the
# baseline speed while large runs still overlap their I/O.
ASYNC_READ_MIN_FILES = 100


def _read_chunk(filenames: list[Filename]) -> list[FileContent]:
    """Read the given files sequentially and return their bytes in the same order."""
    file_contents: list[FileContent] = []
    for filename in filenames:
        with open(filename, 'rb') as f:
            file_contents.append(f.read())
    return file_contents


async def read_python_files(filenames: list[Filename], *, workers: int = 8) -> list[FileContent]:
    """Read every file once, spreading the reads over at most `workers` executor tasks."""
    import asyncio  # noqa: PLC0415

    if not filenames:
        return []

    chunk_count = min(workers, len(filenames))
    chunk_size = math.ceil(len(filenames) / chunk_count)
    chunks = [filenames[start : start + chunk_size] for start in range(0, len(filenames), chunk_size)]

    tasks = [asyncio.to_thread(_read_chunk, chunk) for chunk in chunks]
    chunk_results = await asyncio.gather(*tasks)

    return [file_content for chunk_result in chunk_results for file_content in chunk_result]


def read_python_files_sync(filenames: list[Filename], *, workers: int = 8) -> list[FileContent]:
    """Synchronous bridge from the visitor to the read stage.

    Small corpora skip the event loop entirely: the fixed cost of importing
    asyncio and starting its worker threads is larger than the sequential reads.
    """
    if len(filenames) < ASYNC_READ_MIN_FILES:
        return _read_chunk(filenames)

    import asyncio  # noqa: PLC0415

    return asyncio.run(read_python_files(filenames, workers=workers))
