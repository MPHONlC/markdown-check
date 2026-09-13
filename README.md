# Markdown Checker

Two things in one action:

1. **Validate** - checks that each platform file uses correctly-balanced markup for its own format: BBCode tag pairs (`[b]`/`[/b]`, `[COLOR]`/`[/COLOR]`, ...) for a BBCode forum, `<kbd>`/`<sub>` pairs plus admonition/table sanity for GitHub Flavored Markdown, and balanced `**`/`` ` `` for Bethesda (CommonMark). This is a syntax check, not a content comparison - see [changelog-check](https://github.com/MPHONlC/changelog-check) / [description-check](https://github.com/MPHONlC/description-check) for that. Fails the run on a real syntax error (an unclosed tag, etc).

2. **Regenerate** (opt-in) - auto-generates the BBCode/GitHub/Bethesda changelog files from one canonical, plain-setext `CHANGELOG.md`, so you don't have to hand-author all three every release. Bullet *wording* always comes verbatim from `CHANGELOG.md`; structural conversion (headers, dates, bullet syntax) is fully mechanical.

### Highlighting

Term colors are resolved in this order:

1. `terms_file` (e.g. `.github/changelog-highlight-terms.txt`) - one term per line, optionally `Term:Color`. No color given = inherits the bullet's own leading-verb color.
2. Slash commands, `libraries` names, PC/Console/platform names, memory-unit numbers, and any `(parenthetical)` - always gray/italic. Fully mechanical.
3. A noun-phrase guess, only for `Added`/`Fixed`/`Removed`/`New` bullets.

## Canonical `CHANGELOG.md` format expected by regenerate mode

```
Version: 0.0.9 (2026-09-11)
---------------------------

Section Name
  - A bullet, in plain English.
  - Another bullet.

Another Section
  - More bullets.
```

## Usage

```yaml
name: Markdown Checker

on:
  push:
    branches: [main]
    paths:
      - 'README_BBCODE.txt'
      - 'README_COMMONMARK.txt'
      - 'README.md'
      - 'CHANGELOG_BBCODE.txt'
      - 'CHANGELOG_GFM.txt'
      - 'CHANGELOG_COMMONMARK.txt'
  workflow_dispatch:
    inputs:
      regenerate:
        type: boolean
        default: false
      version:
        description: 'Version to regenerate, e.g. 0.0.9'
        default: ''

jobs:
  check:
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v7
      - uses: MPHONlC/markdown-check@Version-0.0.1
        with:
          mode: ${{ inputs.regenerate == true && 'regenerate' || 'validate' }}
          version: ${{ inputs.version }}
          libraries: 'LibAddonMenu,LibHarvensAddonSettings'
```

> [!NOTE]
> `mode: regenerate` only writes the changelog files - it never commits or pushes. Add your own commit step after it (with `permissions: contents: write` on the job) if you want the result saved back to the repo.

## Inputs

| Input | Required | Default | Description |
|---|---|---|---|
| `bbcode_readme` | No | *(auto-detect)* | BBCode-forum description file. Leave blank to auto-detect `README_BBCODE.txt`, then `README_ESOUI.txt` (any case). |
| `bbcode_changelog` | No | *(auto-detect)* | BBCode-forum changelog file. Leave blank to auto-detect `CHANGELOG_BBCODE.txt`, then `CHANGELOG_ESOUI.txt` (any case; in `regenerate` mode, an existing one of those two is written back to, and a brand-new project with neither yet gets `CHANGELOG_BBCODE.txt`). |
| `github_readme` | No | `README.md` | GitHub Flavored Markdown description file - this is GitHub's own required filename, so it is not auto-detected. |
| `github_changelog` | No | *(auto-detect)* | GitHub Flavored Markdown changelog file. Leave blank to auto-detect `CHANGELOG_GFM.txt`, then `CHANGELOG_GITHUB.txt` (any case). |
| `bethesda_readme` | No | *(auto-detect)* | Bethesda (CommonMark) description file. Leave blank to auto-detect `README_COMMONMARK.txt`, then `README_PLAINMARKDOWN.txt`, then `README_BETHESDA.txt` (any case). |
| `bethesda_changelog` | No | *(auto-detect)* | Bethesda (CommonMark) changelog file. Leave blank to auto-detect `CHANGELOG_COMMONMARK.txt`, then `CHANGELOG_PLAINMARKDOWN.txt`, then `CHANGELOG_BETHESDA.txt` (any case). |
| `mode` | No | `validate` | `validate` or `regenerate`. |
| `canonical_changelog` | No | `CHANGELOG.md` | Source file for regenerate mode. |
| `version` | No | `''` | Version to extract for regenerate mode (required when `mode: regenerate`). |
| `libraries` | No | `''` | Comma-separated known library names to highlight during regeneration. |
| `terms_file` | No | `.github/changelog-highlight-terms.txt` | Your glossary of recurring feature names to highlight - see "Highlighting" above. Missing file = no glossary terms (still works, just less accurate). |

## License

MIT - see [LICENSE](LICENSE).
