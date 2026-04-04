#!/bin/bash
# Quick start guide for Liquid Blog

echo "🌊 Liquid Blog - Quick Start"
echo "============================"
echo ""

# Check if in ink directory
if [ ! -f "ink" ] && [ ! -f "ink-v2" ]; then
    echo "❌ 请在 Ink 目录下运行此脚本"
    exit 1
fi

echo "1. 初始化环境..."
./ink-v2 init 2>/dev/null || ./ink init 2>/dev/null

echo ""
echo "2. 创建示例文章..."
./ink-v2 new "我的第一篇 Liquid Blog" --tags demo,intro 2>/dev/null || \
./ink new "我的第一篇 Liquid Blog" --tags demo,intro 2>/dev/null

echo ""
echo "3. 生成三层上下文..."
./ink-v2 layer --generate 2>/dev/null || \
python3 .ink/scripts/layer-generator.py --batch 2>/dev/null

echo ""
echo "4. 查看状态..."
./ink-v2 status 2>/dev/null || ./ink status 2>/dev/null

echo ""
echo "✅ 完成！接下来你可以:"
echo ""
echo "  创建文章:"
echo "    ./ink new '文章标题'"
echo ""
echo "  编辑文章:"
echo "    ./ink edit 2025/03/20-文章标题/"
echo ""
echo "  查看列表:"
echo "    ./ink list"
echo ""
echo "  自然语言命令:"
echo "    ./ink '搜索关于 AI 的文章'"
echo "    ./ink '发布昨天的文章'"
echo ""
echo "  同步到 Git:"
echo "    ./ink sync"
echo ""
