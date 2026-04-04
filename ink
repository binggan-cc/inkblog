#!/usr/bin/env python3
"""
Ink CLI - Liquid Blog 命令行工具
意图驱动的交互界面，像水一样适应容器
"""

import argparse
import sys
import os
from pathlib import Path
from datetime import datetime
import re
import yaml

# 配置
INK_HOME = Path.home() / 'ink'
SKILLS_DIR = INK_HOME / '.ink' / 'skills'
CONFIG_FILE = INK_HOME / '.ink' / 'config.yaml'

def load_config():
    """加载配置"""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            return yaml.safe_load(f)
    return {}

def ensure_ink_home():
    """确保 Ink 目录存在"""
    INK_HOME.mkdir(parents=True, exist_ok=True)
    (INK_HOME / '.ink' / 'skills').mkdir(parents=True, exist_ok=True)
    (INK_HOME / '.ink' / 'workflows').mkdir(parents=True, exist_ok=True)
    (INK_HOME / '.ink' / 'sessions').mkdir(parents=True, exist_ok=True)
    (INK_HOME / '_index').mkdir(parents=True, exist_ok=True)
    (INK_HOME / '_templates').mkdir(parents=True, exist_ok=True)

def get_skill_path(skill_name):
    """获取 Skill 文件路径"""
    return SKILLS_DIR / f"{skill_name}.md"

def execute_skill(skill_name, args):
    """执行 Skill"""
    skill_path = get_skill_path(skill_name)
    
    if not skill_path.exists():
        print(f"❌ Skill 不存在: {skill_name}")
        print(f"可用 Skills: {', '.join(list_skills())}")
        return 1
    
    # 读取 Skill 内容
    with open(skill_path) as f:
        content = f.read()
    
    # 提取代码块
    code_blocks = re.findall(r'```python\n(.*?)```', content, re.DOTALL)
    
    if not code_blocks:
        print(f"⚠️ Skill {skill_name} 中没有可执行代码")
        return 1
    
    # 执行代码
    # 这里简化处理，实际可以更安全地执行
    code = code_blocks[0]
    
    # 构建参数列表
    arg_list = ['--' + k.replace('_', '-') if len(k) > 1 else '-' + k for k, v in vars(args).items() if v is not None and k != 'command']
    for k, v in vars(args).items():
        if v is not None and k != 'command':
            if isinstance(v, bool):
                if v:
                    arg_list.append(f"--{k.replace('_', '-')}")
            else:
                arg_list.extend([f"--{k.replace('_', '-')}", str(v)])
    
    # 使用 subprocess 执行
    import subprocess
    import tempfile
    
    # 创建临时文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(code)
        temp_file = f.name
    
    try:
        # 构建命令
        cmd = [sys.executable, temp_file] + arg_list
        result = subprocess.run(cmd)
        return result.returncode
    finally:
        os.unlink(temp_file)

def list_skills():
    """列出所有可用 Skills"""
    if not SKILLS_DIR.exists():
        return []
    return [f.stem for f in SKILLS_DIR.glob('*.md')]

def cmd_init(args):
    """初始化 Ink 环境"""
    ensure_ink_home()
    
    # 创建默认配置
    if not CONFIG_FILE.exists():
        default_config = {
            'site': {
                'title': 'My Liquid Blog',
                'description': 'A blog powered by Skills',
                'author': 'Anonymous'
            },
            'channels': {
                'blog': {'type': 'static', 'output': './_site'}
            },
            'search': {
                'engine': 'hybrid',
                'top_k': 10
            }
        }
        with open(CONFIG_FILE, 'w') as f:
            yaml.dump(default_config, f, default_flow_style=False)
        print(f"✅ 配置文件已创建: {CONFIG_FILE}")
    
    print(f"✅ Ink 环境已初始化: {INK_HOME}")
    return 0

