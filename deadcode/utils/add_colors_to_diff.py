def add_colors_to_diff(diff: str) -> str:
    colorful_lines = []
    for line in diff.split('\n'):
        colorful_line = line
        if line.startswith('-'):
            colorful_line = f'\033[31m{colorful_line}\033[0m'
        if line.startswith('+'):
            colorful_line = f'\033[32m{colorful_line}\033[0m'
        colorful_lines.append(colorful_line)
    return '\n'.join(colorful_lines)
