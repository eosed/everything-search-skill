#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从文件里提取命中位置与上下文：xlsx 给单元格坐标+整行，docx/pptx 给段落片段。

不用 openpyxl / python-docx，直接解 OOXML 的 zip（快 1~2 个数量级）。
支持 xlsx/xlsm/docx/pptx/txt/md/csv/json/log/pdf(需 pypdf)；旧版 .doc/.xls 不支持。

用法:
    python extract.py "F:\a.xlsx" 范静雅
    python extract.py "F:\a.docx" 谭超群 -c 80 -m 5
"""

import os
import re
import sys
import zipfile
from html import unescape

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

TEXT_EXT = {'.txt', '.md', '.csv', '.tsv', '.json', '.log', '.xml', '.ini', '.yml', '.yaml',
            '.py', '.js', '.ts', '.html', '.htm', '.sql', '.bat', '.sh', '.tex'}
# 内存护栏：单个 OOXML 部件 / 纯文本文件最多读这么多字节，超了就跳过或截断。
# 防止损坏的 dimension（如 A1:WVS983030）或超大日志把内存吃光。
MAX_PART = 64 * 1024 * 1024
MAX_TEXT = 32 * 1024 * 1024
LINE_MAX = 300  # 单条命中片段的最大显示长度
ATTR = re.compile(r'([\w:]+)="([^"]*)"')
TAG = re.compile(r'<[^>]+>')
PHONETIC = re.compile(r'<(rPh|phoneticPr)\b[^>]*>.*?</\1>', re.S)
CELL = re.compile(r'<c\b([^>]*?)(?:/>|>(.*?)</c>)', re.S)
ROW = re.compile(r'<row\b([^>]*)>(.*?)</row>', re.S)
SLIDE = re.compile(r'ppt/slides/slide(\d+)\.xml$')


def _plain(xml):
    """去掉 XML 标签，保留文字（含实体反转义）。"""
    return unescape(TAG.sub('', PHONETIC.sub('', xml)))


def _ooxml_plain(xml):
    """Word/PowerPoint 正文：段落换行、单元格用 | 分隔，再去标签。"""
    xml = (xml.replace('</w:p>', '\n').replace('</a:p>', '\n')
              .replace('<w:tab/>', '\t').replace('<w:br/>', '\n')
              .replace('</w:tc>', ' | '))
    return _plain(xml)


def _read_text(path):
    with open(path, 'rb') as f:
        raw = f.read(MAX_TEXT)
    for enc in ('utf-8-sig', 'utf-8', 'gb18030', 'utf-16'):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode('utf-8', 'replace')


def _patterns(terms, regex):
    return [re.compile(t if regex else re.escape(t), re.I) for t in terms if t]


def _hit(pattern, text):
    return pattern.search(text)


def _clip(s, n):
    s = re.sub(r'\s+', ' ', str(s)).strip()
    return s if len(s) <= n else s[:n] + '…'


def _scan_text(text, patterns, ctx, max_hits):
    """在纯文本里找命中，返回 (位置说明, 上下文片段)。"""
    hits = []
    for p in patterns:
        for m in p.finditer(text):
            s, e = max(0, m.start() - ctx), min(len(text), m.end() + ctx)
            hits.append(('offset %d' % m.start(), _clip(text[s:e], ctx * 2 + 40)))
            if len(hits) >= max_hits:
                return hits
    return hits


def _shared_strings(z):
    try:
        data = z.read('xl/sharedStrings.xml').decode('utf-8', 'replace')
    except KeyError:
        return []
    return [_plain(si) for si in re.findall(r'<si\b[^>]*>(.*?)</si>', data, re.S)]


def _sheet_map(z):
    """[(sheet 名, 内部 xml 路径)]，按 workbook.xml + rels 解析，兼容非顺序编号。"""
    try:
        wb = z.read('xl/workbook.xml').decode('utf-8', 'replace')
    except KeyError:
        return []
    rels = {}
    try:
        rd = z.read('xl/_rels/workbook.xml.rels').decode('utf-8', 'replace')
        for m in re.finditer(r'<Relationship\b[^>]*/>', rd):
            a = dict(ATTR.findall(m.group(0)))
            t = a.get('Target', '')
            if t.startswith('/'):
                t = t.lstrip('/')
            elif not t.startswith('xl/'):
                t = 'xl/' + t
            rels[a.get('Id', '')] = t
    except KeyError:
        pass
    out = []
    for m in re.finditer(r'<sheet\b[^>]*/>', wb):
        a = dict(ATTR.findall(m.group(0)))
        part = rels.get(a.get('r:id', ''), '')
        if part:
            out.append((a.get('name', ''), part))
    return out


def _cell_values(body, shared):
    """解析一行里的非空单元格 -> [(列引用如 C39, 值)]。"""
    cells = []
    for attrs, inner in CELL.findall(body):
        a = dict(ATTR.findall(attrs))
        ref, t = a.get('r', ''), a.get('t', '')
        inner = inner or ''
        v = ''
        m = re.search(r'<v>(.*?)</v>', inner, re.S)
        if t == 's' and m:
            try:
                i = int(m.group(1))
                v = shared[i] if i < len(shared) else ''
            except ValueError:
                v = ''
        elif t == 'inlineStr':
            v = _plain(inner)
        elif m:
            v = unescape(m.group(1))
        if v != '':
            cells.append((ref, v))
    return cells


def _xlsx(path, patterns, ctx, max_hits):
    hits = []
    with zipfile.ZipFile(path) as z:
        shared = _shared_strings(z)
        for sname, part in _sheet_map(z):
            try:
                if z.getinfo(part).file_size > MAX_PART:
                    continue
                data = z.read(part).decode('utf-8', 'replace')
            except KeyError:
                continue
            for rattrs, body in ROW.findall(data):
                cells = _cell_values(body, shared)
                if not cells:
                    continue
                hit_ref = None
                for ref, v in cells:
                    if any(p.search(v) for p in patterns):
                        hit_ref = ref
                        break
                if not hit_ref:
                    continue
                line = ' | '.join('%s:%s' % (r, _clip(v, ctx)) for r, v in cells[:24])
                if len(cells) > 24:
                    line += ' | …'
                # 整行可能很长，截到 LINE_MAX，避免刷屏
                if len(line) > LINE_MAX:
                    line = line[:LINE_MAX] + '…'
                hits.append(('%s!%s' % (sname, hit_ref), line))
                if len(hits) >= max_hits:
                    return hits
    return hits


def _ooxml(path, part_re, patterns, ctx, max_hits, limit=50):
    hits = []
    with zipfile.ZipFile(path) as z:
        parts = [n for n in z.namelist() if part_re.search(n)]
        parts.sort(key=lambda n: int(re.search(r'(\d+)\.xml$', n).group(1))
                   if re.search(r'(\d+)\.xml$', n) else 0)
        for n in parts[:limit]:
            if z.getinfo(n).file_size > MAX_PART:
                continue
            text = _ooxml_plain(z.read(n).decode('utf-8', 'replace'))
            for loc, snip in _scan_text(text, patterns, ctx, max_hits - len(hits)):
                hits.append(('%s %s' % (os.path.basename(n), loc), snip))
            if len(hits) >= max_hits:
                break
    return hits


def _pdf(path, patterns, ctx, max_hits):
    try:
        from pypdf import PdfReader
    except ImportError:
        try:
            from PyPDF2 import PdfReader  # noqa: F401
        except ImportError:
            return 'pdf-no-lib', []
    hits = []
    for i, page in enumerate(PdfReader(path).pages, 1):
        text = page.extract_text() or ''
        for loc, snip in _scan_text(text, patterns, ctx, max_hits - len(hits)):
            hits.append(('page %d %s' % (i, loc), snip))
        if len(hits) >= max_hits:
            break
    return 'pdf', hits


def extract(path, terms, context=60, max_hits=3, regex=False):
    """返回 (kind, [(位置, 片段)])。kind 说明用了哪种解析器。"""
    patterns = _patterns(terms, regex)
    if not patterns or not os.path.isfile(path):
        return 'skip', []
    ext = os.path.splitext(path)[1].lower()
    try:
        if ext in ('.xlsx', '.xlsm'):
            return 'xlsx', _xlsx(path, patterns, context, max_hits)
        if ext == '.docx':
            return 'docx', _ooxml(path, re.compile(r'^word/document\.xml$'),
                                  patterns, context, max_hits, 1)
        if ext == '.pptx':
            return 'pptx', _ooxml(path, SLIDE, patterns, context, max_hits)
        if ext == '.pdf':
            return _pdf(path, patterns, context, max_hits)
        if ext in TEXT_EXT:
            return 'text', _scan_text(_read_text(path), patterns, context, max_hits)
    except (zipfile.BadZipFile, OSError, KeyError):
        return 'error', []
    return 'unsupported', []


def main():
    import argparse
    p = argparse.ArgumentParser(description='提取文件内命中的位置与上下文')
    p.add_argument('path')
    p.add_argument('terms', nargs='+')
    p.add_argument('-c', '--context', type=int, default=60)
    p.add_argument('-m', '--max-hits', type=int, default=5)
    p.add_argument('-r', '--regex', action='store_true')
    a = p.parse_args()
    kind, hits = extract(a.path, a.terms, a.context, a.max_hits, a.regex)
    print('解析方式: %s, 命中 %d 处' % (kind, len(hits)))
    for loc, snip in hits:
        print('  [%s] %s' % (loc, snip))


if __name__ == '__main__':
    main()