def cmd_new(args):
    """创建新文章"""
    ensure_ink_home()
    
    title = args.title
    now = datetime.now()
    
    # 生成 slug
    slug = re.sub(r'[^\w\s-]', '', title).strip().lower()
    slug = re.sub(r'[-\s]+', '-', slug)
    
    # 创建目录结构
    article_dir = INK_HOME / f"{now:%Y}" / f"{now:%m}" / f"{now:%d}-{slug}"
    article_dir.mkdir(parents=True, exist_ok=True)
    
    # 创建 L0 摘要
    abstract_file = article_dir / '.abstract'
    with open(abstract_file, 'w') as f:
        f.write(f"{title}")
    
    # 创建 L1 概览
    overview_file = article_dir / '.overview'
    overview = {
        'title': title,
        'created_at': now.isoformat(),
        'status': 'draft',
        'tags': [],
        'category': 'uncategorized'
    }
    with open(overview_file, 'w') as f:
        yaml.dump(overview, f, default_flow_style=False)
    
    # 创建 L2 内容
    index_file = article_dir / 'index.md'
    with open(index_file, 'w') as f:
        f.write(f"""# {title}

> 创建于 {now:%Y-%m-%d %H:%M}

## 摘要

在这里写一句话摘要...

## 正文

开始写作吧...

## 参考

- 
""")
    
    # 创建资源目录
    (article_dir / 'assets').mkdir(exist_ok=True)
    
    print(f"✅ 文章已创建: {article_dir}")
    print(f"   L0 摘要: {abstract_file}")
    print(f"   L1 概览: {overview_file}")
    print(f"   L2 内容: {index_file}")
    
    # 如果指定了编辑，打开编辑器
    if args.edit:
        editor = os.environ.get('EDITOR', 'vim')
        os.system(f"{editor} {index_file}")
    
    return 0

def cmd_edit(args):
    """编辑文章"""
    article_path = Path(args.path)
    
    if not article_path.exists():
        print(f"❌ 路径不存在: {article_path}")
        return 1
    
    # 打开编辑器
    editor = os.environ.get('EDITOR', 'vim')
    index_file = article_path / 'index.md'
    
    if index_file.exists():
        os.system(f"{editor} {index_file}")
    else:
        print(f"❌ 未找到 index.md: {index_file}")
        return 1
    
    return 0

def cmd_status(args):
    """显示状态"""
    print("\n🌊 Liquid Blog 状态\n" + "=" * 40)
    
    print(f"\n📁 根目录: {INK_HOME}")
    print(f"   存在: {INK_HOME.exists()}")
    
    if INK_HOME.exists():
        # 统计文章
        article_count = 0
        for year_dir in INK_HOME.iterdir():
            if year_dir.is_dir() and not year_dir.name.startswith('_'):
                for month_dir in year_dir.iterdir():
                    if month_dir.is_dir():
                        article_count += len([d for d in month_dir.iterdir() if d.is_dir()])
        
        print(f"\n📝 文章数量: {article_count}")
        
        # 列出 Skills
        skills = list_skills()
        print(f"\n🛠️  Skills ({len(skills)}):")
        for skill in skills:
            print(f"   • {skill}")
    
    return 0

def cmd_list(args):
    """列出所有文章"""
    print("\n📝 文章列表\n" + "=" * 50)
    
    for year_dir in sorted(INK_HOME.iterdir()):
        if not year_dir.is_dir() or year_dir.name.startswith('_'):
            continue
        
        print(f"\n📅 {year_dir.name}")
        
        for month_dir in sorted(year_dir.iterdir()):
            if not month_dir.is_dir():
                continue
            
            print(f"  📂 {month_dir.name}")
            
            for article_dir in sorted(month_dir.iterdir()):
                if not article_dir.is_dir():
                    continue
                
                # 读取标题
                overview_file = article_dir / '.overview'
                title = article_dir.name
                status = "?"
                
                if overview_file.exists():
                    try:
                        with open(overview_file) as f:
                            overview = yaml.safe_load(f)
                        title = overview.get('title', article_dir.name)
                        status = overview.get('status', '?')[0].upper()
                    except:
                        pass
                
                status_icon = {
                    'D': '📝',  # draft
                    'R': '👀',  # review
                    'Y': '✅',  # ready
                    'P': '🚀',  # published
                    'A': '📦'   # archived
                }.get(status, '❓')
                
                print(f"    {status_icon} {article_dir.name[3:]} - {title}")
    
    return 0

