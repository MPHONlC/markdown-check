import re
import sys
import argparse
from datetime import datetime

VERB_COLORS = [
    (re.compile(r'^(Added|Introduced)\b'), 'Lime', True),
    (re.compile(r'^(Implemented)\b'), '#4CAF50', False),
    (re.compile(r'^(Improved)\b'), '#00BFFF', False),
    (re.compile(r'^(Updated)\b'), '#1E90FF', False),
    (re.compile(r'^(Optimized|Increased|Changed)\b'), '#00FFFF', False),
    (re.compile(r'^(Fixed|Adjusted)\b'), '#FF6347', True),
    (re.compile(r'^(Removed)\b'), '#FF4500', True),
    (re.compile(r'^(New)\b'), 'Lime', True),
    (re.compile(r'^(Now)\b'), '#1E90FF', False),
]

SLASH_COMMAND_RE = re.compile(r'/[A-Za-z][A-Za-z0-9_]*')
MEMORY_UNIT_RE = re.compile(r'\b\d+(?:\.\d+)?\s?(?:KB|MB|GB|TB)\b')
PLATFORM_NAME_RE = re.compile(r'\b(PC|Console|Xbox|PlayStation|PS5|PS4|Steam Deck)\b')
PARENTHETICAL_RE = re.compile(r'\([^()]*\)')
GENERIC_LIBRARY_RE = re.compile(r'\bLib[A-Z]\w*')
HANDLE_RE = re.compile(r'@[A-Za-z][A-Za-z0-9_]*')
NOUN_PHRASE_STOP_RE = re.compile(r'\s-\s|,|\(|\.$|\.\s|\bto\b|\bon\b|\bin\b|\bfor\b|\bof\b|\bwith\b|\bacross\b')


def load_terms(entries, path):
    terms = []
    for entry in entries:
        if ':' in entry:
            term, color = entry.rsplit(':', 1)
            terms.append((term.strip(), color.strip()))
        else:
            terms.append((entry.strip(), None))

    if path:
        try:
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    if ':' in line:
                        term, color = line.rsplit(':', 1)
                        terms.append((term.strip(), color.strip()))
                    else:
                        terms.append((line.strip(), None))
        except FileNotFoundError:
            pass

    return sorted(terms, key=lambda t: len(t[0]), reverse=True)


def find_noun_phrase_span(text, start):
    pos = start
    m = re.match(r'\s*(a|an|the)\s+', text[pos:], re.IGNORECASE)
    if m:
        pos += m.end()
    else:
        m2 = re.match(r'\s+', text[pos:])
        if m2:
            pos += m2.end()
    rest = text[pos:]
    stop = NOUN_PHRASE_STOP_RE.search(rest)
    end = pos + (stop.start() if stop else len(rest))
    while end > pos and text[end - 1] == ' ':
        end -= 1
    return (pos, end) if end > pos else None


def _resolve_overlaps(spans):
    spans = sorted(spans, key=lambda s: (s[0], -(s[1] - s[0])))
    accepted = []
    last_end = -1
    for s in spans:
        if s[0] >= last_end:
            accepted.append(s)
            last_end = s[1]
    return accepted


def _apply_spans(text, spans):
    out = []
    pos = 0
    for start, end, open_tag, close_tag in spans:
        out.append(text[pos:start])
        out.append(open_tag + text[start:end] + close_tag)
        pos = end
    out.append(text[pos:])
    return ''.join(out)


def parse_changelog_md(text, version):
    lines = text.splitlines()
    version_re = re.compile(r'^Version:\s*' + re.escape(version) + r'\s*\((\d{4}-\d{2}-\d{2})\)\s*$')
    start = None
    date = None
    for i, line in enumerate(lines):
        m = version_re.match(line)
        if m:
            start = i
            date = m.group(1)
            break
    if start is None:
        return None

    i = start + 1
    if i < len(lines) and set(lines[i].strip()) <= {'-'} and lines[i].strip():
        i += 1
    while i < len(lines) and not lines[i].strip():
        i += 1

    sections = []
    current_name = None
    current_bullets = []
    next_version_re = re.compile(r'^Version:\s*\S')
    while i < len(lines):
        line = lines[i]
        if next_version_re.match(line):
            break
        stripped = line.strip()
        if not stripped:
            i += 1
            continue
        m = re.match(r'^\s*-\s+(.*)$', line)
        if m:
            current_bullets.append(m.group(1).strip())
        else:
            if current_name is not None:
                sections.append((current_name, current_bullets))
            current_name = stripped
            current_bullets = []
        i += 1
    if current_name is not None:
        sections.append((current_name, current_bullets))

    return date, sections


