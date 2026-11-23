#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Everything 环境自检与一键修复：es.exe / 主程序版本 / 内容索引 / 索引范围。

用法：
    python scripts/doctor.py                  # 只自检
    python scripts/doctor.py --json           # 自检结果 JSON
    python scripts/doctor.py --fix            # 缺 1.5 就装，没开内容索引就开
    python scripts/doctor.py --fix --index-path "F:/中医大" --index-path "H:/"

--fix 需要装主程序时会弹一次 UAC，用户点「是」即可，其余全自动。
"""

import argparse
import json
import os
import platform
import subprocess
import sys
import tempfile
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from search import content_index_enabled, everything_version, find_es, run  # noqa: E402

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

INI = os.path.join(os.environ.get('APPDATA', ''), 'Everything', 'Everything.ini')
VER = '1.5.0.1424b'
URL = 'https://www.voidtools.com/Everything-%s.%%s-Setup.exe' % VER
EXE = 'C:/Program Files/Everything/Everything.exe'
INDEX_EXTS = '*.doc;*.docx;*.pdf;*.txt;*.xls;*.xlsx;*.ppt;*.pptx'


def ini_value(key):
    try:
        with open(INI, encoding='utf-8', errors='replace') as f:
            for ln in f:
                if ln.startswith(key + '='):
                    return ln.split('=', 1)[1].strip()
    except OSError:
        pass
    return None


def arch_tag():
    m = (platform.machine() or '').upper()
    if m in ('AMD64', 'X86_64'):
        return 'x64'
    if m in ('ARM64', 'AARCH64'):
        return 'ARM64'
    return 'x86'


def download(tag):
    url = URL % tag
    dst = os.path.join(tempfile.gettempdir(), 'Everything-%s-%s-Setup.exe' % (VER, tag))
    print('下载 %s' % url)
    urllib.request.urlretrieve(url, dst)
    size = os.path.getsize(dst)
    if size < 1000000:
        raise RuntimeError('安装包只有 %d 字节，下载不完整' % size)
    print('  已存 %s (%.1f MB)' % (dst, size / 1048576.0))
    return dst


def install(setup):
    """自解压壳最终调用 Everything.exe -setup；-silent 免交互，UAC 由系统弹。"""
    print('安装（会弹一次 UAC，点「是」）…')
    ps = ('Start-Process -FilePath "%s" -ArgumentList "-setup","-silent" '
          '-Verb RunAs -Wait -PassThru | Select-Object -ExpandProperty ExitCode') % setup
    r = subprocess.run(['powershell', '-NoProfile', '-Command', ps],
                       capture_output=True, text=True, encoding='utf-8', errors='replace')
    code = (r.stdout or '').strip()
    if r.returncode != 0 or code not in ('0', ''):
        raise RuntimeError('安装未完成: %s' % ((r.stderr or code).strip()[:300] or '用户取消了 UAC'))
    print('  安装完成')


def patch_ini(folders):
    """改 ini 的 4 个 key；需先停服务与进程，否则会被内存里的设置覆盖。"""
    subprocess.run(['sc.exe', 'stop', 'Everything'], capture_output=True)
    subprocess.run(['taskkill', '/IM', 'Everything.exe', '/F'], capture_output=True)
    want = {
        'content_indexing_enabled': '1',
        'content_indexing_max_size': '20',
        'content_indexing_max_size_unit': '1',
    }
    # 用户已有类型就别覆盖，只在空着时补默认值
    if not ini_value('content_indexing_include_only_files'):
        want['content_indexing_include_only_files'] = INDEX_EXTS
    if folders:
        # Everything 只认反斜杠，正斜杠会被当成无效路径
        want['content_indexing_include_only_folders'] = ';'.join(os.path.normpath(p) for p in folders)
    try:
        with open(INI, encoding='utf-8', errors='replace') as f:
            lines = f.read().splitlines()
    except OSError:
        raise RuntimeError('找不到 %s，先运行一次 Everything 再修复' % INI)
    seen = set()
    out = []
    for ln in lines:
        k = ln.split('=', 1)[0]
        if k in want:
            out.append('%s=%s' % (k, want[k]))
            seen.add(k)
        else:
            out.append(ln)
    out += ['%s=%s' % (k, v) for k, v in want.items() if k not in seen]
    with open(INI, 'w', encoding='utf-8', newline='\r\n') as f:
        f.write('\n'.join(out) + '\n')
    subprocess.run(['sc.exe', 'start', 'Everything'], capture_output=True)
    if os.path.isfile(EXE):
        subprocess.Popen([EXE, '-startup'])
    print('  已写 %s 并重启 Everything' % INI)


def check():
    es = find_es()
    report = {'es_exe': es, 'es_version': None, 'everything_version': None,
              'running': False, 'content_indexing': None, 'index_folders': None,
              'index_exts': None, 'max_size_mb': None, 'ini': INI}
    hints = []

    if not es:
        hints.append('未找到 es.exe：应随技能位于 scripts/es.exe')
    else:
        out, err = run([es, '-version'])
        report['es_version'] = (out or '').strip() or None
        ver = everything_version(es)
        report['everything_version'] = ver
        report['running'] = ver is not None
        if not ver:
            hints.append('Everything 主程序未运行：先启动 Everything.exe')
        elif not ver.startswith('1.5'):
            hints.append('主程序 %s 不支持 content:（需 1.5.x）：内容检索请改用 --scan' % ver)

    report['content_indexing'] = content_index_enabled()
    if report['content_indexing'] is None:
        hints.append('ini 里没有 content_indexing_enabled（旧版主程序）')
    elif not report['content_indexing']:
        hints.append('内容索引未开启：Options → Indexes → Enable content indexing，或参考 SKILL.md 手动开启')

    report['index_folders'] = ini_value('content_indexing_include_only_folders')
    report['index_exts'] = ini_value('content_indexing_include_only_files')
    unit = ini_value('content_indexing_max_size_unit')
    size = ini_value('content_indexing_max_size')
    if size is not None:
        report['max_size_mb'] = int(size) * {0: 1 / 1024, 1: 1, 2: 1024}.get(int(unit or 1), 1)
    return report, hints


def fix(report, index_paths):
    ver = report['everything_version']
    if not ver or not ver.startswith('1.5'):
        if not report['es_exe']:
            raise RuntimeError('es.exe 缺失，无法继续：重装本技能')
        tag = arch_tag()
        print('需要安装 Everything %s (%s)' % (VER, tag))
        install(download(tag))
    else:
        print('主程序 %s 已满足要求，跳过安装' % ver)

    if report['content_indexing'] is not True or index_paths:
        folders = []
        for p in index_paths or []:
            if os.path.isdir(p):
                folders.append(os.path.abspath(p))
            else:
                print('  跳过不存在的目录: %s' % p)
        patch_ini(folders)
    else:
        print('内容索引已开启，跳过')


def main():
    p = argparse.ArgumentParser(description='Everything 环境自检 / 一键修复')
    p.add_argument('--json', '-j', action='store_true', help='输出 JSON')
    p.add_argument('--fix', action='store_true', help='缺 1.5 就装、没开内容索引就开')
    p.add_argument('--index-path', action='append', default=[],
                   help='要索引的目录，可重复；不给则沿用 ini 现有设置')
    a = p.parse_args()

    report, hints = check()

    if a.fix:
        try:
            fix(report, a.index_path)
        except Exception as e:  # noqa: BLE001
            print('\n修复失败: %s' % e)
            return 1
        report, hints = check()

    if a.json:
        print(json.dumps({'report': report, 'hints': hints}, ensure_ascii=False, indent=2))
        return 0 if not hints else 1

    def mark(ok):
        return 'OK ' if ok else '!! '

    print('Everything 环境自检')
    print('-' * 52)
    print('%s es.exe            %s' % (mark(bool(report['es_exe'])), report['es_exe'] or '(未找到)'))
    print('%s es.exe 版本       %s' % (mark(bool(report['es_version'])), report['es_version'] or '-'))
    print('%s 主程序版本        %s' % (mark(bool(report['everything_version'])),
                                     report['everything_version'] or '(未运行)'))
    ci = report['content_indexing']
    print('%s 内容索引          %s' % (mark(ci is True),
                                     {True: '已开启', False: '未开启', None: '不可用（旧版）'}[ci]))
    print('  索引目录          %s' % (report['index_folders'] or '(未限定)'))
    print('  索引类型          %s' % (report['index_exts'] or '(默认)'))
    print('  单文件上限        %s' % ('%d MB' % report['max_size_mb']
                                     if report['max_size_mb'] else '(不限)'))
    print('  ini               %s' % INI)
    if hints:
        print('\n需要处理:')
        for h in hints:
            print('  - ' + h)
        if not a.fix:
            print('\n一键修复（缺 1.5 会弹一次 UAC，点「是」即可）:')
            print('  python scripts/doctor.py --fix')
            print('  想顺带指定索引目录: --fix --index-path "F:/中医大" --index-path "H:/"')
        return 1
    print('\n全部就绪，可正常使用 content: 内容检索。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
