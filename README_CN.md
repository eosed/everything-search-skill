# Everything 搜索技能

> 🚀 基于 Everything (es.exe) 的极速文件搜索，专为 OpenClaw 智能体设计

## 特性

- **毫秒级搜索**: 秒级找到文件，告别漫长等待
- **零配置**: Everything 运行即可使用
- **丰富过滤**: 支持按文件名、扩展名、路径、日期、大小搜索
- **OpenClaw 原生**: 专为 AI 智能体优化

## 系统要求

- 已安装并运行 [Everything](https://www.voidtools.com/)
- `es.exe` 位于 `C:\Program Files\Everything\es.exe`

## 安装方法

### 通过 ClawHub 安装（推荐）

```bash
clawhub install everything-search
```

### 手动安装

```bash
git clone https://github.com/eosed/everything-search-skill.git
cp -r everything-search-skill ~/.openclaw/config/skills/everything-search
```

## 使用方法

### 基础搜索

```python
python scripts/search.py --query "报告"
```

### 按扩展名搜索

```python
python scripts/search.py --query "预算" --ext xlsx
```

### 指定路径搜索

```python
python scripts/search.py --query "合同" --path "D:\Documents"
```

### 限制结果数量

```python
python scripts/search.py --query "照片" --max-results 20
```

### 按日期排序

```python
python scripts/search.py --query "发票" --sort-by date-modified
```

## 为什么用 Everything 而不是 dir /s？

| 方法 | 速度 | Token 消耗 |
|------|------|------------|
| `dir /s` (PowerShell) | 数分钟 | ~3000-4000 tokens |
| `es.exe` (Everything) | <1 秒 | ~800-1000 tokens |

**结论**: 快 60 倍，节省 3-4 倍 token 消耗。

## 参数说明

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `query` | 字符串 | 是 | 搜索关键词 |
| `max_results` | 整数 | 否 | 最大结果数（默认: 50） |
| `path` | 字符串 | 否 | 限定搜索路径 |
| `ext` | 字符串 | 否 | 文件扩展名过滤（如 `pdf`, `xlsx`） |
| `files_only` | 布尔 | 否 | 仅文件，不含文件夹（默认: True） |
| `sort_by` | 字符串 | 否 | 排序方式: `name`, `size`, `date-modified`, `date-created` |

## 通配符支持

- `*` 匹配任意字符
- `?` 匹配单个字符
- `|` 或搜索（如 `pdf|docx`）

## 常见问题

**"Everything not running" 错误**:
- 确保 Everything 已安装并在系统托盘运行
- 下载地址: https://www.voidtools.com/

**"es.exe not found" 错误**:
- 安装 Everything 时勾选命令行支持
- 或手动下载 `es.exe` 到 `C:\Program Files\Everything\`

## 许可证

MIT License

## 致谢

- [Everything](https://www.voidtools.com/) by voidtools
- 为 [OpenClaw](https://github.com/openclaw/openclaw) 构建
