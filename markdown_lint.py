import re
import sys
import argparse

BBCODE_TAG_RE = re.compile(r'\[(/?)([A-Za-z]+)(=[^\]]*)?\]')
HTML_INLINE_TAG_RE = re.compile(r'</?(kbd|sub|sup|b|i|em|strong)>')
ADMONITION_RE = re.compile(r'^\s*>\s*\[!([A-Za-z]+)\]\s*$')
KNOWN_ADMONITIONS = {'NOTE', 'WARNING', 'IMPORTANT', 'TIP', 'CAUTION'}


def check_bbcode(text, filename):
    errors = []
    stack = []
    for lineno, line in enumerate(text.splitlines(), 1):
        for m in BBCODE_TAG_RE.finditer(line):
            closing, name, _value = m.groups()
            name_lower = name.lower()
            if not closing:
                stack.append((name_lower, lineno))
            else:
                if not stack:
                    errors.append(f"{filename}:{lineno}: [/{name}] has no matching open tag")
                elif stack[-1][0] == name_lower:
                    stack.pop()
                else:
                    errors.append(f"{filename}:{lineno}: [/{name}] does not match innermost open tag [{stack[-1][0]}] (opened line {stack[-1][1]})")
                    stack.pop()
    for name, lineno in stack:
        errors.append(f"{filename}:{lineno}: [{name}] was never closed")
    return errors


FENCE_OPEN_RE = re.compile(r'^\s*(`{3,})')


def check_github_markdown(text, filename):
    errors = []
    stack = []
    fence_len = None
    for lineno, line in enumerate(text.splitlines(), 1):
        if fence_len is not None:
            if re.match(r'^\s*`{' + str(fence_len) + r',}\s*$', line):
                fence_len = None
            continue
        m = FENCE_OPEN_RE.match(line)
        if m:
            fence_len = len(m.group(1))
            continue
        for m in HTML_INLINE_TAG_RE.finditer(line):
            tag = m.group(0)
            name = m.group(1).lower()
            if not tag.startswith('</'):
                stack.append((name, lineno))
            else:
                if not stack:
                    errors.append(f"{filename}:{lineno}: </{name}> has no matching open tag")
                elif stack[-1][0] == name:
                    stack.pop()
                else:
                    errors.append(f"{filename}:{lineno}: </{name}> does not match innermost open tag <{stack[-1][0]}> (opened line {stack[-1][1]})")
                    stack.pop()

        if line.count('**') % 2 != 0:
            errors.append(f"{filename}:{lineno}: odd number of ** (unbalanced bold)")

        stripped = line.strip()
        if stripped.startswith('>'):
            m = ADMONITION_RE.match(line)
            if m and m.group(1).upper() not in KNOWN_ADMONITIONS:
                errors.append(f"{filename}:{lineno}: unrecognized admonition type [!{m.group(1)}] (expected one of {sorted(KNOWN_ADMONITIONS)})")

        if stripped.startswith('|') and stripped.endswith('|') and not re.match(r'^\|[\s:|-]+\|$', stripped):
            cell_count = stripped.count('|') - 1
            if cell_count < 1:
                errors.append(f"{filename}:{lineno}: malformed table row (no cells)")

    for name, lineno in stack:
        errors.append(f"{filename}:{lineno}: <{name}> was never closed")
    return errors


def check_plain_markdown(text, filename):
    errors = []
    fence_len = None
    for lineno, line in enumerate(text.splitlines(), 1):
        if fence_len is not None:
            if re.match(r'^\s*`{' + str(fence_len) + r',}\s*$', line):
                fence_len = None
            continue
        m = FENCE_OPEN_RE.match(line)
        if m:
            fence_len = len(m.group(1))
            continue
        if line.count('**') % 2 != 0:
            errors.append(f"{filename}:{lineno}: odd number of ** (unbalanced bold)")
        if line.count('`') % 2 != 0:
            errors.append(f"{filename}:{lineno}: odd number of ` (unbalanced code span)")
    return errors


CHECKERS = {
    'bbcode': check_bbcode,
    'github': check_github_markdown,
    'plain': check_plain_markdown,
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('files', nargs='+')
    args = parser.parse_args()

    all_errors = []
    checked = []
    for entry in args.files:
        if ':' not in entry:
            print(f"::error::Expected path:format (format is one of {list(CHECKERS)}), got: {entry}", file=sys.stderr)
            sys.exit(2)
        path, fmt = entry.rsplit(':', 1)
        if fmt not in CHECKERS:
            print(f"::error::Unknown format '{fmt}' for {path} - expected one of {list(CHECKERS)}", file=sys.stderr)
            sys.exit(2)
        try:
            with open(path) as f:
                text = f.read()
        except FileNotFoundError:
            continue
        checked.append(path)
        all_errors.extend(CHECKERS[fmt](text, path))

    print("## Markdown syntax check")
    print()
    print(f"Checked: {', '.join(checked) if checked else '(no files found)'}")
    print()
    if all_errors:
        print(f"**{len(all_errors)} issue(s) found:**")
        print()
        for e in all_errors:
            print(f"- {e}")
            print(f"::error::{e}")
        sys.exit(1)
    else:
        print("No syntax issues found.")


if __name__ == '__main__':
    main()
