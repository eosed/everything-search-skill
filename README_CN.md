# Everything 搜索技能

> 🚀 基于 Everything (es.exe) 的极速文件搜索——**按文件名**和**按文件内容**都能查

## 特性

- **毫秒级搜索**：秒级找到文件，告别漫长等待
- **内容检索**：按文档里写了什么来查（`content:`，需 Everything 1.5 + 内容索引）
- **丰富过滤**：文件名、扩展名、路径、正则、整词、大小写、全路径匹配、词首/词尾
- **分页与总数**：`--offset` / `--total` 应付大批结果
- **机器可读输出**：`json` / `csv` / `tsv`，或直接导出文件
- **直接看命中内容**（`-x`）：解析命中的 xlsx/docx/pptx/pdf/txt，打印具体行/单元格/段落，不依赖 openpyxl
- **一站式查人**（`--person`）：按姓名检索并抽出 8 位工号，按出现次数排序
- **自带 es.exe**：`scripts/es.exe` 随技能打包，无需另装

## 系统要求

- 已安装并运行 [Everything](https://www.voidtools.com/) 1.5.x（1.4 没有 `content:`）
- 想快速内容检索：Options → Indexes → 勾选 **Enable content indexing**，并加入要索引的目录与文件类型

## 安装

```bash
git clone https://github.com/eosed/everything-search-skill.git
cp -r everything-search-skill ~/.agents/skills/everything-search
```

## 使用方法

```bash
# 按文件名
python scripts/search.py -q 招生
python scripts/search.py -q 谭超群 -e docx -p "F:\\中医大"

# 按文件内容
python scripts/search.py -c 智能医学工程 -e docx

# 正则 + 最新优先
python scripts/search.py -q "试卷[CD]-2026" -r -e docx -s date-modified --desc

# 分页
python scripts/search.py -e pdf -n 0 --total
python scripts/search.py -e pdf -n 50 --offset 50 --json

# 导出
python scripts/search.py -q 谭超群 -e docx --format csv --export out.csv

# 检索后直接看命中的那一行/格
python scripts/search.py -c 范静雅 -e xlsx -x -m 2

# 一站式查某人的工号
python scripts/search.py --person 孙涛
```

## 参数说明

| 参数 | 说明 |
| --- | --- |
| `-q/--query` | 文件名关键词 |
| `-c/--content` | **文件内容**关键词（与 `-q` 是 AND） |
| `-p/--path` | 限定目录（含子目录） |
| `-e/--ext` | 扩展名，多个用 `;`，如 `docx;pdf` |
| `-n/--max-results` | 最大结果数，默认 50；`0` + `--total` 只取总数 |
| `--offset` | 跳过前 N 条 |
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
| `-j/--json` | 等价 `--format json` |
| `--export` | 结果写入文件 |
| `-x/--extract` | 解析命中的文件，打印命中行/单元格（xlsx/docx/pptx/pdf/txt） |
| `--context` | 每处命中截取的字符数，默认 60 |
| `-m/--max-hits` | 每个文件最多输出几处命中，默认 3 |
| `-b/--brief` | 只打命中内容，不打表头 |
| `--person` | 一站式查人：检索 + 花名册文件名兜底，抽 8 位工号并按次数排序 |

## 注意事项（都是实测踩出来的坑）

1. 每个搜索词必须是**独立参数**；拼成一个带空格的字符串会被当成字面量，返回 0 条。
2. `path:` / `content:` 的值**不要加引号**，中文路径加引号会返回 0 条。
3. `-r` 必须**紧贴**正则表达式本身，放别处会被当普通开关，静默返回空。
4. `-viewport-offset` 是"从第 N 条开始显示"，`-n` 是"最多取 N 条"；要取 offset 之后的 N 条得传 `-n = offset + count`（脚本已处理）。
5. `-get-result-count` 不能与 `-n` / `-viewport-*` 同用，否则返回的是本次显示条数。
6. 支持通配符 `*` `?`，`|` 表示 OR。
7. Everything 未运行时返回码 8。
8. **内容索引会静默漏收部分 xlsx**。实测花名册（78 KB，远小于 20 MB 上限）没进内容索引：`content:<手机号>` 查不到，但 `花名册 ext:xlsx` 文件名检索正常。所以查人不能只靠 `content:`，`--person` 会再按「花名册/名单/人员名单/通讯录」文件名兜底捞一遍。
9. **别用 openpyxl 遍历来路不明的 xlsx**。损坏的 `dimension`（`A1:WVS983030` 对 29 行的表假称 98 万行）会让 `iter_rows()` 吃掉约 8.2 GB 内存且永不返回，而 `load_workbook` 只占 43 MB。`extract.py` 直读 zip、只认真实存在的 `<row>`，单部件上限 64 MB。

## 为什么不用 `dir /s`？

| 方法 | 速度 | Token 消耗 |
|------|------|------------|
| `dir /s` (PowerShell) | 数分钟 | ~3000-4000 tokens |
| `es.exe` (Everything) | <1 秒 | ~800-1000 tokens |

## 许可证

MIT

## 致谢

- [Everything](https://www.voidtools.com/) by voidtools
