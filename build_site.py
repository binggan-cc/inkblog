#!/usr/bin/env python3
"""
静态网站生成器 - 将所有文章 index.md 转换为 HTML
用法: python3 build_site.py
"""

import os
import re
import yaml
from pathlib import Path
from datetime import datetime

# 尝试导入 markdown 库，没有则用简单替换
try:
    import markdown
    HAS_MARKDOWN = True
except ImportError:
    HAS_MARKDOWN = False
    print("提示: 安装 markdown 库可获得更好效果: pip3 install markdown")

ROOT = Path(".")
SITE_DIR = ROOT / "_site"

def md_to_html(text):
    """Markdown 转 HTML"""
    if HAS_MARKDOWN:
        return markdown.markdown(text, extensions=['tables', 'fenced_code', 'toc'])
    
    # 简单的 Markdown 转换（不依赖第三方库）
    lines = text.split('\n')
    html_lines = []
    in_code = False
    in_table = False
    in_list = False
    
    for line in lines:
        # 代码块
        if line.startswith('```'):
            if in_code:
                html_lines.append('</code></pre>')
                in_code = False
            else:
                lang = line[3:].strip()
                html_lines.append(f'<pre><code class="language-{lang}">')
                in_code = True
            continue
        
        if in_code:
            html_lines.append(line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'))
            continue
        
        # 表格
        if '|' in line and line.strip().startswith('|'):
            if not in_table:
                html_lines.append('<table>')
                in_table = True
            cells = [c.strip() for c in line.strip().strip('|').split('|')]
            if all(re.match(r'^[-:]+$', c) for c in cells if c):
                html_lines.append('<tbody>')
                continue
            tag = 'th' if not any('<tbody>' in l for l in html_lines[-5:]) else 'td'
            row = ''.join(f'<{tag}>{c}</{tag}>' for c in cells)
            html_lines.append(f'<tr>{row}</tr>')
            continue
        elif in_table:
            html_lines.append('</tbody></table>')
            in_table = False
        
        # 标题
        if line.startswith('######'):
            html_lines.append(f'<h6>{line[6:].strip()}</h6>')
        elif line.startswith('#####'):
            html_lines.append(f'<h5>{line[5:].strip()}</h5>')
        elif line.startswith('####'):
            html_lines.append(f'<h4>{line[4:].strip()}</h4>')
        elif line.startswith('###'):
            html_lines.append(f'<h3>{line[3:].strip()}</h3>')
        elif line.startswith('##'):
            html_lines.append(f'<h2>{line[2:].strip()}</h2>')
        elif line.startswith('#'):
            html_lines.append(f'<h1>{line[1:].strip()}</h1>')
        # 分割线
        elif line.strip() in ('---', '***', '___'):
            html_lines.append('<hr>')
        # 引用
        elif line.startswith('>'):
            html_lines.append(f'<blockquote><p>{inline_md(line[1:].strip())}</p></blockquote>')
        # 列表
        elif re.match(r'^[-*+] ', line):
            if not in_list:
                html_lines.append('<ul>')
                in_list = True
            html_lines.append(f'<li>{inline_md(line[2:].strip())}</li>')
        elif re.match(r'^\d+\. ', line):
            if not in_list:
                html_lines.append('<ol>')
                in_list = True
            html_lines.append(f'<li>{inline_md(re.sub(r"^\d+\. ", "", line))}</li>')
        else:
            if in_list:
                html_lines.append('</ul>')
                in_list = False
            if line.strip():
                html_lines.append(f'<p>{inline_md(line)}</p>')
            else:
                html_lines.append('')
    
    if in_table:
        html_lines.append('</tbody></table>')
    if in_list:
        html_lines.append('</ul>')
    
    return '\n'.join(html_lines)

def inline_md(text):
    """处理行内 Markdown"""
    # 粗体
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'__(.+?)__', r'<strong>\1</strong>', text)
    # 斜体
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
    # 行内代码
    text = re.sub(r'`(.+?)`', r'<code>\1</code>', text)
    # 链接
    text = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2">\1</a>', text)
    return text

def read_overview(article_dir):
    """读取文章元数据"""
    overview_file = article_dir / '.overview'
    abstract_file = article_dir / '.abstract'
    
    meta = {'title': article_dir.name, 'tags': [], 'status': 'published'}
    
    if overview_file.exists():
        try:
            content = overview_file.read_text(encoding='utf-8')
            parsed = yaml.safe_load(content)
            if parsed:
                meta.update(parsed)
        except:
            pass
    
    if abstract_file.exists():
        meta['abstract'] = abstract_file.read_text(encoding='utf-8').strip()
    
    return meta

