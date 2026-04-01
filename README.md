# Everything Search Skill

> 🚀 Lightning-fast file search for OpenClaw agents using Everything (es.exe)

## Features

- **Instant search**: Find files in milliseconds, not minutes
- **Zero configuration**: Works out of the box with Everything running
- **Rich filtering**: Search by name, extension, path, date, size
- **OpenClaw native**: Designed specifically for AI agents

## Requirements

- [Everything](https://www.voidtools.com/) must be installed and running
- `es.exe` located at `C:\Program Files\Everything\es.exe`

## Installation

### Via ClawHub (Recommended)

```bash
clawhub install everything-search
```

### Manual Installation

```bash
git clone https://github.com/eosed/everything-search-skill.git
cp -r everything-search-skill ~/.openclaw/config/skills/everything-search
```

## Usage

### Basic Search

```python
python scripts/search.py --query "report"
```

### Search by Extension

```python
python scripts/search.py --query "budget" --ext xlsx
```

### Search in Specific Path

```python
python scripts/search.py --query "contract" --path "D:\Documents"
```

### Limit Results

```python
python scripts/search.py --query "photo" --max-results 20
```

### Sort by Date

```python
python scripts/search.py --query "invoice" --sort-by date-modified
```

## Why Everything vs. dir /s?

| Method | Speed | Token Usage |
|--------|-------|-------------|
| `dir /s` (PowerShell) | Minutes | ~3000-4000 tokens |
| `es.exe` (Everything) | <1 second | ~800-1000 tokens |

**Result**: 60x faster, 3-4x fewer tokens consumed.

## API Reference

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `query` | string | Yes | Search keywords |
| `max_results` | int | No | Max results (default: 50) |
| `path` | string | No | Limit search to path |
| `ext` | string | No | File extension filter (e.g., `pdf`, `xlsx`) |
| `files_only` | bool | No | Only files, not folders (default: True) |
| `sort_by` | string | No | Sort: `name`, `size`, `date-modified`, `date-created` |

## Wildcards

- `*` matches any characters
- `?` matches single character
- `|` for OR search (e.g., `pdf|docx`)

## Troubleshooting

**"Everything not running" error**:
- Make sure Everything is installed and running in the system tray
- Download from: https://www.voidtools.com/

**"es.exe not found" error**:
- Install Everything with command-line support
- Or manually download `es.exe` to `C:\Program Files\Everything\`

## License

MIT License

## Credits

- [Everything](https://www.voidtools.com/) by voidtools
- Built for [OpenClaw](https://github.com/openclaw/openclaw)