def cmd_nlp(args):
    """自然语言解析入口"""
    query = args.query
    
    # 简单的意图识别
    # 可以接入 LLM 做更智能的解析
    
    # 发布意图
    if any(kw in query for kw in ['发布', 'publish', 'deploy', '上线']):
        # 提取路径
        match = re.search(r'(\d{4}/\d{2}/\d{2}-[^\s]+)', query)
        if match:
            path = match.group(1)
            print(f"🤖 识别意图: 发布文章")
            print(f"   路径: {path}")
            # 调用 publish skill
            return execute_skill('publish', argparse.Namespace(path=path, channels='all', draft=False, schedule=None))
    
    # 搜索意图
    if any(kw in query for kw in ['搜索', '查找', 'find', 'search', '找']):
        # 提取查询词
        match = re.search(r'["\']([^"\']+)["\']', query)
        if match:
            search_query = match.group(1)
            print(f"🤖 识别意图: 搜索")
            print(f"   查询: {search_query}")
            return execute_skill('search', argparse.Namespace(query=search_query, mode='semantic', context=None, top_k=10, filter=None, json=False))
    
    # 分析意图
    if any(kw in query for kw in ['分析', '统计', 'analyze', 'stats']):
        print(f"🤖 识别意图: 分析")
        return execute_skill('analyze', argparse.Namespace(path=None, type='stats', period='month', output='text'))
    
    # 新建意图
    if any(kw in query for kw in ['新建', '创建', 'new', 'create']):
        match = re.search(r'["\']([^"\']+)["\']', query)
        if match:
            title = match.group(1)
            print(f"🤖 识别意图: 创建文章")
            print(f"   标题: {title}")
            return cmd_new(argparse.Namespace(title=title, edit=False))
    
    print(f"🤖 未能识别意图: {query}")
    print("   尝试直接执行 skill...")
    
    # 尝试匹配 skill 名称
    words = query.split()
    if words and words[0] in list_skills():
        return execute_skill(words[0], argparse.Namespace())
    
    return 1

def main():
    parser = argparse.ArgumentParser(
        description='Ink CLI - Liquid Blog 命令行工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  ink init                           # 初始化环境
  ink new "我的第一篇博客"             # 创建新文章
  ink edit 2025/03/20-hello-world/   # 编辑文章
  ink publish 2025/03/20-hello-world/# 发布文章
  ink search "AI 开发"               # 搜索文章
  ink analyze                        # 分析统计
  ink "把昨天的想法扩展成文章"         # 自然语言命令
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # init
    init_parser = subparsers.add_parser('init', help='初始化 Ink 环境')
    init_parser.set_defaults(func=cmd_init)
    
    # new
    new_parser = subparsers.add_parser('new', help='创建新文章')
    new_parser.add_argument('title', help='文章标题')
    new_parser.add_argument('--edit', '-e', action='store_true', help='创建后立即编辑')
    new_parser.set_defaults(func=cmd_new)
    
    # edit
    edit_parser = subparsers.add_parser('edit', help='编辑文章')
    edit_parser.add_argument('path', help='文章路径')
    edit_parser.set_defaults(func=cmd_edit)
    
    # status
    status_parser = subparsers.add_parser('status', help='显示状态')
    status_parser.set_defaults(func=cmd_status)
    
    # list
    list_parser = subparsers.add_parser('list', help='列出所有文章')
    list_parser.set_defaults(func=cmd_list)
    
    # publish (skill wrapper)
    publish_parser = subparsers.add_parser('publish', help='发布文章')
    publish_parser.add_argument('path', help='文章路径')
    publish_parser.add_argument('--channels', '-c', default='all', help='目标渠道')
    publish_parser.add_argument('--draft', action='store_true', help='作为草稿发布')
    publish_parser.add_argument('--schedule', '-s', help='定时发布')
    publish_parser.set_defaults(func=lambda args: execute_skill('publish', args))
    
    # search (skill wrapper)
    search_parser = subparsers.add_parser('search', help='搜索文章')
    search_parser.add_argument('query', help='搜索查询')
    search_parser.add_argument('--mode', '-m', default='semantic', choices=['semantic', 'keyword', 'hybrid', 'sql'])
    search_parser.add_argument('--top-k', '-k', type=int, default=10)
    search_parser.add_argument('--json', action='store_true', help='JSON 输出')
    search_parser.set_defaults(func=lambda args: execute_skill('search', args))
    
    # analyze (skill wrapper)
    analyze_parser = subparsers.add_parser('analyze', help='分析文章')
    analyze_parser.add_argument('path', nargs='?', help='文章路径')
    analyze_parser.add_argument('--type', '-t', default='content', choices=['content', 'stats', 'graph', 'readability'])
    analyze_parser.add_argument('--period', '-p', default='all')
    analyze_parser.add_argument('--output', '-o', default='text', choices=['text', 'json', 'html'])
    analyze_parser.set_defaults(func=lambda args: execute_skill('analyze', args))
    
    # 自然语言入口（无子命令时）
    parser.add_argument('query', nargs='?', help='自然语言命令')
    
    args = parser.parse_args()
    
    # 如果没有子命令但有 query，使用 NLP 解析
    if args.command is None and args.query:
        return cmd_nlp(args)
    
    # 如果没有命令也没有 query，显示帮助
    if args.command is None:
        parser.print_help()
        return 0
    
    # 执行命令
    return args.func(args)

if __name__ == '__main__':
    sys.exit(main())
