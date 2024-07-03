def add_colors_to_diff(diff: bytes) -> bytes:
    colorful_lines = []
    for line in diff.split(b'\n'):
        colorful_line = line
        if line.startswith(b'-'):
            colorful_line = b'\033[31m' + colorful_line + b'\033[0m'
        if line.startswith(b'+'):
            colorful_line = b'\033[32m' + colorful_line + b'\033[0m'
        colorful_lines.append(colorful_line)
    return b'\n'.join(colorful_lines)