def to_mdy(iso_date):
    return datetime.strptime(iso_date, '%Y-%m-%d').strftime('%m/%d/%Y')


def colorize_bbcode_bullet(bullet, libraries, terms):
    text = bullet

    paren_spans = [(m.start(), m.end()) for m in PARENTHETICAL_RE.finditer(text)]

    def inside_any_paren(start, end):
        return any(ps <= start and end <= pe for ps, pe in paren_spans)

    entity_spans = []
    verb_end = None
    verb_color = None
    guessable_verb = False
    for pattern, color, guessable in VERB_COLORS:
        m = pattern.match(text)
        if m:
            entity_spans.append((m.start(1), m.end(1), f'[COLOR="{color}"]', '[/COLOR]'))
            verb_end = m.end(1)
            verb_color = color
            guessable_verb = guessable
            break

    for term, term_color in terms:
        m = re.search(r'\b' + re.escape(term) + r'\b', text)
        if m:
            resolved_color = term_color or verb_color or 'Lime'
            entity_spans.append((m.start(), m.end(), f'[COLOR="{resolved_color}"]', '[/COLOR]'))

    for lib in sorted(libraries, key=len, reverse=True):
        m = re.search(r'\b' + re.escape(lib) + r'\b', text)
        if m:
            entity_spans.append((m.start(), m.end(), '[COLOR="#FF69B4"]', '[/COLOR]'))

    for m in GENERIC_LIBRARY_RE.finditer(text):
        entity_spans.append((m.start(), m.end(), '[COLOR="#FF69B4"]', '[/COLOR]'))

    for m in HANDLE_RE.finditer(text):
        entity_spans.append((m.start(), m.end(), '[COLOR="#FF69B4"]', '[/COLOR]'))

    for m in MEMORY_UNIT_RE.finditer(text):
        entity_spans.append((m.start(), m.end(), '[COLOR="Orange"]', '[/COLOR]'))

    for m in PLATFORM_NAME_RE.finditer(text):
        entity_spans.append((m.start(), m.end(), '[COLOR="#FF69B4"]', '[/COLOR]'))

    if guessable_verb and verb_end is not None:
        span = find_noun_phrase_span(text, verb_end)
        if span:
            s, e = span
            overlaps_existing = any(s < b and a < e for a, b, *_ in entity_spans)
            if not inside_any_paren(s, e) and not overlaps_existing:
                verb_color = entity_spans[0][2]
                entity_spans.append((s, e, verb_color, '[/COLOR]'))

    paren_wrap_spans = [(s, e, '[COLOR="Gray"][i]', '[/i][/COLOR]') for s, e in paren_spans]

    all_spans = _resolve_overlaps(entity_spans + paren_wrap_spans)
    return _apply_spans(text, all_spans)


def format_bbcode(version, date, sections, libraries, terms):
    out = [f'[b][COLOR="Orange"]Version {version}[/COLOR]: [COLOR="Gray"][i]({to_mdy(date)})[/i][/COLOR][/b]', '']
    for name, bullets in sections:
        out.append(f'[SIZE="2"][b][COLOR="RoyalBlue"]{name}:[/COLOR][/b][/SIZE]')
        out.append('[LIST]')
        for bullet in bullets:
            colored = colorize_bbcode_bullet(bullet, libraries, terms)
            out.append(f'[*] {colored}')
        out.append('[/LIST]')
        out.append('')
    return '\n'.join(out).rstrip() + '\n'


def kbd_wrap_bullet(bullet, libraries, terms):
    spans = []
    for term, _color in terms:
        m = re.search(r'\b' + re.escape(term) + r'\b', bullet)
        if m:
            spans.append((m.start(), m.end(), '<kbd>', '</kbd>'))
    for lib in sorted(libraries, key=len, reverse=True):
        m = re.search(r'\b' + re.escape(lib) + r'\b', bullet)
        if m:
            spans.append((m.start(), m.end(), '<kbd>', '</kbd>'))
    for m in GENERIC_LIBRARY_RE.finditer(bullet):
        spans.append((m.start(), m.end(), '<kbd>', '</kbd>'))
    for m in SLASH_COMMAND_RE.finditer(bullet):
        spans.append((m.start(), m.end(), '<kbd>', '</kbd>'))
    return _apply_spans(bullet, _resolve_overlaps(spans))


