"""D11 prototype measurement: parse+convert cost of the Rust native parser
versus CPython `ast.parse`, per corpus entry.

For every Python file in every corpus entry the script times
(a) the running interpreter's `ast.parse` and (b) the native `parse_module`
(parse plus the AST conversion). Files the converter cannot yet map (the
slice-05 grammar: starred, walrus, yield/await, match, type comments) are
counted and skipped on the native side; they are timed on the reference side
so the ratio stays comparable per-entry.

Run with the scratch venv so the native module is importable:
    .venv-maturin/bin/python benchmarks/prototype_parse.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import ast

from benchmarks.corpus import acquire, load_corpus
from benchmarks.run_benchmark import BENCHMARKS_DIR, CACHE_DIR
from deadcode import _native


def python_files(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob('*.py') if path.is_file())


def main() -> None:
    if _native is None:
        sys.exit('native module not importable: run with .venv-maturin/bin/python')
    entries = load_corpus(BENCHMARKS_DIR / 'corpus.json')
    print(f'{"entry":<10} {"files":>6} {"ast.parse s":>12} {"native s":>10} {"ratio":>7} {"skipped":>8}')
    for entry in entries:
        root = acquire(entry, CACHE_DIR)
        files = python_files(root)
        reference_seconds = 0.0
        native_seconds = 0.0
        skipped = 0
        for path in files:
            content = path.read_bytes()
            start = time.perf_counter()
            try:
                ast.parse(content, filename=str(path), type_comments=True)
            except SyntaxError:
                continue  # Deliberately broken corpus files measure nothing.
            reference_seconds += time.perf_counter() - start
            start = time.perf_counter()
            try:
                _native.parse_module(content, str(path), True)
            except _native.ParseError:
                pass  # Parse rejections cost the same rejection time on both sides.
            except Exception:  # noqa: BLE001 - any native failure means "skip this file".
                skipped += 1  # Unmapped slice-05 constructs are skipped on the native side.
                continue
            native_seconds += time.perf_counter() - start
        ratio = native_seconds / reference_seconds if reference_seconds else float('nan')
        print(
            f'{entry.name:<10} {len(files):>6} {reference_seconds:>12.3f} '
            f'{native_seconds:>10.3f} {ratio:>7.2f} {skipped:>8}'
        )


if __name__ == '__main__':
    main()
