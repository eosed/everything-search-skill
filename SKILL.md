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
# 检索 + 直接看命中的那一行（两段式：es.exe 定位文件，再解析文件）
python scripts/search.py -c 范静雅 -e xlsx -x -m 2
# 提取结果进 JSON，便于脚本继续处理
python scripts/search.py -c 范静雅 -e xlsx -x --json
# 内容索引没收录的目录：绕过索引直接扫（慢但不受盲区影响）
python scripts/search.py --scan -p "F:\中医大\招生" -c 调剂 -e docx
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
| `-x/--extract` | 检索后**解析命中的文件**，打印命中行/单元格（xlsx/docx/pptx/pdf/txt 等） |
| `--context` | 提取时每处命中截取的字符数，默认 60 |
| `-m/--max-hits` | 每个文件最多输出几处命中，默认 3 |
| `-b/--brief` | 提取模式下只打命中内容，不打表头 |
| `--scan` | 不用 Everything 索引，直接遍历 `-p` 目录（默认当前目录）读文件找内容；索引漏收时的兜底 |

## 注意（都是实测踩出来的坑）

1. 每个搜索词必须是**独立参数**；拼成一个带空格的字符串会被当成字面量，返回 0 条。
2. `path:` / `content:` 的值**不要加引号**，中文路径加引号会返回 0 条。
3. `-r` 必须**紧贴**正则表达式本身，放别处会被当普通开关，静默返回空。
4. `-viewport-offset` 是"从第 N 条开始显示"，`-n` 是"最多取 N 条"；要取 offset 之后的 N 条，得传 `-n=offset+count`（脚本已处理）。
5. `-get-result-count` 不能和 `-n` / `-viewport-*` 同用，否则返回的是本次显示条数。
6. 语法支持通配符 `*` `?`，`|` 表示 OR。
7. Everything 未运行时返回码 8。
8. **内容索引会漏收部分文件**。实测花名册（78 KB，远小于 20 MB 上限）没进内容索引：`content:18981860513` 查不到它，但 `花名册 ext:xlsx` 文件名检索正常。遇到「文件名查得到、内容查不到」就用 `--scan` 直接扫目录，不依赖索引。
9. **别用 openpyxl 遍历来路不明的 xlsx**。损坏的 `dimension`（如 `A1:WVS983030`，假称 98 万行、实际 29 行）会让 `iter_rows()` 按假尺寸生成空行，实测峰值内存 **8.2 GB**、60 秒跑不完。`load_workbook` 本身只占 43 MB，所以「加载快」不代表「遍历安全」。`extract.py` 直读 zip、只认真实存在的 `<row>`，同一文件 0.005 秒，并且对单部件 >64 MB、纯文本 >32 MB 做了截断护栏。