def wrap_text(text, width=90, indent='  '):
    words = text.split(' ')
    lines, current = [], ''
    for word in words:
        candidate = (current + ' ' + word).strip()
        if len(candidate) > width and current:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    if not lines:
        return ''
    result = [lines[0]]
    result.extend(indent + line for line in lines[1:])
    return '\n'.join(result)


def format_github(version, date, sections, libraries, terms):
    out = [f'### Version {version} <sub>*({to_mdy(date)})*</sub>', '']
    for name, bullets in sections:
        out.append(f'#### {name}')
        for bullet in bullets:
            wrapped = kbd_wrap_bullet(bullet, libraries, terms)
            out.append(wrap_text('* ' + wrapped))
        out.append('')
    return '\n'.join(out).rstrip() + '\n'


def format_bethesda(version, date, sections):
    out = ['# Changelog', '', f'# VERSION {version} ({date})', '']
    for name, bullets in sections:
        out.append(f'## {name}')
        out.append('')
        for bullet in bullets:
            out.append(f'- {bullet}')
        out.append('')
    return '\n'.join(out).rstrip() + '\n'


def write_bbcode_entry(path, new_entry):
    try:
        with open(path) as f:
            existing = f.read()
    except FileNotFoundError:
        existing = ''

    if not existing.strip():
        with open(path, 'w') as f:
            f.write(new_entry)
        return

    lines = existing.splitlines(keepends=True)
    for i, line in enumerate(lines):
        if line.startswith('[b][COLOR="Orange"]Version '):
            header = ''.join(lines[:i])
            rest = ''.join(lines[i:])
            with open(path, 'w') as f:
                f.write(header + new_entry + '\n' + rest)
            return

    with open(path, 'w') as f:
        f.write(existing.rstrip('\n') + '\n\n' + new_entry)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--changelog-md', default='CHANGELOG.md')
    parser.add_argument('--version', required=True)
    parser.add_argument('--library', action='append', default=[])
    parser.add_argument('--term', action='append', default=[])
    parser.add_argument('--terms-file')
    parser.add_argument('--format', choices=['bbcode', 'github', 'bethesda', 'all'], default='all')
    parser.add_argument('--out-bbcode')
    parser.add_argument('--out-github')
    parser.add_argument('--out-bethesda')
    args = parser.parse_args()

    try:
        with open(args.changelog_md) as f:
            md_text = f.read()
    except FileNotFoundError:
        print(f"::error::Could not read {args.changelog_md}", file=sys.stderr)
        sys.exit(1)

    parsed = parse_changelog_md(md_text, args.version)
    if parsed is None:
        print(f"::error::No 'Version: {args.version} (...)' entry found in {args.changelog_md}", file=sys.stderr)
        sys.exit(1)
    date, sections = parsed
    terms = load_terms(args.term, args.terms_file)

    if args.format in ('bbcode', 'all'):
        entry = format_bbcode(args.version, date, sections, args.library, terms)
        print('--- BBCode ---')
        print(entry, end='')
        print()
        if args.out_bbcode:
            write_bbcode_entry(args.out_bbcode, entry)
            print(f'Wrote (prepended) to {args.out_bbcode}')
    if args.format in ('github', 'all'):
        entry = format_github(args.version, date, sections, args.library, terms)
        print('--- GitHub (kbd-markdown) ---')
        print(entry, end='')
        print()
        if args.out_github:
            with open(args.out_github, 'w') as f:
                f.write(entry)
            print(f'Wrote (overwrote - single latest entry) to {args.out_github}')
    if args.format in ('bethesda', 'all'):
        entry = format_bethesda(args.version, date, sections)
        print('--- Bethesda (plain markdown) ---')
        print(entry, end='')
        print()
        if args.out_bethesda:
            with open(args.out_bethesda, 'w') as f:
                f.write(entry)
            print(f'Wrote (overwrote - single latest entry) to {args.out_bethesda}')


if __name__ == '__main__':
    main()
