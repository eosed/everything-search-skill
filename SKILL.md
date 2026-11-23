---
name: everything-search
description: Lightning-fast file search over the local machine with Everything (filename AND file content). Use when the user wants to find files/folders by name, by extension, under a path, or by text inside documents, or asks "where is", "搜索文件", "找文件", "哪个文件里写了".
---

# Everything 文件搜索

用 Everything 的命令行工具 `es.exe` 秒级检索整机文件——**文件名**和**文件内容**都支持，并可直接导出 CSV/JSON。

## 前置条件

- Everything 主程序必须在运行（`C:\Program Files\Everything\Everything.exe`，需 1.5.x 才有 `content:`）。
- `es.exe` 已随本技能打包在 `scripts/es.exe`（1.1.1.40），无需另装。
- **内容检索**要快，必须在 Everything 里开启内容索引：Options → Indexes → Enable content indexing（ini 里 `content_indexing_enabled=1`），并指定要索引的目录与文件类型。未开启时 `content:` 走按需扫描，能出结果但很慢，且不带 `--path`/`--ext` 收窄容易超时返回空。

## 调用

```bash
# 按文件名
python scripts/search.py -q 招生
python scripts/search.py -q 谭超群 -e docx -p "F:\中医大"
# 按文件内容（文档里写了什么）
python scripts/search.py -c 智能医学工程 -e docx
# 正则 + 只看最新
python scripts/search.py -q "试卷[CD]-2026" -r -e docx -s date-modified --desc
# 分页拿全量：先看总命中，再翻页
python scripts/search.py -e pdf -n 0 --total
python scripts/search.py -e pdf -n 50 --offset 50 --json
# 导出
python scripts/search.py -q 谭超群 -e docx --format csv --export out.csv
```

## 参数

| 参数 | 说明 |
| --- | --- |
| `-q/--query` | 文件名关键词 |
| `-c/--content` | **文件内容**关键词（与 `-q` 是 AND） |
| `-p/--path` | 限定目录（含子目录） |
| `-e/--ext` | 限定扩展名，多个用 `;`，如 `docx;pdf` |
| `-n/--max-results` | 最大结果数，默认 50；`0` 配合 `--total` 只取总数 |
| `--offset` | 跳过前 N 条，配合 `-n` 分页 |
| `--total` | 额外返回总命中数 |
| `-s/--sort-by` | name / path / size / extension / date-created / date-modified / date-accessed / date-recently-changed |
| `--desc` | 降序 |
| `-r/--regex` | 正则匹配 |
| `--case` | 区分大小写 |
| `-w/--whole-word` | 整词匹配 |
| `--match-path` | 匹配完整路径而非仅文件名 |
| `--prefix` / `--suffix` | 匹配词首 / 词尾 |
| `--ignore-punctuation` | 忽略标点 |
| `--folders` / `--all` | 只列文件夹 / 文件与文件夹都要（默认只列文件） |
| `--format` | text（默认）/ json / csv / tsv |
| `-j/--json` | 等价 `--format json`，返回 `{count, results[], total?}` |
| `--export` | 结果写入文件，格式随 `--format` |

## 注意（都是实测踩出来的坑）

1. 每个搜索词必须是**独立参数**；拼成一个带空格的字符串会被当成字面量，返回 0 条。
2. `path:` / `content:` 的值**不要加引号**，中文路径加引号会返回 0 条。
3. `-r` 必须**紧贴**正则表达式本身，放别处会被当普通开关，静默返回空。
4. `-viewport-offset` 是"从第 N 条开始显示"，`-n` 是"最多取 N 条"；要取 offset 之后的 N 条，得传 `-n=offset+count`（脚本已处理）。
5. `-get-result-count` 不能和 `-n` / `-viewport-*` 同用，否则返回的是本次显示条数。
6. 语法支持通配符 `*` `?`，`|` 表示 OR。
7. Everything 未运行时返回码 8。