def build_article_html(title, content_html, meta, back_path="../../../"):
    """生成文章页面 HTML"""
    tags_html = ''.join(f'<span class="tag">{t}</span>' for t in meta.get('tags', []))
    date_str = ''
    if 'created_at' in meta:
        try:
            dt = meta['created_at']
            if isinstance(dt, str):
                date_str = dt[:10]
            else:
                date_str = str(dt)[:10]
        except:
            pass
    
    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - 程老师的数字花园</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            line-height: 1.8;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 2rem 1rem;
            background: #fafafa;
        }}
        nav {{
            margin-bottom: 2rem;
        }}
        nav a {{
            color: #3498db;
            text-decoration: none;
            font-size: 0.9rem;
        }}
        nav a:hover {{ text-decoration: underline; }}
        .article-header {{
            margin-bottom: 2rem;
            padding-bottom: 1rem;
            border-bottom: 2px solid #e0e0e0;
        }}
        .article-header h1 {{
            font-size: 2rem;
            color: #2c3e50;
            margin-bottom: 0.5rem;
            line-height: 1.3;
        }}
        .article-meta {{
            display: flex;
            gap: 1rem;
            align-items: center;
            flex-wrap: wrap;
            font-size: 0.85rem;
            color: #999;
        }}
        .tag {{
            background: #f0f4f8;
            color: #5a6c7d;
            padding: 0.2rem 0.6rem;
            border-radius: 12px;
            font-size: 0.8rem;
        }}
        .content h1 {{ font-size: 1.8rem; margin: 2rem 0 1rem; color: #2c3e50; }}
        .content h2 {{ font-size: 1.4rem; margin: 2rem 0 0.8rem; color: #2c3e50; padding-bottom: 0.3rem; border-bottom: 1px solid #eee; }}
        .content h3 {{ font-size: 1.2rem; margin: 1.5rem 0 0.6rem; color: #34495e; }}
        .content h4 {{ font-size: 1.05rem; margin: 1.2rem 0 0.5rem; color: #34495e; }}
        .content p {{ margin-bottom: 1rem; }}
        .content ul, .content ol {{ margin: 0.5rem 0 1rem 1.5rem; }}
        .content li {{ margin-bottom: 0.3rem; }}
        .content blockquote {{
            border-left: 4px solid #3498db;
            padding: 0.5rem 1rem;
            margin: 1rem 0;
            background: #f8f9fa;
            color: #555;
            border-radius: 0 4px 4px 0;
        }}
        .content pre {{
            background: #1e1e1e;
            color: #d4d4d4;
            padding: 1rem;
            border-radius: 6px;
            overflow-x: auto;
            margin: 1rem 0;
            font-size: 0.9rem;
        }}
        .content code {{
            background: #f0f0f0;
            padding: 0.1rem 0.3rem;
            border-radius: 3px;
            font-size: 0.9em;
            font-family: "SF Mono", Monaco, Consolas, monospace;
        }}
        .content pre code {{
            background: none;
            padding: 0;
            color: inherit;
        }}
        .content table {{
            width: 100%;
            border-collapse: collapse;
            margin: 1rem 0;
            font-size: 0.9rem;
        }}
        .content th, .content td {{
            border: 1px solid #ddd;
            padding: 0.5rem 0.75rem;
            text-align: left;
        }}
        .content th {{ background: #f5f5f5; font-weight: 600; }}
        .content tr:nth-child(even) {{ background: #fafafa; }}
        .content hr {{ border: none; border-top: 1px solid #e0e0e0; margin: 2rem 0; }}
        .content a {{ color: #3498db; text-decoration: none; }}
        .content a:hover {{ text-decoration: underline; }}
        .content strong {{ font-weight: 600; }}
        footer {{
            text-align: center;
            padding: 3rem 0;
            color: #999;
            font-size: 0.9rem;
            border-top: 1px solid #e0e0e0;
            margin-top: 3rem;
        }}
    </style>
</head>
<body>
    <nav><a href="{back_path}index.html">← 返回首页</a></nav>
    
    <div class="article-header">
        <h1>{title}</h1>
        <div class="article-meta">
            {f'<span>📅 {date_str}</span>' if date_str else ''}
            {tags_html}
        </div>
    </div>
    
    <div class="content">
        {content_html}
    </div>
    
    <footer>
        <p>🍪 使用 Liquid Blog Manager 构建</p>
        <p>© 2026 程老师的数字花园</p>
    </footer>
</body>
</html>'''

def build_site():
    """构建整个静态网站"""
    count = 0
    
    for year_dir in sorted(ROOT.iterdir()):
        if not year_dir.is_dir() or not year_dir.name.isdigit():
            continue
        
        for month_dir in sorted(year_dir.iterdir()):
            if not month_dir.is_dir():
                continue
            
            for article_dir in sorted(month_dir.iterdir()):
                if not article_dir.is_dir():
                    continue
                
                index_md = article_dir / 'index.md'
                if not index_md.exists():
                    continue
                
                # 读取 Markdown
                md_content = index_md.read_text(encoding='utf-8')
                
                # 读取元数据
                meta = read_overview(article_dir)
                title = meta.get('title', article_dir.name)
                
                # 转换内容（跳过第一个 h1，因为 header 里已有标题）
                lines = md_content.split('\n')
                if lines and lines[0].startswith('# '):
                    lines = lines[1:]
                content_html = md_to_html('\n'.join(lines))
                
                # 生成输出路径
                out_dir = SITE_DIR / year_dir.name / month_dir.name / article_dir.name
                out_dir.mkdir(parents=True, exist_ok=True)
                
                # 写入 HTML
                html = build_article_html(title, content_html, meta)
                (out_dir / 'index.html').write_text(html, encoding='utf-8')
                
                print(f"✅ {year_dir.name}/{month_dir.name}/{article_dir.name}")
                count += 1
    
    print(f"\n共生成 {count} 篇文章页面")
    print(f"输出目录: {SITE_DIR.resolve()}")

if __name__ == '__main__':
    build_site()
