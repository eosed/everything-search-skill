#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Everything 文件搜索（es.exe 封装）：文件名 / 文件内容 / 正则 / 分页 / 导出。

用法示例：
    python search.py -q 谭超群 -e docx
    python search.py -c 智能医学工程 -e docx -p F:\中医大
    python search.py -q "试卷.*2026" -r -e docx --json
    python search.py -e pdf -n 100 --offset 100 --format csv
"""

import argparse
import concurrent.futures
import json
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from extract import extract as extract_hits
except ImportError:  # 单文件拷贝时降级
    extract_hits = None

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

HERE = os.path.dirname(os.path.abspath(__file__))
SORTS = ('name', 'path', 'size', 'extension', 'date-created', 'date-modified',
         'date-accessed', 'date-recently-changed')
# --scan 未指定 -e 时默认扫这些类型（extract.py 能解析的）
SCAN_EXT = 'xlsx;xlsm;docx;pptx;pdf;txt;md;csv;json;log;xml;ini;yml;yaml;py;js;ts;html;sql'


def find_es():
    """定位 es.exe：技能自带 > 官方安装目录 > PATH。"""
    for c in (os.path.join(HERE, 'es.exe'), r'C:\Program Files\Everything\es.exe'):
        if os.path.isfile(c):
            return c
    return shutil.which('es')


def content_index_enabled():
    """Everything 1.5 内容索引是否开启（直接扫 ini 的 key=value，无 section）。"""
    ini = os.path.join(os.environ.get('APPDATA', ''), 'Everything', 'Everything.ini')
    try:
        with open(ini, encoding='utf-8', errors='replace') as f:
            for ln in f:
                if ln.startswith('content_indexing_enabled='):
                    return ln.split('=', 1)[1].strip() == '1'
    except OSError:
        pass
    return None


def build_cmd(es, a, count=None, paginate=True):
    """按空格拆 argv，path:/content: 的值不加引号（加引号遇中文路径返回 0 条）。"""
    cmd = [es]
    if paginate:
        n = count if count is not None else a.max_results
        if a.offset:
            # -viewport-offset 是"从第 N 条开始显示"，-n 是"最多取 N 条"，
            # 因此取 offset+count 条再裁掉前 offset 条，否则 offset>=count 时会空
            cmd += ['-n', str(n + a.offset), '-viewport-offset', str(a.offset)]
        else:
            cmd += ['-n', str(n)]
    if a.folders:
        cmd.append('/ad')
    elif a.files_only:
        cmd.append('/a-d')
    if a.sort_by:
        cmd += ['-sort', a.sort_by + ('-descending' if a.desc else '')]
    if a.case:
        cmd.append('-i')
    if a.whole_word:
        cmd.append('-w')
    if a.match_path:
        cmd.append('-p')
    if a.prefix:
        cmd.append('-prefix')
    if a.suffix:
        cmd.append('-suffix')
    if a.ignore_punctuation:
        cmd.append('-ignore-punctuation')
    cols = ['-size', '-dm', '-dc', '-extension']
    if a.format == 'json':
        cmd += ['-json', '-date-format', '1'] + cols
    elif a.format in ('csv', 'tsv'):
        cmd += ['-' + a.format] + cols
    else:
        cmd += ['-full-path-and-name', '-size', '-dm']
    if a.path:
        cmd += ['-path', a.path]
    terms = []
    if a.ext:
        terms.append('ext:%s' % a.ext)
    if a.content:
        terms.append('content:%s' % a.content)
    if a.query:
        # -r 必须紧贴正则表达式本身，放别处会被当成普通开关，匹配不到任何东西
        terms.extend(['-r', a.query] if a.regex else [a.query])
    return cmd + terms


def run(cmd, timeout=180):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8',
                           errors='replace', timeout=timeout)
    except subprocess.TimeoutExpired:
        return None, '搜索超时'
    except FileNotFoundError:
        return None, 'es.exe 未找到: %s' % cmd[0]
    except Exception as e:  # noqa: BLE001
        return None, str(e)
    if r.returncode == 8:
        return None, 'Everything 未运行，请先启动 Everything'
    if r.returncode != 0:
        return None, '搜索失败，错误码 %d: %s' % (r.returncode, (r.stderr or '').strip()[:200])
    return r.stdout or '', None


def search(a):
    es = find_es()
    if not es:
        return {'error': 'es.exe 未找到（应有 scripts/es.exe，或 C:\\Program Files\\Everything\\es.exe）'}
    if not (a.query or a.content or a.ext or a.path):
        return {'error': '至少给出 --query / --content / --ext / --path 之一'}
    if a.content and content_index_enabled() is False:
        sys.stderr.write('提示: 内容索引未开启（content_indexing_enabled=0），content: 查询会很慢或返回空。\n')

    if a.export:
        cmd = build_cmd(es, a) + ['-export-' + a.format, a.export]
        _, err = run(cmd)
        return {'error': err} if err else {'exported': a.export, 'format': a.format}

    out, err = run(build_cmd(es, a))
    if err:
        return {'error': err}

    res = {'count': 0}
    if a.format == 'json':
        text = out.strip()
        res['results'] = json.loads(text) if text else []
        res['count'] = len(res['results'])
    else:
        lines = [ln for ln in out.splitlines() if ln.strip()]
        if a.format == 'csv':
            res['results'] = lines
            res['count'] = max(0, len(lines) - 1)
        elif a.format == 'tsv':
            res['results'] = lines
            res['count'] = max(0, len(lines) - 1)
        else:
            res['results'] = [ln.strip() for ln in lines]
            res['count'] = len(res['results'])

    if a.extract:
        # 只调一次 es.exe：非 json 时切 json 重跑，已经是 json 就直接复用 out
        if a.format != 'json':
            fmt, a.format = a.format, 'json'
            out, err = run(build_cmd(es, a))
            a.format = fmt
            if err:
                return {'error': err}
        text = out.strip()
        try:
            rows = json.loads(text) if text else []
        except (ValueError, TypeError):
            rows = []
        # 同一文件在微信多个目录里重复出现，按 (文件名, 大小) 去重
        seen, paths = set(), []
        for r in rows:
            p = r.get('filename', '')
            key = (os.path.basename(p), r.get('size', 0))
            if p and key not in seen:
                seen.add(key)
                paths.append(p)
        res['paths'] = paths
        res['count'] = len(paths)
        res['raw_count'] = len(rows)

    if a.total:
        # -get-result-count 必须不带 -n / -viewport-*，否则返回的是本次显示条数
        cnt, err = run(build_cmd(es, a, count=None, paginate=False) + ['-get-result-count'])
        if not err:
            try:
                res['total'] = int(cnt.strip() or 0)
            except ValueError:
                pass
    return res


def walk_files(root, exts):
    """递归列出 root 下扩展名匹配的文件。exts 形如 'docx;pdf'，空则全要。"""
    want = {('.' + e.strip().lstrip('.').lower()) for e in (exts or '').split(';') if e.strip()}
    out = []
    for dirpath, _, names in os.walk(root):
        for n in names:
            if not want or os.path.splitext(n)[1].lower() in want:
                out.append(os.path.join(dirpath, n))
    return out


def collect_hits(paths, terms, a):
    """并行解析一批文件，返回 [{'file','kind','hits'}]，只保留有命中的。"""
    if extract_hits is None or not paths:
        return []
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(8, len(paths))) as ex:
        parsed = list(ex.map(lambda p: extract_hits(p, terms, a.context, a.max_hits), paths))
    return [{'file': p, 'kind': kind, 'hits': hits}
            for p, (kind, hits) in zip(paths, parsed) if hits]


def main():
    p = argparse.ArgumentParser(description='Everything 文件搜索（文件名 / 文件内容 / 正则）')
    p.add_argument('--query', '-q', default='', help='文件名关键词')
    p.add_argument('--content', '-c', default='', help='文件内容关键词（需 Everything 1.5 + 内容索引）')
    p.add_argument('--path', '-p', help='限定目录（含子目录）')
    p.add_argument('--ext', '-e', help='限定扩展名，多个用 ; 分隔，如 docx;pdf')
    p.add_argument('--max-results', '-n', type=int, default=50, help='最大结果数，默认 50')
    p.add_argument('--offset', type=int, default=0, help='跳过前 N 条（配合 -n 分页）')
    p.add_argument('--total', action='store_true', help='额外返回总命中数')
    p.add_argument('--folders', action='store_true', help='只列文件夹')
    p.add_argument('--files-only', action='store_true', default=True, help='只列文件（默认）')
    p.add_argument('--all', dest='files_only', action='store_false', help='文件与文件夹都要')
    p.add_argument('--sort-by', '-s', choices=SORTS, help='排序字段')
    p.add_argument('--desc', action='store_true', help='降序')
    p.add_argument('--regex', '-r', action='store_true', help='按正则匹配')
    p.add_argument('--case', action='store_true', help='区分大小写')
    p.add_argument('--whole-word', '-w', action='store_true', help='整词匹配')
    p.add_argument('--match-path', action='store_true', help='匹配完整路径而非文件名')
    p.add_argument('--prefix', action='store_true', help='匹配词首')
    p.add_argument('--suffix', action='store_true', help='匹配词尾')
    p.add_argument('--ignore-punctuation', action='store_true', help='忽略标点')
    p.add_argument('--format', default='text', choices=['text', 'json', 'csv', 'tsv'],
                   help='输出格式，默认 text')
    p.add_argument('--json', '-j', dest='json_alias', action='store_true', help='等价 --format json')
    p.add_argument('--export', help='把结果写入文件（格式由 --format 决定）')
    p.add_argument('--extract', '-x', action='store_true',
                   help='在命中文件里提取命中位置与上下文（xlsx 给单元格坐标+整行，docx/pptx/pdf/txt 给片段）')
    p.add_argument('--context', type=int, default=60, help='--extract 时上下文长度，默认 60 字符')
    p.add_argument('--max-hits', '-m', type=int, default=3, help='--extract 时每个文件最多显示几处命中，默认 3')
    p.add_argument('--brief', '-b', action='store_true', help='只输出命中内容，省略表头与文件列表')
    p.add_argument('--scan', action='store_true',
                   help='不依赖 Everything 内容索引，直接遍历 -p 目录（默认当前目录）读文件找内容；慢但不受索引盲区影响')
    a = p.parse_args()
    if a.json_alias:
        a.format = 'json'

    # --scan：不依赖 Everything 内容索引，直接遍历目录读文件（索引漏收时的兜底）
    if a.scan:
        root = a.path or '.'
        if not os.path.isdir(root):
            print('错误: --scan 需要一个目录（用 -p 指定，或当前目录）')
            sys.exit(1)
        terms = [t for t in (a.query, a.content) if t]
        if not terms:
            print('错误: --scan 需要 -q 或 -c 作为检索词')
            sys.exit(1)
        if extract_hits is None:
            print('错误: 找不到 extract.py，无法解析文件')
            sys.exit(1)
        paths = walk_files(root, a.ext or SCAN_EXT)
        hits = collect_hits(paths, terms, a)
        if a.format == 'json' or a.json_alias:
            print(json.dumps({'root': root, 'scanned': len(paths), 'extracts': hits},
                             ensure_ascii=False, indent=2))
            return
        if not a.brief:
            print('扫描 %d 个文件，命中 %d 个:' % (len(paths), len(hits)))
        for h in hits:
            print('\n%s  [%s]' % (os.path.basename(h['file']), h['kind']))
            for loc, snip in h['hits']:
                print('  [%s] %s' % (loc, snip))
        return

    res = search(a)
    if 'error' in res:
        print('错误: %s' % res['error'])
        sys.exit(1)
    if 'exported' in res:
        print('已导出到 %s' % res['exported'])
        return

    hits = []
    if a.extract:
        terms = [t for t in (a.query, a.content) if t]
        if not terms:
            print('错误: --extract 需要 --query 或 --content 作为检索词')
            sys.exit(1)
        if extract_hits is None:
            print('错误: 找不到 extract.py，无法提取内容')
            sys.exit(1)
        hits = collect_hits(res.get('paths', []), terms, a)

    if a.format == 'json' or a.json_alias:
        if a.extract:
            res['extracts'] = hits
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return

    if a.brief:
        pass
    elif a.extract:
        # 提取模式不铺全路径列表，避免刷屏；命中段用文件名
        extra = '' if res.get('raw_count', res['count']) == res['count'] else \
            '，去重后 %d' % res['count']
        print('找到 %d 个结果%s%s' % (res.get('raw_count', res['count']), extra,
              '' if 'total' not in res else '（总命中 %d）' % res['total']))
    else:
        print('找到 %d 个结果%s:' % (res['count'],
              '' if 'total' not in res else '（总命中 %d）' % res['total']))
        for ln in res['results']:
            print(ln)

    if a.extract:
        if not a.brief:
            print('\n== 命中内容 ==')
        for h in hits:
            print('\n%s  [%s]' % (os.path.basename(h['file']), h['kind']))
            for loc, snip in h['hits']:
                print('  [%s] %s' % (loc, snip))

if __name__ == '__main__':
    main()