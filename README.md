# Everything Search Skill

> 🚀 Lightning-fast file search for AI agents using Everything (es.exe) — by filename **and by file content**

## Features

- **Instant search**: Find files in milliseconds, not minutes
- **Content search**: Find documents by the text inside them (`content:`, needs Everything 1.5 + content indexing)
- **Rich filtering**: name, extension, path, regex, whole word, case, match-path, prefix/suffix
- **Pagination & totals**: `--offset` / `--total` for large result sets
- **Machine-readable output**: `json` / `csv` / `tsv`, or export straight to a file
- **Bundled es.exe**: `scripts/es.exe` ships with the skill, no separate download

## Requirements

- [Everything](https://www.voidtools.com/) 1.5.x installed and running (1.4 has no `content:`)
- For fast content search: Options → Indexes → **Enable content indexing**, and add the folders/file types you want indexed

## Installation

```bash
git clone https://github.com/eosed/everything-search-skill.git
cp -r everything-search-skill ~/.agents/skills/everything-search
```

## Usage

```bash
# by filename
python scripts/search.py -q 招生
python scripts/search.py -q 谭超群 -e docx -p "F:\\中医大"

# by text inside documents
python scripts/search.py -c 智能医学工程 -e docx

# regex, newest first
python scripts/search.py -q "试卷[CD]-2026" -r -e docx -s date-modified --desc

# paginate
python scripts/search.py -e pdf -n 0 --total
python scripts/search.py -e pdf -n 50 --offset 50 --json

# export
python scripts/search.py -q 谭超群 -e docx --format csv --export out.csv
```

## API Reference

| Parameter | Description |
| --- | --- |
| `-q/--query` | Filename keywords |
| `-c/--content` | Keyword **inside** file content (AND with `-q`) |
| `-p/--path` | Limit to a folder (recursive) |
| `-e/--ext` | Extensions, `;`-separated, e.g. `docx;pdf` |
| `-n/--max-results` | Max results, default 50; `0` + `--total` for count only |
| `--offset` | Skip first N results |
| `--total` | Also return the total match count |
| `-s/--sort-by` | name / path / size / extension / date-created / date-modified / date-accessed / date-recently-changed |
| `--desc` | Descending order |
| `-r/--regex` | Regular expression match |
| `--case` | Case sensitive |
| `-w/--whole-word` | Whole word match |
| `--match-path` | Match full path instead of filename |
| `--prefix` / `--suffix` | Match start / end of words |
| `--ignore-punctuation` | Ignore punctuation |
| `--folders` / `--all` | Folders only / files and folders (files only by default) |
| `--format` | text (default) / json / csv / tsv |
| `-j/--json` | Same as `--format json` |
| `--export` | Write results to a file |

## Gotchas (all found the hard way)

1. Each search term must be its **own argv**; joining them into one space-separated string makes es.exe treat it as a literal and return 0 results.
2. Never quote `path:` / `content:` values — quoted Chinese paths return 0 results.
3. `-r` must sit **immediately before** the regex, otherwise it is treated as a plain switch and silently matches nothing.
4. `-viewport-offset` starts display at N while `-n` caps how many are fetched — pass `-n = offset + count` (handled by the script).
5. `-get-result-count` must not be combined with `-n` / `-viewport-*`, or you get the page size back.
6. Wildcards `*` `?`, `|` for OR.
7. Exit code 8 means Everything is not running.

## Why Everything vs. `dir /s`?

| Method | Speed | Token usage |
|--------|-------|-------------|
| `dir /s` (PowerShell) | Minutes | ~3000-4000 tokens |
| `es.exe` (Everything) | <1 second | ~800-1000 tokens |

## License

MIT

## Credits

- [Everything](https://www.voidtools.com/) by voidtools
