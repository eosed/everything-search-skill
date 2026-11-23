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
import json
import os
import shutil
import subprocess
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

HERE = os.path.dirname(os.path.abspath(__file__))
SORTS = ('name', 'path', 'size', 'extension', 'date-created', 'date-modified',
         'date-accessed', 'date-recently-changed')


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

    if a.total:
        # -get-result-count 必须不带 -n / -viewport-*，否则返回的是本次显示条数
        cnt, err = run(build_cmd(es, a, count=None, paginate=False) + ['-get-result-count'])
        if not err:
            try:
                res['total'] = int(cnt.strip() or 0)
            except ValueError:
                pass
    return res


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
    a = p.parse_args()
    if a.json_alias:
        a.format = 'json'

    res = search(a)
    if a.format == 'json' or a.json_alias:
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return
    if 'error' in res:
        print('错误: %s' % res['error'])
        sys.exit(1)
    if 'exported' in res:
        print('已导出 %d 条到 %s' % (res.get('count', 0), res['exported']))
        return
    print('找到 %d 个结果%s:' % (res['count'],
          '' if 'total' not in res else '（总命中 %d）' % res['total']))
    for ln in res['results']:
        print(ln)


if __name__ == '__main__':
    main()
