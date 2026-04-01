# Everything 文件搜索技能

使用 Everything 命令行工具 (es.exe) 快速搜索电脑文件。

## 触发条件

当用户需要：
- 搜索电脑上的文件/文件夹
- 按文件名查找文件
- 按扩展名查找文件
- 查找特定路径下的文件

触发关键词：搜索文件、找文件、查找文件、search file、where is

## 前置条件

- Everything 软件必须正在运行
- es.exe 位于 `C:\Program Files\Everything\es.exe`

## 使用方法

调用脚本：`scripts/search.py`

参数：
- `query`: 搜索关键词（必填）
- `max_results`: 最大结果数（可选，默认50）
- `path`: 限定搜索路径（可选）
- `ext`: 限定文件扩展名（可选）
- `files_only`: 仅文件（可选，默认True）
- `sort_by`: 排序方式（可选：name/size/date-modified/date-created）

## 示例

```python
# 搜索包含"招生"的文件
python scripts/search.py --query "招生"

# 搜索PDF文件
python scripts/search.py --query "" --ext pdf

# 在特定目录下搜索
python scripts/search.py --query "意向表" --path "E:\中医大"

# 按修改时间排序，显示最新10个
python scripts/search.py --query "报告" --sort-by date-modified --max-results 10
```

## 注意事项

1. 如果 Everything 未运行，需要先启动 Everything
2. 搜索语法支持通配符：`*` 匹配任意字符，`?` 匹配单个字符
3. 可以使用 `|` 进行 OR 搜索，如 `pdf|docx`
