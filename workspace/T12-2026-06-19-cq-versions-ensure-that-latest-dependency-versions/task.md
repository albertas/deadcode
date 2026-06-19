# Task

Ensure the project's Python dependencies are pinned to their latest available
versions across all dependency-declaration and lock artifacts (pyproject.toml,
uv.lock, requirements.txt, requirements-dev.txt), keeping the resolved set
internally consistent and passing the project's checks. This keeps the toolchain
current and reduces exposure to outdated or vulnerable packages.

Ticket: [T12] [cq:versions] from BACKLOG.md.
