#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Everything 文件搜索脚本
调用 es.exe 进行快速文件搜索
"""

import subprocess
import argparse
import sys
import os
import json

# 设置标准输出编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ES_PATH = r"C:\Program Files\Everything\es.exe"

def search_files(query, max_results=50, path=None, ext=None, files_only=True, sort_by=None):
    """调用 es.exe 搜索文件"""
    
    cmd = [ES_PATH]
    
    # 构建搜索条件
    search_terms = []
    
    if path:
        search_terms.append(f'path:"{path}"')
    
    if ext:
        search_terms.append(f'ext:{ext}')
    
    if query:
        search_terms.append(query)
    
    # 组合搜索条件
    if search_terms:
        cmd.append(' '.join(search_terms))
    
    # 仅文件
    if files_only:
        cmd.append('/a-d')
    
    # 最大结果数
    cmd.extend(['-n', str(max_results)])
    
    # 排序
    if sort_by:
        sort_map = {
            'name': 'name',
            'size': 'size',
            'date-modified': 'dm',
            'date-created': 'dc'
        }
        cmd.extend(['-sort', sort_map.get(sort_by, 'name')])
    
    # 显示完整路径和大小
    cmd.extend(['-full-path-and-name', '-size', '-date-modified'])
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='cp936',
            errors='replace',
            timeout=30
        )
        
        if result.returncode == 8:
            return {"error": "Everything 未运行，请先启动 Everything 软件"}
        elif result.returncode != 0:
            return {"error": f"搜索失败，错误码: {result.returncode}"}
        
        lines = result.stdout.strip().split('\n') if result.stdout.strip() else []
        
        results = []
        for line in lines:
            if line.strip():
                # 清理乱码字符
                clean_line = line.strip().replace('\ufffd', '?')
                results.append(clean_line)
        
        return {
            "count": len(results),
            "results": results
        }
        
    except subprocess.TimeoutExpired:
        return {"error": "搜索超时"}
    except FileNotFoundError:
        return {"error": f"es.exe 未找到: {ES_PATH}"}
    except Exception as e:
        return {"error": str(e)}


def main():
    parser = argparse.ArgumentParser(description='Everything 文件搜索')
    parser.add_argument('--query', '-q', type=str, default='', help='搜索关键词')
    parser.add_argument('--max-results', '-n', type=int, default=50, help='最大结果数')
    parser.add_argument('--path', '-p', type=str, help='限定搜索路径')
    parser.add_argument('--ext', '-e', type=str, help='限定文件扩展名')
    parser.add_argument('--folders', '-f', action='store_true', help='包含文件夹')
    parser.add_argument('--sort-by', '-s', type=str, 
                        choices=['name', 'size', 'date-modified', 'date-created'],
                        help='排序方式')
    parser.add_argument('--json', '-j', action='store_true', help='JSON 格式输出')
    
    args = parser.parse_args()
    
    result = search_files(
        query=args.query,
        max_results=args.max_results,
        path=args.path,
        ext=args.ext,
        files_only=not args.folders,
        sort_by=args.sort_by
    )
    
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        if 'error' in result:
            print(f"错误: {result['error']}")
            sys.exit(1)
        
        print(f"找到 {result['count']} 个结果:")
        for r in result['results']:
            print(r)


if __name__ == '__main__':
    main()
